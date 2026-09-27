"""Persisted runtime model-routing settings for Alpha Edge Intelligence.

The registry deliberately exposes a small, reviewed set of model variables.
It is not a general environment-variable editor: provider credentials, timeouts,
and unrelated feature flags remain outside this operational surface.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .portfolio_roles import (
    ALLOCATOR_ROLES,
    DEFAULT_ALLOCATOR_MODELS,
    DEFAULT_ALLOCATOR_JUDGE_MODEL,
    LEGACY_ALLOCATOR_KEY,
    MODEL_ID_RE,
    legacy_allocator_assignments,
    normalize_allocator_assignment,
    validate_allocator_assignments,
)

_MODEL_ID_RE = MODEL_ID_RE
_SHARED_COUNCIL_KEYS = ("PERPLEXITY_STAGE1_OPENROUTER_MODELS", "COUNCIL_MODELS")
_STORE_LOCK = threading.RLock()
_STORE_PATH = Path(
    os.getenv(
        "MODEL_ROUTING_STORE",
        str(Path(os.getenv("ANALYSIS_OUTPUTS_DIR", "outputs")) / "model_routing.json"),
    )
)
_MAX_AUDIT_ROWS = 120

# These are deliberately curated release records, rather than dates scraped at
# request time. Provider aliases and quietly revised endpoints need operator
# review before they can be described as fresh or dated in the routing UI.
_MODEL_FRESHNESS_REGISTRY: Dict[str, Dict[str, str]] = {
    "openai/gpt-5.6-sol": {
        "released_at": "2026-07-09",
        "date_basis": "Provider release",
        "source_url": "https://openai.com/index/gpt-5-6/",
    },
    "google/gemini-3.7-flash": {
        "released_at": "2026-08-13",
        "date_basis": "Provider release",
        "source_url": "https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-3-7-flash/",
    },
    "anthropic/claude-sonnet-5": {
        "released_at": "2026-06-30",
        "date_basis": "Provider release",
        "source_url": "https://www.anthropic.com/news/claude-sonnet-5",
    },
    "x-ai/grok-4.6": {
        "released_at": "2026-08-12",
        "date_basis": "Provider release",
        "source_url": "https://x.ai/news/grok-4-6",
    },
    "qwen/qwen3.8-flash": {
        "released_at": "2026-08-27",
        "date_basis": "Reviewed provider catalogue date",
    },
    "z-ai/glm-5.3-flash": {
        "released_at": "2026-08-26",
        "date_basis": "Reviewed provider catalogue date",
    },
    "moonshotai/kimi-k3": {
        "released_at": "2026-07-16",
        "date_basis": "Reviewed provider catalogue date",
    },
    "thinkingmachines/inkling": {
        "released_at": "2026-07-17",
        "date_basis": "Reviewed provider catalogue date",
    },
    "deepseek/deepseek-v4-pro-0813": {
        "released_at": "2026-08-13",
        "date_basis": "Versioned endpoint date",
    },
    "deepseek/deepseek-v4-flash-0731": {
        "released_at": "2026-07-31",
        "date_basis": "Versioned endpoint date",
    },
    "meituan/longcat-2.0": {
        "released_at": "2026-07-20",
        "date_basis": "Reviewed provider catalogue date",
    },
}
_MODEL_FRESHNESS_VERIFIED_AT = "2026-08-30"
_CURRENT_MODEL_AGE_DAYS = 90
_AGEING_MODEL_AGE_DAYS = 180


MODEL_ROUTE_SPECS: tuple[Dict[str, Any], ...] = (
    {
        "id": "council.prepass-web-research",
        "app": "Analyst Council",
        "layer": "Prepass · Web research",
        "key": "COUNCIL_PREPASS_WEB_PROCESSOR",
        "kind": "single",
        "provider": "Parallel",
        "default": "ultra2x",
        "description": "Discovers material primary sources. Native ASX discovery, full-document decoding and worker summaries remain separate.",
    },
    {
        "id": "council.perplexity-stage1",
        "app": "Analyst Council",
        "layer": "Stage 1 · Perplexity research lane",
        "key": "PERPLEXITY_COUNCIL_MODELS",
        "kind": "list",
        "provider": "Perplexity",
        "default": ["openai/gpt-5.6-sol", "google/gemini-3.7-flash", "anthropic/claude-sonnet-5"],
        "description": "Independent evidence-backed analyses. Unsupported models may be removed by preflight for a run.",
    },
    {
        "id": "council.openrouter-stage1",
        "app": "Analyst Council",
        "layer": "Stage 1 · OpenRouter analysis lane",
        "key": "PERPLEXITY_STAGE1_OPENROUTER_MODELS",
        "kind": "list",
        "provider": "OpenRouter",
        "default": [
            "x-ai/grok-4.6", "qwen/qwen3.8-flash", "z-ai/glm-5.3-flash",
            "moonshotai/kimi-k3", "thinkingmachines/inkling", "deepseek/deepseek-v4-pro-0813",
            "meituan/longcat-2.0",
        ],
        "description": "Stage 1 analysis and Stage 2 judging use the same models. Editing either list updates both.",
    },
    {
        "id": "council.local-stage1-and-stage2",
        "app": "Analyst Council",
        "layer": "Local Stage 1 and Stage 2 judge pool",
        "key": "COUNCIL_MODELS",
        "kind": "list",
        "provider": "OpenRouter",
        "default": [
            "x-ai/grok-4.6", "qwen/qwen3.8-flash", "z-ai/glm-5.3-flash",
            "moonshotai/kimi-k3", "thinkingmachines/inkling", "deepseek/deepseek-v4-pro-0813",
            "meituan/longcat-2.0",
        ],
        "description": "Shared with the OpenRouter analysis lane. Editing either list updates both.",
    },
    {
        "id": "council.chairman",
        "app": "Analyst Council",
        "layer": "Stage 3 · Chairman",
        "key": "CHAIRMAN_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3.7-flash",
        "description": "Synthesises the final council verdict from Stage 1 and Stage 2 outputs.",
    },
    {
        "id": "council.analyst-memo",
        "app": "Analyst Council",
        "layer": "Stage 3 · Analyst memo",
        "key": "STAGE3_ANALYST_MEMO_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3-flash-preview",
        "description": "Writes the human-readable council memo after structured synthesis.",
    },
    {
        "id": "council.json-normalizer",
        "app": "Analyst Council",
        "layer": "Stage 3 · JSON normalizer",
        "key": "CHAIRMAN_JSONIFIER_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3.1-flash-lite-preview",
        "description": "Normalises structured chairman output when JSON repair is required.",
    },
    {
        "id": "council.reference-parser",
        "app": "Analyst Council",
        "layer": "Stage 3 · Reference parser",
        "key": "STAGE1_REFERENCE_PARSER_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3.1-flash-lite-preview",
        "description": "Extracts the Stage 1 reference table used by the analyst memo.",
    },
    {
        "id": "portfolio.macro-news",
        "app": "Portfolio Analysis",
        "layer": "Evidence · Macro and news retrieval",
        "key": "PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR",
        "kind": "single",
        "provider": "Parallel",
        "default": "ultra2x",
        "description": "Initial discovery uses Parallel Search. This processor is retained for already-paid macro research tasks on recovery.",
    },
    {
        "id": "portfolio.source-retrieval",
        "app": "Portfolio Analysis",
        "layer": "Evidence · Focused source research",
        "key": "PORTFOLIO_POSITIONING_SOURCE_PROCESSOR",
        "kind": "single",
        "provider": "Parallel",
        "default": "ultra2x",
        "description": "Deep-research processor for material questions still unresolved after Search and selective Extract. Existing evidence is reused first.",
    },
    {
        "id": "portfolio.deep-summary",
        "app": "Portfolio Analysis",
        "layer": "Evidence summary",
        "key": "PORTFOLIO_POSITIONING_DEEP_SUMMARY_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "openai/gpt-6-luna-pro",
        "description": "Extracts source-linked observations, checks answer coverage and reconciles evidence. Research direction uses the decision model.",
    },
    *({
        "id": role["id"],
        "app": "Portfolio Analysis",
        "layer": role["label"],
        "role": role["role"],
        "key": role["key"],
        "kind": "role",
        "provider": "OpenRouter",
        "default": legacy_allocator_assignments(list(DEFAULT_ALLOCATOR_MODELS))[role["key"]],
        "description": role["description"],
    } for role in ALLOCATOR_ROLES),
    {
        "id": "portfolio.deep-chairman",
        "app": "Portfolio Analysis",
        "layer": "Allocator judge",
        "key": "PORTFOLIO_POSITIONING_DEEP_CHAIRMAN_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "anthropic/claude-opus-5.5",
        "description": "Plans decision-relevant research and compares the independent and current-aware portfolios using specialist critiques.",
    },
    {
        "id": "portfolio.deep-commentary",
        "app": "Portfolio Analysis",
        "layer": "Commentary",
        "key": "PORTFOLIO_POSITIONING_DEEP_COMMENTARY_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "anthropic/claude-opus-5.5",
        "description": "Writes the asset-class commentary after the allocator decision.",
    },
    {
        "id": "portfolio.synthesis",
        "app": "Portfolio Analysis",
        "layer": "Final allocation synthesis",
        "key": "PORTFOLIO_POSITIONING_SYNTHESIS_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "anthropic/claude-opus-5.5",
        "description": "Resolves allocator proposals and follow-up evidence into the final allocation.",
    },
    {
        "id": "router.semantic-adjudicator",
        "app": "Announcement Router",
        "layer": "Ambiguity · Semantic adjudicator",
        "key": "SCENARIO_ROUTER_MODEL_ADJUDICATION_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3.1-flash-lite",
        "description": "Evidence-bounds ambiguous watchlist and thesis-condition matches.",
    },
    {
        "id": "router.thesis-judge",
        "app": "Announcement Router",
        "layer": "Classification · Thesis judge",
        "key": "SCENARIO_ROUTER_THESIS_JUDGE_MODEL",
        "kind": "single",
        "provider": "OpenRouter",
        "default": "google/gemini-3.1-flash-lite",
        "description": "Classifies a new filing against the saved company thesis.",
    },
    {
        "id": "market.core-asset-resolver",
        "app": "Market Intelligence",
        "layer": "Resources · Commodity exposure resolver",
        "key": "CRITICAL_MINERALS_CORE_ASSET_XAI_MODEL",
        "kind": "single",
        "provider": "xAI",
        "default": "grok-4-1-fast-reasoning",
        "description": "Resolves ambiguous or multi-commodity resource exposure before supported benchmark prices are injected.",
    },
    {
        "id": "market.company-type-detector",
        "app": "Market Intelligence",
        "layer": "Company setup · Template classifier",
        "key": "COMPANY_TYPE_DETECTION_PERPLEXITY_MODEL",
        "kind": "single",
        "provider": "Perplexity",
        "default": "sonar-pro",
        "description": "Classifies the company type used to select a research template.",
    },
)

_SPECS_BY_ID = {str(spec["id"]): spec for spec in MODEL_ROUTE_SPECS}
_SPECS_BY_KEY = {str(spec["key"]): spec for spec in MODEL_ROUTE_SPECS}

PORTFOLIO_ROUTE_GROUPS = (
    {"id": "portfolio.group-research", "layer": "Research", "provider": "Parallel",
     "members": ("portfolio.macro-news", "portfolio.source-retrieval"),
     "description": "Search and selective Extract handle discovery. This processor handles justified deep-research escalation."},
    {"id": "portfolio.group-evidence", "layer": "Evidence Processing", "provider": "OpenRouter",
     "members": ("portfolio.deep-summary",),
     "description": "Source extraction, evidence summaries and research coverage checks."},
    {"id": "portfolio.group-analysis", "layer": "Allocation & Review", "provider": "OpenRouter",
     "members": tuple(role["id"] for role in ALLOCATOR_ROLES),
     "description": "Independent and current-portfolio views, exposure comparisons and defensive review."},
    {"id": "portfolio.group-decision", "layer": "Decision & Memo", "provider": "OpenRouter",
     "members": ("portfolio.deep-chairman", "portfolio.synthesis", "portfolio.deep-commentary"),
     "description": "Research direction, allocation comparison, final synthesis and written commentary."},
)
_GROUPS_BY_ID = {group["id"]: group for group in PORTFOLIO_ROUTE_GROUPS}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _model_freshness(model: str, *, today: Optional[date] = None) -> Dict[str, Any]:
    """Return reviewed release metadata for one configured model identifier."""
    record = _MODEL_FRESHNESS_REGISTRY.get(model)
    if record is None:
        return {
            "model": model,
            "status": "unverified",
            "released_at": None,
            "age_days": None,
            "date_basis": "No reviewed release date",
            "last_verified_at": None,
            "source_url": None,
        }

    released_at = date.fromisoformat(record["released_at"])
    age_days = max(0, ((today or date.today()) - released_at).days)
    if age_days <= _CURRENT_MODEL_AGE_DAYS:
        status = "current"
    elif age_days <= _AGEING_MODEL_AGE_DAYS:
        status = "ageing"
    else:
        status = "stale"
    return {
        "model": model,
        "status": status,
        "released_at": released_at.isoformat(),
        "age_days": age_days,
        "date_basis": record["date_basis"],
        "last_verified_at": _MODEL_FRESHNESS_VERIFIED_AT,
        "source_url": record.get("source_url"),
    }


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "overrides": {}, "audit": []}


def _load_store() -> Dict[str, Any]:
    with _STORE_LOCK:
        try:
            payload = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return _empty_store()
        if not isinstance(payload, dict):
            return _empty_store()
        overrides = payload.get("overrides") if isinstance(payload.get("overrides"), dict) else {}
        audit = payload.get("audit") if isinstance(payload.get("audit"), list) else []
        result = {"version": payload.get("version", 1), "overrides": overrides, "audit": audit[-_MAX_AUDIT_ROWS:]}
        if "portfolio_allocator_defaults" in payload:
            result["portfolio_allocator_defaults"] = payload["portfolio_allocator_defaults"]
        return result


def _save_store(payload: Dict[str, Any]) -> None:
    with _STORE_LOCK:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = _STORE_PATH.with_suffix(f"{_STORE_PATH.suffix}.tmp")
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_path, _STORE_PATH)


def _load_portfolio_store() -> Dict[str, Any]:
    """Freeze the pre-migration assignments once, so resets cannot shift roles."""
    with _STORE_LOCK:
        store = _load_store()
        needs_initial_assignments = "portfolio_allocator_defaults" not in store
        needs_required_roles = store["version"] in (1, 2)
        if not needs_initial_assignments and not needs_required_roles:
            return store
        judge_spec = _SPECS_BY_ID["portfolio.deep-chairman"]
        judge_model = _normalise_value(
            judge_spec,
            store["overrides"].get(judge_spec["key"], os.getenv(judge_spec["key"]) or DEFAULT_ALLOCATOR_JUDGE_MODEL),
        )
        if "portfolio_allocator_defaults" not in store:
            legacy = store["overrides"].get(
                LEGACY_ALLOCATOR_KEY,
                os.getenv(LEGACY_ALLOCATOR_KEY, ",".join(DEFAULT_ALLOCATOR_MODELS)),
            )
            defaults = legacy_allocator_assignments(legacy, default_model=judge_model)
            store["portfolio_allocator_defaults"] = defaults
        else:
            defaults = store["portfolio_allocator_defaults"]
            # Convert the optional-role preview without losing assigned models.
            for values in (defaults, store["overrides"]):
                if not isinstance(values, dict):
                    continue
                for role in ALLOCATOR_ROLES:
                    previous = values.get(role["key"])
                    if not isinstance(previous, dict) or "enabled" not in previous:
                        continue
                    model = previous.get("model", "")
                    if previous["enabled"] is False and isinstance(model, str) and not model.strip():
                        model = judge_model
                    values[role["key"]] = {"model": model}
        store["version"] = 3
        if isinstance(defaults, dict):
            for role in ALLOCATOR_ROLES:
                store["audit"].append({
                    "at": _utc_now(), "actor": "system", "action": "migrate_role",
                    "route_id": role["id"], "key": role["key"],
                    "effective_value": store["overrides"].get(role["key"], defaults.get(role["key"])),
                })
        store["audit"] = store["audit"][-_MAX_AUDIT_ROWS:]
        _save_store(store)
        return store


def _configured_value(spec: Dict[str, Any], store: Optional[Dict[str, Any]] = None) -> tuple[Any, str]:
    if spec["kind"] == "role":
        if spec["key"] in os.environ:
            try:
                return json.loads(os.environ[spec["key"]]), "environment"
            except ValueError as exc:
                raise ValueError(f"{spec['layer']}: invalid named role configuration.") from exc
        if any(role["key"] in os.environ for role in ALLOCATOR_ROLES):
            raise ValueError(f"{spec['layer']}: missing named role configuration.")
        defaults = (store or {}).get("portfolio_allocator_defaults")
        if defaults is not None:
            if not isinstance(defaults, dict) or spec["key"] not in defaults:
                raise ValueError(f"{spec['layer']}: missing saved role assignment.")
            return defaults[spec["key"]], "migrated"
        return spec["default"], "code_default"
    raw = os.getenv(str(spec["key"]), "").strip()
    if spec["kind"] == "list":
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return (values or list(spec["default"]), "environment" if values else "code_default")
    return (raw or str(spec["default"]), "environment" if raw else "code_default")


def _normalise_value(spec: Dict[str, Any], value: Any) -> Any:
    if spec["kind"] == "role":
        return normalize_allocator_assignment(value, spec["layer"])
    if spec["kind"] == "list":
        items = value if isinstance(value, list) else re.split(r"[,\n]", str(value or ""))
        normalized: List[str] = []
        seen: set[str] = set()
        for item in items:
            model = str(item or "").strip()
            if not model:
                continue
            if not _MODEL_ID_RE.fullmatch(model):
                raise ValueError(f"Invalid model identifier: {model}")
            if model not in seen:
                normalized.append(model)
                seen.add(model)
        if not normalized:
            raise ValueError("Provide at least one model identifier")
        return normalized
    model = str(value or "").strip()
    if spec["provider"] == "Parallel" and not re.fullmatch(r"[a-z][a-z0-9-]*", model):
        raise ValueError("Provide a Parallel processor name, such as ultra4x")
    if not _MODEL_ID_RE.fullmatch(model):
        raise ValueError("Provide one valid model identifier")
    return model


def get_runtime_model_value(key: str, fallback: Any) -> Any:
    """Return a saved override for a reviewed key, otherwise the caller fallback."""
    if key in _SHARED_COUNCIL_KEYS:
        return _shared_council_value(_load_store())[0]
    spec = _SPECS_BY_KEY.get(str(key))
    if spec is None:
        return fallback
    override = _load_store()["overrides"].get(spec["key"])
    if override is None:
        return fallback
    try:
        return _normalise_value(spec, override)
    except ValueError:
        return fallback


def get_runtime_model_list(key: str, fallback: List[str]) -> List[str]:
    value = get_runtime_model_value(key, fallback)
    if isinstance(value, list):
        return list(value)
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def get_portfolio_allocator_assignments(store: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    active_store = _load_portfolio_store() if store is None else store
    values = {}
    for role in ALLOCATOR_ROLES:
        key = role["key"]
        if key in active_store["overrides"]:
            values[key] = active_store["overrides"][key]
        else:
            values[key] = _configured_value(_SPECS_BY_KEY[key], active_store)[0]
    return validate_allocator_assignments(values)


def runtime_model_environment(*, include_portfolio_roles: bool = True) -> Dict[str, str]:
    """Return persisted overrides in subprocess-ready environment form."""
    store = _load_portfolio_store() if include_portfolio_roles else _load_store()
    overrides = store["overrides"]
    result: Dict[str, str] = {}
    for key, value in overrides.items():
        spec = _SPECS_BY_KEY.get(str(key))
        if spec is None:
            continue
        if spec["kind"] == "role":
            continue
        try:
            normalized = _normalise_value(spec, value)
        except ValueError:
            continue
        result[key] = ",".join(normalized) if isinstance(normalized, list) else normalized
    shared = ",".join(_shared_council_value(store)[0])
    for key in _SHARED_COUNCIL_KEYS:
        result[key] = shared
    if include_portfolio_roles:
        assignments = get_portfolio_allocator_assignments(store)
        by_role = {row["role"]: row for row in assignments}
        for role in ALLOCATOR_ROLES:
            assignment = by_role[role["role"]]
            result[role["key"]] = json.dumps({"model": assignment["model"]})
    return result


def _shared_council_value(store: Dict[str, Any], *, configured_only: bool = False) -> tuple[List[str], str]:
    # Preserve the latest operator edit when migrating previously independent lists.
    keys = list(_SHARED_COUNCIL_KEYS)
    if not configured_only:
        edited = [row.get("key") for row in reversed(store["audit"]) if row.get("key") in keys]
        for key in dict.fromkeys(edited + keys):
            if key in store["overrides"]:
                try:
                    return _normalise_value(_SPECS_BY_KEY[key], store["overrides"][key]), "runtime_override"
                except ValueError:
                    continue
    for key in keys:
        if os.getenv(key, "").strip():
            return _configured_value(_SPECS_BY_KEY[key])
    return list(_SPECS_BY_KEY["COUNCIL_MODELS"]["default"]), "code_default"


def list_model_routes() -> Dict[str, Any]:
    store = _load_portfolio_store()
    overrides = store["overrides"]
    routes: List[Dict[str, Any]] = []
    for spec in MODEL_ROUTE_SPECS:
        if spec["kind"] == "role":
            routes.append(_portfolio_role_route(spec, store))
            continue
        configured, source = _configured_value(spec, store)
        override = overrides.get(spec["key"])
        if override is not None:
            try:
                effective = _normalise_value(spec, override)
                source = "runtime_override"
            except ValueError:
                effective = configured
        else:
            effective = configured
        if spec["key"] in _SHARED_COUNCIL_KEYS:
            configured, _ = _shared_council_value(store, configured_only=True)
            effective, source = _shared_council_value(store)
        models = effective if isinstance(effective, list) else [effective]
        routes.append(
            {
                "id": spec["id"],
                "app": spec["app"],
                "layer": spec["layer"],
                "provider": spec["provider"],
                "key": spec["key"],
                "kind": spec["kind"],
                "description": spec["description"],
                "configured_value": configured,
                "effective_value": effective,
                "model_freshness": {
                    str(model): _model_freshness(str(model)) for model in models
                },
                "source": source,
                "editable": True,
            }
        )
    errors = []
    try:
        get_portfolio_allocator_assignments(store)
    except ValueError as exc:
        errors.append({"app": "Portfolio Analysis", "detail": str(exc)})
    return {"routes": routes, "route_groups": _portfolio_route_groups(routes),
            "audit": list(reversed(store["audit"][-30:])), "configuration_errors": errors}


def _portfolio_route_groups(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {route["id"]: route for route in routes}
    groups = []
    for spec in PORTFOLIO_ROUTE_GROUPS:
        members = [by_id[identifier] for identifier in spec["members"]]
        def model(value):
            return value.get("model", "") if isinstance(value, dict) else value
        models = list(dict.fromkeys(model(member["effective_value"]) for member in members))
        sources = {member["source"] for member in members}
        groups.append({"id": spec["id"], "app": "Portfolio Analysis", "kind": "group",
            "layer": spec["layer"], "description": spec["description"], "provider": spec["provider"],
            "effective_value": {"model": models[0] if len(models) == 1 else ""},
            "mixed": len(models) > 1, "editable": True,
            "source": next(iter(sources)) if len(sources) == 1 else "mixed",
            "has_override": any(member["source"] == "runtime_override" for member in members),
            "members": [{"id": member["id"], "layer": member["layer"],
                "model": model(member["effective_value"]), "source": member["source"]} for member in members],
            "validation_error": "; ".join(member["validation_error"] for member in members if member.get("validation_error")),
            "model_freshness": {name: _model_freshness(name) for name in models if name}})
    return groups


def _change_route_group(group: Dict[str, Any], value: Any, *, reset: bool, actor: str) -> Dict[str, Any]:
    specs = [_SPECS_BY_ID[identifier] for identifier in group["members"]]
    updates = {}
    if not reset:
        model = value.get("model") if isinstance(value, dict) else value
        if not isinstance(model, str):
            raise ValueError("Provide one model for this group")
        # Validate every member before changing anything; one write applies the whole group.
        updates = {spec["key"]: _normalise_value(spec, {"model": model} if spec["kind"] == "role" else model) for spec in specs}
    store = _load_portfolio_store()
    changes = []
    for spec in specs:
        previous = store["overrides"].get(spec["key"])
        if reset:
            store["overrides"].pop(spec["key"], None)
            effective = _normalise_value(spec, _configured_value(spec, store)[0])
        else:
            effective = updates[spec["key"]]
            store["overrides"][spec["key"]] = effective
        changes.append({"route_id": spec["id"], "key": spec["key"],
            "previous_override": previous, "effective_value": effective})
    if reset and any(spec["kind"] == "role" for spec in specs):
        get_portfolio_allocator_assignments(store)
    if not reset or any(row["previous_override"] is not None for row in changes):
        values = list(dict.fromkeys(row["effective_value"].get("model") if isinstance(row["effective_value"], dict)
                                   else row["effective_value"] for row in changes))
        store["audit"].append({"at": _utc_now(), "actor": actor, "route_id": group["id"],
            "label": group["layer"], "action": "clear_override" if reset else "set_override",
            "effective_value": values[0] if len(values) == 1 else values, "member_changes": changes})
        store["audit"] = store["audit"][-_MAX_AUDIT_ROWS:]
        _save_store(store)
    return list_model_routes()


def _portfolio_role_route(spec: Dict[str, Any], store: Dict[str, Any]) -> Dict[str, Any]:
    configured = None
    effective = {"model": ""}
    source = "environment" if spec["key"] in os.environ else "migrated"
    error = ""
    try:
        try:
            configured, source = _configured_value(spec, store)
        except ValueError:
            if spec["key"] not in store["overrides"]:
                raise
        effective = store["overrides"].get(spec["key"], configured)
        if spec["key"] in store["overrides"]:
            source = "runtime_override"
        effective = _normalise_value(spec, effective)
    except ValueError as exc:
        error = str(exc)
    model = effective.get("model", "") if isinstance(effective, dict) else ""
    model = model if isinstance(model, str) else ""
    return {
        **{key: spec[key] for key in ("id", "app", "layer", "key", "kind", "provider", "description", "role")},
        "configured_value": configured,
        "effective_value": {"model": model},
        "source": source, "editable": True, "validation_error": error,
        "model_freshness": {model: _model_freshness(model)} if model else {},
    }


def update_model_route(route_id: str, value: Any, *, actor: str = "authenticated_operator") -> Dict[str, Any]:
    with _STORE_LOCK:
        return _update_model_route(route_id, value, actor=actor)


def _update_model_route(route_id: str, value: Any, *, actor: str) -> Dict[str, Any]:
    if route_id in _GROUPS_BY_ID:
        return _change_route_group(_GROUPS_BY_ID[route_id], value, reset=False, actor=actor)
    if route_id == "portfolio.deep-allocator":
        raise ValueError("The positional allocator list is retired. Refresh Model Routing and edit the named allocator roles.")
    spec = _SPECS_BY_ID.get(str(route_id or ""))
    if spec is None:
        raise KeyError("Unknown model route")
    normalized = _normalise_value(spec, value)
    store = _load_portfolio_store()
    previous = store["overrides"].get(spec["key"])
    store["overrides"][spec["key"]] = normalized
    if spec["key"] in _SHARED_COUNCIL_KEYS:
        for key in _SHARED_COUNCIL_KEYS:
            store["overrides"][key] = normalized
    store["audit"].append(
        {
            "at": _utc_now(),
            "actor": actor,
            "route_id": spec["id"],
            "key": spec["key"],
            "previous_override": previous,
            "effective_value": normalized,
            "action": "set_override",
        }
    )
    store["audit"] = store["audit"][-_MAX_AUDIT_ROWS:]
    _save_store(store)
    return list_model_routes()


def clear_model_route_override(route_id: str, *, actor: str = "authenticated_operator") -> Dict[str, Any]:
    with _STORE_LOCK:
        return _clear_model_route_override(route_id, actor=actor)


def _clear_model_route_override(route_id: str, *, actor: str) -> Dict[str, Any]:
    if route_id in _GROUPS_BY_ID:
        return _change_route_group(_GROUPS_BY_ID[route_id], None, reset=True, actor=actor)
    if route_id == "portfolio.deep-allocator":
        raise ValueError("The positional allocator list is retired. Refresh Model Routing and edit the named allocator roles.")
    spec = _SPECS_BY_ID.get(str(route_id or ""))
    if spec is None:
        raise KeyError("Unknown model route")
    store = _load_portfolio_store()
    previous = store["overrides"].pop(spec["key"], None)
    if spec["kind"] == "role":
        get_portfolio_allocator_assignments(store)
    if spec["key"] in _SHARED_COUNCIL_KEYS:
        for key in _SHARED_COUNCIL_KEYS:
            linked_previous = store["overrides"].pop(key, None)
            if previous is None:
                previous = linked_previous
    if previous is not None:
        store["audit"].append(
            {
                "at": _utc_now(),
                "actor": actor,
                "route_id": spec["id"],
                "key": spec["key"],
                "previous_override": previous,
                "effective_value": _configured_value(spec, store)[0],
                "action": "clear_override",
            }
        )
        store["audit"] = store["audit"][-_MAX_AUDIT_ROWS:]
        _save_store(store)
    return list_model_routes()
