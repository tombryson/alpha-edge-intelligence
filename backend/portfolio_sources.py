"""Retrieve text for citation-only research without substituting a model summary."""

from copy import deepcopy
from urllib.parse import urlsplit
import ipaddress
import asyncio

from .portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from .portfolio_retrieval import ParallelSourceProvider, source_key

RESEARCH_PROVIDERS = ("macro_news", "perplexity", "parallel", "tavily")  # Legacy checkpoints remain readable.


def public_url(url):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
            return False
        if host == "localhost" or host.endswith((".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host
    except ValueError:
        return False


async def extract_sources(urls, runtime=None, **context):
    return await ParallelSourceProvider().gather(runtime or CURRENT_RUNTIME.get() or PortfolioRuntime(), urls=urls, **context)


async def hydrate_citations(lanes, runtime):
    for lane in lanes:
        for provider in RESEARCH_PROVIDERS:
            if provider in lane:
                lane[provider] = deepcopy(lane[provider])
    rows = [row for lane in lanes for provider in RESEARCH_PROVIDERS
            for row in (lane.get(provider) or {}).get("results", [])]
    existing = {source_key(row["url"]): row for row in rows if row.get("url") and row.get("content")}
    # Reuse individual excerpts even when the current URL batch differs on resume.
    for entry in runtime.cache.values():
        if entry.get("receipt", {}).get("request_settings"):
            continue
        for row in entry.get("result", {}).get("results") or []:
            if row.get("url") and row.get("content"):
                existing.setdefault(source_key(row["url"]), row)
    missing = sorted({source_key(row["url"]): row["url"] for row in rows if not row.get("content") and source_key(row.get("url", "")) not in existing
                      and public_url(row.get("url", ""))}.values())
    from .portfolio_runtime import digest
    contexts = {}
    for lane in lanes:
        for provider in RESEARCH_PROVIDERS:
            result = lane.get(provider) or {}
            context = result.get("retrieval_context") or {}
            for row in result.get("results", []):
                if row.get("url"):
                    contexts[source_key(row["url"])] = context
    groups = {}
    for url in missing:
        context = contexts.get(source_key(url), {})
        group = groups.setdefault(digest(context), {"context": context, "urls": []})
        group["urls"].append(url)
    batches = [(group["urls"][offset:offset + 20], group["context"]) for group in groups.values()
               for offset in range(0, len(group["urls"]), 20)]
    runtime.plan("source_text", len(batches), group=",".join(lane.get("label", "") for lane in lanes))
    async def batch(urls, context):
        legacy = {"urls": urls, "provider": "tavily"}
        if runtime.has_research("citation_source_text", legacy):
            return await runtime.research("citation_source_text", legacy, lambda: None, required=False)
        return await extract_sources(urls, runtime, **context)
    results = await asyncio.gather(*(batch(urls, context) for urls, context in batches))
    for result in results:
        existing.update({source_key(row["url"]): row for row in result.get("results", []) if row.get("content")})
    for row in rows:
        if row.get("content") or source_key(row.get("url", "")) not in existing:
            continue
        source = existing[source_key(row["url"])]
        row["content"] = source["content"]
        row["text_provider"] = source.get("text_provider") or "retrieved_source"
        if source.get("date_provenance"):
            row["date_provenance"] = source["date_provenance"]
        if not row.get("published_at") and source.get("published_at"):
            row["published_at"] = source["published_at"]
    from .portfolio_documents import fetch_pdf_context, fetch_document_context
    if not hasattr(runtime, "document_locks"):
        runtime.document_locks = {}
        runtime.document_slots = asyncio.Semaphore(2)
    async def enrich(row):
        row.setdefault("context_coverage", "excerpt_only")
        is_pdf = str(row.get("url", "")).split("?", 1)[0].lower().endswith(".pdf")
        if not row.get("content") or not (is_pdf or row.get("context_required")):
            return
        if len(row["content"]) >= 1600 and not row.get("context_required"):
            return
        identity = digest({"url": row["url"], "excerpt": row["content"], "context_query": row.get("context_query"), "contract": "pdf-context-v1" if is_pdf else "html-context-v1"})
        async with runtime.document_locks.setdefault(identity, asyncio.Lock()):
            cache = runtime.partial.setdefault("document_sections", {})
            if identity not in cache:
                try:
                    async with runtime.document_slots:
                        fetch = fetch_pdf_context if is_pdf else fetch_document_context
                        cache[identity] = await fetch(row["url"], row.get("context_query") or row["content"])
                except Exception as exc:
                    cache[identity] = {"error": str(exc), "coverage": "excerpt_only"}
                await runtime.asave_request("document:" + identity, partial_records={"document_sections": {identity: cache[identity]}})
            context = cache[identity]
        row["document_context"] = deepcopy(context)
        if context.get("sections"):
            row["original_excerpt"] = row["content"]
            row["content"] += "\n\nPublisher context (table structure retained):\n" + "\n\n".join(
                (f"Page {section['page']}" if "page" in section else f"Section {section.get('section', '')}") + f"\n{section['text']}"
                for section in context["sections"])
            row["context_coverage"] = context["coverage"]
        elif context.get("error"):
            row["context_limitation"] = context["error"]
    await asyncio.gather(*(enrich(row) for row in rows))
    return lanes
