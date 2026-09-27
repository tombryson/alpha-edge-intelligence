"""Stream native xAI research, retaining terminal status and failure evidence."""

import asyncio
import json
import time
from typing import Callable

import httpx


def output_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    parts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "output_text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
        if item.get("type") != "message" or item.get("role", "assistant") != "assistant":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                parts.append(part["text"])
    return "\n".join(parts).strip()


def cited_sources(data: dict) -> list[dict]:
    sources = {}
    def visit(value):
        if isinstance(value, dict):
            url = value.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                sources[url] = {"url": url, "title": value.get("title") or url, "content": "",
                    "published_at": value.get("published_at"), "verification": "provider_citation_only"}
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    # Search-result URLs are retained in the raw response, not labelled as citations.
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message" or item.get("role", "assistant") != "assistant":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                visit(part.get("annotations") or [])
    return list(sources.values())


async def fetch_xai_research(*, api_key: str, api_url: str, model: str, prompt: str,
    timeout_seconds: float = 600, idle_timeout_seconds: float = 180, max_tokens: int | None = None,
    max_attempts: int = 2, temperature: float = 0.15, on_progress: Callable | None = None) -> dict:
    model = model.strip().removeprefix("x-ai/")
    attempts = []
    base = {"model": model, "prompt": prompt, "summary": "", "results": [], "provider": "xai"}
    if not api_key:
        return {**base, "attempted": False, "success": False, "error": "xAI API key is missing",
                "error_type": "authentication", "request_count": 0, "attempts": []}
    # Retain the old argument for callers, but never send an application output cap.
    attempt_limit = max(1, min(int(max_attempts), 3))
    timeout = httpx.Timeout(connect=30, read=idle_timeout_seconds, write=30, pool=30)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(attempt_limit):
            started = time.monotonic()
            state = {"http_status": 0, "response_id": "", "event_count": 0, "last_event": "",
                     "raw_response": {}, "partial_text": "", "tool_calls_count": 0}
            payload = {"model": model, "input": prompt, "tools": [{"type": "web_search"}, {"type": "x_search"}],
                       "stream": True, "temperature": temperature}
            last_progress = 0.0
            def progress(force=False):
                nonlocal last_progress
                now = time.monotonic()
                if on_progress and (force or now - last_progress >= 10):
                    on_progress({key: state[key] for key in ("response_id", "event_count", "last_event", "tool_calls_count")} |
                                {"attempt": attempt + 1, "elapsed_seconds": round(now - started, 2)})
                    last_progress = now

            async def request():
                async with client.stream("POST", api_url, headers={"Authorization": f"Bearer {api_key}"}, json=payload) as response:
                    state["http_status"] = response.status_code
                    if response.status_code >= 400:
                        await response.aread()
                        response.raise_for_status()
                    if "text/event-stream" not in response.headers.get("content-type", ""):
                        await response.aread()
                        data = response.json()
                        if not isinstance(data, dict):
                            raise ValueError("xAI response must be a JSON object")
                        state["raw_response"] = data
                        return data
                    event_lines, items = [], {}
                    def consume():
                        chunk = "\n".join(event_lines)
                        event_lines.clear()
                        if not chunk or chunk == "[DONE]":
                            return None
                        event = json.loads(chunk)
                        if not isinstance(event, dict):
                            raise ValueError("xAI stream event must be a JSON object")
                        state["event_count"] += 1
                        kind = event.get("type", "")
                        state["last_event"] = kind
                        data = event.get("response")
                        if isinstance(data, dict):
                            state["raw_response"].update(data)
                            state["response_id"] = data.get("id") or state["response_id"]
                        if kind == "response.output_text.delta":
                            state["partial_text"] += str(event.get("delta") or "")
                        if kind == "response.output_item.done" and isinstance(event.get("item"), dict):
                            item = event["item"]
                            items[event.get("output_index", len(items))] = item
                            state["raw_response"]["output"] = list(items.values())
                            state["tool_calls_count"] = sum(row.get("type") in {"web_search_call", "x_search_call"} for row in items.values())
                        progress(kind in {"response.created", "response.completed", "response.failed", "response.incomplete", "error"})
                        if kind in {"response.completed", "response.failed", "response.incomplete"}:
                            state["raw_response"]["status"] = (data or {}).get("status") or kind.removeprefix("response.")
                            return state["raw_response"]
                        if kind == "error":
                            state["raw_response"].update(status="failed", error=event.get("error") or event)
                            return state["raw_response"]
                        return None
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            event_lines.append(line[5:].lstrip())
                        elif not line:
                            terminal = consume()
                            if terminal is not None:
                                return terminal
                    terminal = consume()
                    if terminal is not None:
                        return terminal
                    raise EOFError("xAI stream ended without a completed, incomplete or failed terminal response")

            error, error_type, retryable = "", "", False
            try:
                data = await asyncio.wait_for(request(), timeout=timeout_seconds)
                if not isinstance(data.get("output") or [], list) or not isinstance(data.get("incomplete_details") or {}, dict):
                    raise ValueError("Malformed xAI output or incomplete_details")
                state["response_id"] = data.get("id") or state["response_id"]
                state["tool_calls_count"] = sum(item.get("type") in {"web_search_call", "x_search_call"} for item in data.get("output") or [] if isinstance(item, dict))
                reason = (data.get("incomplete_details") or {}).get("reason") or data.get("finish_reason") or ""
                if reason in {"max_output_tokens", "length", "max_tokens"}:
                    error_type, retryable = "output_truncated", True
                    error = "Grok research was truncated by xAI; no application output-token limit was sent"
                elif data.get("error") or data.get("status") in {"failed", "incomplete", "cancelled"}:
                    error_type = "provider_error"
                    error = f"xAI response {data.get('status')}: {data.get('error') or reason or 'no completion reason supplied'}"
                elif data.get("status") != "completed":
                    error_type, error = "incomplete_response", "xAI did not return a completed response"
                elif not output_text(data):
                    error_type, error = "empty_research", "xAI completed without an assistant research summary"
            except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
                error_type, retryable = "timeout", True
                error = f"{type(exc).__name__}: Grok research timed out after {time.monotonic() - started:.1f}s (idle limit {idle_timeout_seconds:g}s; attempt limit {timeout_seconds:g}s)"
            except httpx.HTTPStatusError as exc:
                error_type = "http_error"
                retryable = exc.response.status_code in {408, 429, 500, 502, 503, 504}
                error = f"xAI HTTP {exc.response.status_code}: {exc.response.text[:1200]}"
            except (httpx.TransportError, EOFError) as exc:
                error_type, retryable = "transport_error", True
                error = f"{type(exc).__name__}: {str(exc) or 'xAI connection closed before completion'}"
            except (ValueError, TypeError, AttributeError) as exc:
                error_type, error = "invalid_response", f"{type(exc).__name__}: {str(exc) or 'Invalid xAI response'}"
            data = state["raw_response"]
            record = {**state, "attempt": attempt + 1, "elapsed_seconds": round(time.monotonic() - started, 2),
                      "error": error, "error_type": error_type, "status": "failed" if error else "complete",
                      "request_settings": {key: value for key, value in payload.items() if key != "input"},
                      "timeout_seconds": timeout_seconds, "idle_timeout_seconds": idle_timeout_seconds}
            attempts.append(record)
            progress(True)
            if not error:
                return {**base, "attempted": True, "success": True, "error": "", "error_type": "",
                        "summary": output_text(data), "results": cited_sources(data), "raw_response": data,
                        "request_count": len(attempts), "attempts": attempts, "usage": data.get("usage", {}),
                        "request_id": state["response_id"], "http_status": state["http_status"],
                        "tool_calls_count": state["tool_calls_count"], "finish_reason": "completed"}
            if not retryable:
                break
            if attempt + 1 < attempt_limit:
                await asyncio.sleep(1)
    last = attempts[-1]
    details = last["raw_response"].get("incomplete_details")
    return {**base, "attempted": True, "success": False, "error": last["error"], "error_type": last["error_type"],
            "request_count": len(attempts), "attempts": attempts, "raw_response": last["raw_response"],
            "usage": last["raw_response"].get("usage", {}), "request_id": last["response_id"],
            "http_status": last["http_status"], "tool_calls_count": last["tool_calls_count"],
            "finish_reason": (details.get("reason") if isinstance(details, dict) else "") or last["raw_response"].get("status", "")}
