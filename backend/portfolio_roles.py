"""Named portfolio allocator roles shared by routing and the memo runner."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Mapping


LEGACY_ALLOCATOR_KEY = "PORTFOLIO_POSITIONING_DEEP_ALLOCATOR_COUNCIL_MODELS"
ALLOCATOR_JUDGE_KEY = "PORTFOLIO_POSITIONING_DEEP_CHAIRMAN_MODEL"
DEFAULT_ALLOCATOR_JUDGE_MODEL = "openai/gpt-5.5"
DEFAULT_ALLOCATOR_MODELS = ("openai/gpt-5.5", "google/gemini-3.1-pro-preview", "x-ai/grok-4.3")
MODEL_ID_RE = re.compile(r"^~?[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?$")

ALLOCATOR_ROLES = (
    {
        "role": "blind_macro_prior",
        "id": "portfolio.allocator-macro-prior",
        "key": "PORTFOLIO_POSITIONING_ALLOCATOR_MACRO_PRIOR",
        "label": "Macro-first allocator",
        "description": "Builds and saves the independent ideal before seeing holdings or investment plays.",
    },
    {
        "role": "portfolio_aware_allocator",
        "id": "portfolio.allocator-portfolio-aware",
        "key": "PORTFOLIO_POSITIONING_ALLOCATOR_PORTFOLIO_AWARE",
        "label": "Portfolio-aware allocator",
        "description": "Assesses the current book without seeing the ideal's weights or submitted plays.",
    },
    {
        "role": "exposure_equivalence_reviewer",
        "id": "portfolio.allocator-exposure-equivalence",
        "key": "PORTFOLIO_POSITIONING_ALLOCATOR_EXPOSURE_EQUIVALENCE",
        "label": "Exposure-equivalence reviewer",
        "description": "Challenges both portfolio views and assesses investment plays and their economic expressions.",
    },
    {
        "role": "defensive_regime_reviewer",
        "id": "portfolio.allocator-defensive-review",
        "key": "PORTFOLIO_POSITIONING_ALLOCATOR_DEFENSIVE_REVIEW",
        "label": "Defensive-regime reviewer",
        "description": "Tests adverse regimes, then checks final financial claims and the treatment of reviewer corrections.",
    },
)


def legacy_allocator_assignments(value: Any, *, default_model: str = DEFAULT_ALLOCATOR_JUDGE_MODEL) -> Dict[str, Dict[str, Any]]:
    items = value if isinstance(value, list) else str(value or "").split(",")
    # The old runner de-duplicated its pool before assigning positional roles.
    models = list(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))
    if len(models) > len(ALLOCATOR_ROLES):
        raise ValueError("More than four legacy allocator models are configured. Review the legacy pool before migrating to named roles.")
    return {
        role["key"]: {"model": models[index] if index < len(models) else default_model}
        for index, role in enumerate(ALLOCATOR_ROLES)
    }


def normalize_allocator_assignment(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: provide a model assignment.")
    if "enabled" in value:
        raise ValueError(f"{label}: every allocator role runs. Refresh Model Routing and edit the model only.")
    if not isinstance(value.get("model", ""), str):
        raise ValueError(f"{label}: provide one valid model identifier.")
    model = value.get("model", "").strip()
    if not model:
        raise ValueError(f"{label}: a model is required.")
    if not MODEL_ID_RE.fullmatch(model):
        raise ValueError(f"{label}: invalid model identifier: {model}")
    return {"model": model}


def validate_allocator_assignments(values: Mapping[str, Any]) -> List[Dict[str, Any]]:
    assignments = []
    for role in ALLOCATOR_ROLES:
        value = normalize_allocator_assignment(values.get(role["key"]), role["label"])
        assignments.append({"role": role["role"], "label": role["label"], **value})
    return assignments


def allocator_assignments_from_environment(env: Mapping[str, str] | None = None) -> List[Dict[str, Any]]:
    environment = os.environ if env is None else env
    explicit = any(role["key"] in environment for role in ALLOCATOR_ROLES)
    if explicit:
        # Once named assignments are supplied, never fill a gap by list position.
        values = {}
        for role in ALLOCATOR_ROLES:
            try:
                values[role["key"]] = json.loads(environment[role["key"]])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{role['label']}: missing or invalid named role configuration.") from exc
    else:
        legacy = environment.get(LEGACY_ALLOCATOR_KEY, ",".join(DEFAULT_ALLOCATOR_MODELS))
        judge_model = environment.get(ALLOCATOR_JUDGE_KEY, "").strip() or DEFAULT_ALLOCATOR_JUDGE_MODEL
        values = legacy_allocator_assignments(legacy, default_model=judge_model)
    return validate_allocator_assignments(values)
