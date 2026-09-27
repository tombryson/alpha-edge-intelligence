"""OpenRouter API client for making LLM requests."""

import asyncio
import json
import logging
import httpx
from typing import List, Dict, Any, Optional, Callable
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL
from .reasoning import build_reasoning_payload, normalize_reasoning_effort

logger = logging.getLogger(__name__)
_TRANSIENT_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_TRANSIENT_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    asyncio.TimeoutError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
)


def _build_error_response(
    *,
    model: str,
    status: Optional[int] = None,
    body: str = "",
    error_type: str,
    error_message: str,
    retryable: bool,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    result = {
        "content": "",
        "provider": "openrouter",
        "model": model,
        "error": error_message,
        "error_type": error_type,
        "error_status": status,
        "error_body": body[:1000],
        "error_retryable": bool(retryable),
    }
    try:
        data = json.loads(body)
        error = data.get("error", data) if isinstance(data, dict) else {}
        metadata = (error.get("metadata") or {}) if isinstance(error, dict) else {}
        reason = metadata.get("reason")
        if reason:
            result["error_reason"] = reason
        if status == 402 and reason == "in_flight_budget_exhausted" and headers is not None:
            result.update(error_type="in_flight_budget", error_retryable=True,
                request_accepted=False, error="openrouter_in_flight_budget_exhausted")
        retry_after = (headers or {}).get("retry-after") or (headers or {}).get("Retry-After")
        retry_after = retry_after if retry_after is not None else (metadata.get("headers") or {}).get("Retry-After")
        if retry_after is not None:
            from email.utils import parsedate_to_datetime
            from datetime import datetime, timezone
            try:
                delay = float(retry_after)
            except (ValueError, TypeError):
                delay = (parsedate_to_datetime(str(retry_after)) - datetime.now(timezone.utc)).total_seconds()
            if 0 <= delay < float("inf"):
                result["retry_after_seconds"] = delay
    except (ValueError, TypeError, AttributeError, OverflowError):
        pass
    return result


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    max_tokens: Optional[int] = None,
    reasoning_effort: str = "",
    include_error_details: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable] = None,
    provider_preferences: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        max_tokens: Optional completion token cap for the model response
        reasoning_effort: Optional reasoning effort override
        include_error_details: When true, return structured failure metadata
            instead of None so callers can distinguish permanent from retryable
            errors.

    Returns:
        Response dict with 'content' and metadata, or None if failed.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }
    if provider_preferences:
        payload["provider"] = provider_preferences
    if response_format is not None:
        payload["response_format"] = response_format
    if isinstance(max_tokens, int) and max_tokens > 0:
        payload["max_tokens"] = int(max_tokens)
    effort = normalize_reasoning_effort(reasoning_effort)
    payload["reasoning"] = build_reasoning_payload(
        model=model,
        effort=effort,
        provider="openrouter",
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if on_progress is not None:
                return await _stream_model(client, headers, payload, on_progress)
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            choices = data.get("choices") or []
            choice = choices[0] if choices else {}
            provider_error = data.get("error") or choice.get("error")
            if provider_error or choice.get("finish_reason") == "error" or not choices:
                if not include_error_details:
                    return None
                detail = provider_error if isinstance(provider_error, dict) else {}
                code = detail.get("code")
                status = code if isinstance(code, int) else None
                result = _build_error_response(model=model, status=status,
                    body=json.dumps(provider_error or {}, ensure_ascii=False)[:1000],
                    error_type="provider_error" if provider_error else "empty_response",
                    error_message=str(detail.get("message") or provider_error or "Provider returned no completed choice")[:500],
                    retryable=status in _TRANSIENT_HTTP_STATUS_CODES or (not provider_error and not choices))
                result.update(id=data.get("id"), usage=data.get("usage"), finish_reason=choice.get("finish_reason"))
                return result
            message = choice.get("message") or {}
            raw_content = message.get("content")
            content: str = ""
            if isinstance(raw_content, str):
                content = raw_content
            elif isinstance(raw_content, list):
                parts: List[str] = []
                for item in raw_content:
                    if not isinstance(item, dict):
                        continue
                    text_part = item.get("text")
                    if isinstance(text_part, str) and text_part:
                        parts.append(text_part)
                content = "\n".join(parts).strip()
            elif raw_content is not None:
                content = str(raw_content)

            return {
                "content": content,
                "reasoning_details": message.get("reasoning_details"),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage"),
                "id": data.get("id"),
                "provider": data.get("provider"),
                "requested_model": model,
                "resolved_model": data.get("model"),
            }

    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = (e.response.text or "") if e.response is not None else ""
        logger.error("Error querying model %s: HTTP %s body=%s", model, status, body[:500])
        if include_error_details:
            status_int = status if isinstance(status, int) else None
            body_lower = body.lower()
            if status_int == 402 and (
                "more credits" in body_lower
                or "can only afford" in body_lower
                or "\"code\":402" in body_lower
            ):
                return _build_error_response(
                    model=model,
                    status=status_int,
                    body=body,
                    error_type="insufficient_credits",
                    error_message=f"openrouter_insufficient_credits_http_{status_int}",
                    retryable=False,
                    headers=dict(e.response.headers),
                )
            return _build_error_response(
                model=model,
                status=status_int,
                body=body,
                error_type="http_error",
                error_message=f"openrouter_http_{status}",
                retryable=status_int in _TRANSIENT_HTTP_STATUS_CODES,
                headers=dict(e.response.headers) if e.response is not None else None,
            )
        return None
    except Exception as e:
        causes = []
        cause = e.__cause__
        while cause is not None and len(causes) < 4:
            causes.append(f"{type(cause).__name__}: {cause}")
            cause = cause.__cause__
        logger.error("Error querying model %s: %s: %s; causes=%s", model, type(e).__name__, e, causes)
        if include_error_details:
            error_type = "timeout" if isinstance(e, (httpx.TimeoutException, asyncio.TimeoutError)) else "transport_error"
            result = _build_error_response(
                model=model,
                error_type=error_type,
                error_message=f"openrouter_{type(e).__name__.lower()}",
                retryable=isinstance(e, _TRANSIENT_TRANSPORT_ERRORS),
            )
            result["error_causes"] = [cause[:500] for cause in causes]
            return result
        return None


def _terminal_stream_failure(model, error, metadata, content, reasoning):
    code = error.get("code") if isinstance(error, dict) else None
    status = code if type(code) is int else None
    failure = _build_error_response(model=model, status=status,
        body=json.dumps({"error": error}), error_type="stream_error",
        error_message=str(error.get("message") or error) if isinstance(error, dict) else str(error),
        retryable=status in _TRANSIENT_HTTP_STATUS_CODES)
    return {**failure, **metadata, "content": content, "reasoning_details": reasoning,
        "request_accepted": True, "outcome_uncertain": False, "terminal_error": True,
        "finish_reason": "error", "requested_model": model, "resolved_model": metadata.get("model")}


async def _stream_model(client, headers, payload, on_progress):
    """Read SSE without imposing a generation deadline; retain partial output on failure."""
    parts, reasoning, metadata = [], [], {}
    finished = None
    try:
        async with client.stream("POST", OPENROUTER_API_URL, headers=headers,
                json={**payload, "stream": True, "stream_options": {"include_usage": True}}) as response:
            if response.is_error:
                await response.aread()
                response.raise_for_status()
            if response.headers.get("x-generation-id"):
                metadata["id"] = response.headers["x-generation-id"]
            await on_progress({"activity": "provider_connected", **metadata})
            if "application/json" in response.headers.get("content-type", ""):
                await response.aread()
                data = response.json()
                for key in ("id", "model", "provider", "usage"):
                    if data.get(key) is not None:
                        metadata[key] = data[key]
                choice = (data.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content") or ""
                if not isinstance(content, str):
                    raise ValueError("Unrecognized provider content")
                parts.append(content)
                reasoning = (choice.get("message") or {}).get("reasoning_details") or []
                await on_progress({"activity": "receiving_text", **metadata, "content_delta": content})
                error = data.get("error") or choice.get("error")
                if error or choice.get("finish_reason") == "error":
                    return _terminal_stream_failure(payload["model"], error or {"message": "Provider stream failed"},
                        metadata, content, reasoning)
                if not choice.get("finish_reason"):
                    return {**metadata, "content": content, "reasoning_details": reasoning,
                        "error": "Incomplete provider response; received output retained.",
                        "error_type": "incomplete_stream", "error_retryable": False, "outcome_uncertain": True}
                return {**metadata, "content": content, "reasoning_details": reasoning, "finish_reason": choice["finish_reason"],
                    "requested_model": payload["model"], "resolved_model": metadata.get("model")}
            async for line in response.aiter_lines():
                if line.startswith(":"):
                    await on_progress({"activity": "provider_heartbeat"})
                    continue
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if value == "[DONE]":
                    break
                if not value:
                    continue
                chunk = json.loads(value)
                for key in ("id", "model", "provider", "usage"):
                    if chunk.get(key) is not None:
                        metadata[key] = chunk[key]
                choice = next((row for row in chunk.get("choices", []) if row.get("index", 0) == 0), {})
                delta = choice.get("delta") or {}
                content = delta.get("content") or ""
                if isinstance(content, list):
                    content = "".join(row.get("text", "") for row in content if isinstance(row, dict))
                if not isinstance(content, str):
                    raise ValueError("Unrecognized streamed content")
                parts.append(content)
                details = delta.get("reasoning_details") or []
                if details:
                    reasoning.extend(details)
                if delta.get("reasoning"):
                    reasoning.append({"type": "reasoning.text", "text": delta["reasoning"]})
                if choice.get("finish_reason"):
                    finished = choice["finish_reason"]
                await on_progress({"activity": "receiving_text" if content else "provider_working",
                    "content_delta": content, "reasoning_delta": details or delta.get("reasoning"), **metadata})
                if chunk.get("error") or choice.get("error") or finished == "error":
                    return _terminal_stream_failure(payload["model"],
                        chunk.get("error") or choice.get("error") or {"message": "Provider stream failed"},
                        metadata, "".join(parts), reasoning)
        if not finished:
            return {**metadata, "content": "".join(parts), "reasoning_details": reasoning,
                "error": "Connection ended without a completed provider response; received output retained.",
                "error_type": "incomplete_stream", "error_retryable": False, "outcome_uncertain": True}
        return {**metadata, "content": "".join(parts), "reasoning_details": reasoning,
            "finish_reason": finished, "requested_model": payload["model"], "resolved_model": metadata.get("model")}
    except httpx.HTTPStatusError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        return {**metadata, "content": "".join(parts), "reasoning_details": reasoning,
            "error": str(exc) or type(exc).__name__, "error_type": "incomplete_stream",
            "error_retryable": isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)),
            "outcome_uncertain": not isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))}


query_model.supports_progress = True
query_model.supports_provider_preferences = True


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    max_tokens: Optional[int] = None,
    reasoning_effort: str = "",
    on_model_complete: Optional[Callable[[str, Optional[Dict[str, Any]], int, int], None]] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        timeout: Per-model request timeout in seconds
        max_tokens: Optional completion token cap applied to every model
        reasoning_effort: Optional reasoning effort override applied to every model
        on_model_complete: Optional progress callback (model, response, completed, total)

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    async def _run_model(model: str) -> tuple[str, Optional[Dict[str, Any]]]:
        return model, await query_model(
            model,
            messages,
            timeout=timeout,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )

    tasks = [asyncio.create_task(_run_model(model)) for model in models]
    responses: Dict[str, Optional[Dict[str, Any]]] = {}
    total = len(tasks)
    completed = 0

    for task in asyncio.as_completed(tasks):
        model, response = await task
        responses[model] = response
        completed += 1
        if on_model_complete is not None:
            try:
                on_model_complete(model, response, completed, total)
            except Exception:
                # Progress callbacks are advisory only; never fail the model run.
                pass

    return responses
