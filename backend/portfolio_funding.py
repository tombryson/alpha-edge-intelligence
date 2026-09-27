"""Read-only funding checks; estimates are not provider-side credit reservations."""

import asyncio
import json
import math
import os
import time
from collections import Counter
from statistics import median

import httpx

from .config import OPENROUTER_API_KEY
from .portfolio_roles import allocator_assignments_from_environment
from .portfolio_tokens import without_output_limit

_catalog = None
_catalog_at = 0


class FundingRequired(RuntimeError):
    def __init__(self, report, response=None):
        self.report = report
        self.response = response
        super().__init__(report["message"])


# Median/max input and output tokens from the September 16 run's paid receipts.
# Kept conservative until compact-workflow receipts provide a new measured baseline.
TOKEN_PROFILE = {
    "extract": (2572, 4874, 6430, 13270), "brief": (40679, 14270, 44734, 19763),
    "review": (4598, 6662, 6410, 11395), "reconcile": (186970, 13278, 186970, 13278),
    "allocation": (203467, 13896, 228902, 16330), "details": (209884, 1997, 234399, 7053),
    "commentary": (203467, 5000, 234399, 5000),
}


def work_kind(stage, prompt=None):
    if isinstance(stage, dict):
        return stage.get("work_kind") or work_kind(stage.get("stage"), stage.get("prompt"))
    if prompt:
        from .portfolio_progress import request_phase
        phase = request_phase(prompt, str(stage).split(":", 1)[0])
        return {"extraction": "extract", "briefs": "brief", "source_review": "review",
                "reconciliation": "reconcile", "details": "details", "commentary": "commentary"}.get(phase, "allocation")
    text = str(stage).lower()
    for needle, kind in (("investment details", "details"), ("extract source-linked", "extract"),
                         ("extract dated observations", "extract"), ("answer the focused research", "brief"),
                         ("build source-grounded", "brief"), ("review source support", "review"),
                         ("reconcile portfolio evidence", "reconcile"), ("explain the recorded", "commentary")):
        if needle in text:
            return kind
    return "allocation"


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


async def funding_snapshot():
    global _catalog, _catalog_at
    management_key = os.getenv("OPENROUTER_MANAGEMENT_API_KEY") or OPENROUTER_API_KEY
    async with httpx.AsyncClient(timeout=15) as client:
        async def get(path, key):
            response = await client.get("https://openrouter.ai/api/v1/" + path,
                                        headers={"Authorization": "Bearer " + (key or "")})
            response.raise_for_status()
            return response.json()["data"]
        credits = await get("credits", management_key)
        key = await get("key", OPENROUTER_API_KEY)
        if _catalog is None or time.monotonic() - _catalog_at > 300:
            _catalog = await get("models", OPENROUTER_API_KEY)
            _catalog_at = time.monotonic()
        models = _catalog
    total, used = number(credits.get("total_credits")), number(credits.get("total_usage"))
    if total is None or used is None:
        raise ValueError("Account credit balance unavailable")
    balance = max(0, total - used)
    limit = key.get("limit")
    if limit is not None:
        remaining = number(key.get("limit_remaining"))
        if remaining is None:
            raise ValueError("API-key spending allowance unavailable")
        balance = min(balance, max(0, remaining))
    return {"available_usd": balance, "prices": {row["id"]: row.get("pricing", {}) for row in models},
            "models": {row["id"]: row for row in models}}


def estimate_request(snapshot, model, messages, *, receipts=(), stage=""):
    """Forecast spend from billed usage. This is not a token limit or a reservation."""
    message_bytes = len(json.dumps(messages, ensure_ascii=False).encode())
    try:
        prompt = json.loads(messages[0].get("content", ""))
    except (IndexError, TypeError, ValueError):
        prompt = None
    kind = work_kind(stage, prompt if isinstance(prompt, dict) else None)
    samples = {}
    for row in receipts:
        if row.get("model") == model and row.get("status") == "complete" and row.get("usage"):
            identity = row.get("request_id") or row.get("input_hash") or row.get("stage")
            samples[identity] = row
    ratios, outputs = [], []
    for row in samples.values():
        usage = row["usage"]
        size = number((row.get("payload_accounting") or {}).get("message_bytes"))
        tokens = number(usage.get("prompt_tokens"))
        if size and tokens and size > 0 and tokens > 0:
            ratios.append(tokens / size)
        output = number(usage.get("completion_tokens"))
        if work_kind(row) == kind and output is not None and output >= 0:
            outputs.append(output)
    # A text approximation is only a fallback forecast, never a reason to reject a call.
    input_tokens = math.ceil(message_bytes * (median(ratios) if ratios else 1 / 3))
    output_tokens = math.ceil(median(outputs) if outputs else TOKEN_PROFILE[kind][1])
    cost = request_cost(snapshot["prices"], model, input_tokens, output_tokens)
    return {"estimated_request_usd": round(cost * 1.25, 6), "input_tokens_estimate": input_tokens,
            "output_tokens_estimate": output_tokens, "input_samples": len(ratios), "output_samples": len(outputs),
            "basis": "Same-model billed tokens per byte and same-work-type output median where available; historical/text fallback otherwise. Includes 25% cost margin; not a guaranteed bill or output limit."}


def request_cost(prices, model, input_tokens, output_tokens):
    price = prices.get(model, {})
    prompt, completion = number(price.get("prompt")), number(price.get("completion"))
    request = number(price.get("request", 0))
    if any(value is None or value < 0 for value in (prompt, completion, request)):
        raise ValueError(f"Current pricing unavailable for {model}")
    return prompt * input_tokens + completion * output_tokens + request


def estimate_plan(context, environment, previous=None):
    previous = previous or {}
    legacy = bool(previous) and previous.get("workflow_version", 1) == 1
    roles = allocator_assignments_from_environment(environment)
    judge = environment.get("PORTFOLIO_POSITIONING_DEEP_CHAIRMAN_MODEL", "openai/gpt-5.5")
    summary = environment.get("PORTFOLIO_POSITIONING_DEEP_SUMMARY_MODEL", "openai/gpt-5.5")
    synthesis = environment.get("PORTFOLIO_POSITIONING_SYNTHESIS_MODEL", judge)
    commentary = environment.get("PORTFOLIO_POSITIONING_DEEP_COMMENTARY_MODEL", judge)
    sleeves = max(1, len(context.get("asset_classes", [])), len(context.get("available_asset_classes", [])))
    batches = math.ceil(sleeves / 4)
    # Research volume is estimated, never constrained by these planning counts.
    plan = Counter({(summary, "extract"): 25, (summary, "brief"): 3,
                    (summary, "review"): 39, (summary, "reconcile"): 1})
    for role in roles:
        count = 3 if legacy and role["role"] != "blind_macro_prior" else 1
        plan[role["model"], "allocation"] += count
        if legacy:
            plan[role["model"], "details"] += count * batches
    plan[judge, "allocation"] += 3 if legacy else 1
    plan[synthesis, "allocation"] += 1
    plan[synthesis, "details"] += batches
    if not legacy:
        # Final changes can invalidate provisional cases; one bounded claim review follows.
        plan[synthesis, "details"] += batches
        defensive = next(role["model"] for role in roles if role["role"] == "defensive_regime_reviewer")
        plan[defensive, "allocation"] += 1
        # Conditional only: scoped reconsideration, affected details and updated prose.
        plan[synthesis, "allocation"] += 1
        plan[synthesis, "details"] += batches
        plan[commentary, "commentary"] += 1
        if previous.get("workflow_version", 4) >= 4:
            # New plays share final synthesis; only old checkpoints have a separate play plan.
            component_plays = bool(previous) and previous.get("play_assessment_mode", "components") == "components"
            plan[summary, "allocation"] += 3 + bool(component_plays and context.get("investment_plays"))
            plan[defensive, "allocation"] += 1  # Only if reconsideration produces new final prose.
    plan[commentary, "commentary"] += 4 if legacy else 1
    if legacy:
        plan[judge, "details"] += 3 * batches
    # Include the existing single conditional follow-up round in the funding estimate.
    plan[summary, "extract"] += 9
    plan[summary, "brief"] += 1
    plan[summary, "review"] += 52 if legacy else 13
    plan[summary, "reconcile"] += 1
    if legacy:
        plan[judge, "allocation"] += 1
        plan[judge, "details"] += batches
        plan[commentary, "commentary"] += 1
    latest = {row.get("input_hash") or row.get("stage"): row for row in previous.get("stage_receipts", [])}
    for row in latest.values():
        if row.get("status") == "complete" and row.get("request_settings"):
            key = (row.get("model"), work_kind(row))
            plan[key] = max(0, plan[key] - 1)
    return {key: count for key, count in plan.items() if count > 0}


def estimate_cost(plan, prices):
    low, high = 0.0, 0.0
    for (model, kind), count in plan.items():
        inp, out, max_inp, max_out = TOKEN_PROFILE[kind]
        low += count * request_cost(prices, model, inp, out)
        high += count * request_cost(prices, model, max_inp, max_out)
    return {"low_usd": round(low, 2), "high_usd": round(high, 2), "estimated_requests": sum(plan.values()),
            "basis": "September 16 median/max token usage, current model prices, selected workflow and one follow-up round. Retries and external-provider charges are not included; not a guaranteed price."}


async def preflight(context, environment, previous=None, reserved_usd=0):
    try:
        snapshot = await funding_snapshot()
        plan = estimate_plan(context, environment, previous)
        estimate = estimate_cost(plan, snapshot["prices"])
        paid = any(request_cost(snapshot["prices"], model, 1, 1) > 0 for model, _ in plan)
        minimum = max((request_cost(snapshot["prices"], model, 0, 0) for model, _ in plan), default=0)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return {"status": "unverified", "message": "Could not verify OpenRouter funding or model pricing. Check the server's credit-check credentials and try again.",
                "reason": type(exc).__name__}
    available = max(0, snapshot["available_usd"] - reserved_usd)
    needed = estimate["high_usd"]
    # A historical whole-run forecast is not a provider charge or an execution plan.
    sufficient = (not paid or available > 0) and available >= minimum
    return {"status": "ready" if sufficient else "insufficient", "available_usd": round(available, 2),
            "reserved_usd": round(reserved_usd, 2), "estimate": estimate,
            "top_up_usd": round(max(0, needed - available), 2),
            "estimate_advisory": True, "low_balance_warning": available < needed,
            "unchecked_providers": ["Parallel"],
            "message": (f"OpenRouter credit ${available:.2f}; estimated remaining cost ${estimate['low_usd']:.2f}-${needed:.2f}."
                        + " This estimate is advisory, not a completion guarantee. Each paid request is checked separately."
                        + ("" if sufficient else " The available balance cannot cover a paid request or its fixed charge; add credit before starting."))}


class FundingGuard:
    """Check each uncached request; allow existing in-flight calls to finish."""
    def __init__(self):
        self.lock = asyncio.Lock()
        self.reserved = 0.0
        self.reserved_minimum = 0.0
        self.waiting = None
        self.inflight = 0
        self.inflight_limit = None
        self.retry_not_before = 0.0
        self.draining = False
        self.capacity_changed = asyncio.Event()

    async def start(self, context, previous=None):
        report = await preflight(context, os.environ, previous)
        if report["status"] != "ready":
            self.waiting = report
            raise FundingRequired(report)

    async def call(self, client, model, messages, *, receipts=(), stage="", **kwargs):
        kwargs = without_output_limit(kwargs)
        while True:
            async with self.lock:
                if self.waiting:
                    raise FundingRequired(self.waiting)
                delay = max(0.0, self.retry_not_before - time.monotonic())
                busy = (self.draining and self.inflight > 0) or (
                    self.inflight_limit is not None and self.inflight >= self.inflight_limit)
                if delay or busy:
                    capacity_changed = self.capacity_changed
                else:
                    self.draining = False
                    try:
                        snapshot = await funding_snapshot()
                        estimate = estimate_request(snapshot, model, messages, receipts=receipts, stage=stage)
                        quote = estimate["estimated_request_usd"]
                        minimum = request_cost(snapshot["prices"], model, 0, 0)
                        available = snapshot["available_usd"]
                        paid = request_cost(snapshot["prices"], model, 1, 1) > 0
                        # Forecasts remain advisory; a provider reservation response controls admission.
                        if (paid and available <= 0) or available - self.reserved_minimum < minimum:
                            self.waiting = {"status": "insufficient", "available_usd": available,
                                "next_request_usd": minimum, "estimate": estimate,
                                "message": "OpenRouter balance cannot cover a paid request or its fixed charge. Completed work is saved; add credit to continue."}
                        estimate.update(available_usd=available, other_inflight_estimate_usd=self.reserved,
                            low_balance_warning=available - self.reserved < quote)
                    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                        self.waiting = {"status": "unverified", "reason": str(exc),
                            "message": "Credit or model-capacity check unavailable. Completed work is saved; retry recovery when the credit service is reachable."}
                    if self.waiting:
                        raise FundingRequired(self.waiting)
                    self.reserved += quote
                    self.reserved_minimum += minimum
                    self.inflight += 1
                    break
            if delay:
                await asyncio.sleep(delay)
            else:
                await capacity_changed.wait()
        try:
            response = await client(model, messages, **kwargs)
            if isinstance(response, dict) and response.get("error_status") == 402:
                if (response.get("error_reason") == "in_flight_budget_exhausted" and response.get("request_accepted") is False
                        and not response.get("id") and not response.get("outcome_uncertain")):
                    async with self.lock:
                        self.draining = True
                        self.inflight_limit = max(1, self.inflight - 1)
                        retry_delay = number(response.get("retry_after_seconds"))
                        self.retry_not_before = max(self.retry_not_before,
                            time.monotonic() + max(0.0, retry_delay if retry_delay is not None else 30.0))
                    # Runtime owns retries and records each rejected attempt separately.
                    response = {**response, "error_type": "in_flight_budget", "error_retryable": True}
                else:
                    self.waiting = {"status": "insufficient", "message": "OpenRouter requested more credit. Completed work is saved; add credit and recover this run."}
                    raise FundingRequired(self.waiting, response=response)
            return {**response, "funding_estimate": estimate} if isinstance(response, dict) else response
        finally:
            async with self.lock:
                self.reserved -= quote
                self.reserved_minimum -= minimum
                self.inflight -= 1
                self.capacity_changed.set()
                self.capacity_changed = asyncio.Event()
