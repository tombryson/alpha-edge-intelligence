from copy import deepcopy
from datetime import datetime, timezone
from itertools import permutations

import pytest

from backend.scenario_router.trajectory_scoring import apply_cumulative_scores

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)


def filing(catalyst, value, **changes):
    row = {
        "ticker": "ASX:TEST", "run_id": "run-1", "event_id": catalyst,
        "published_at_utc": "2026-09-01T00:00:00Z",
        "saved_at_utc": "2026-09-08T00:00:00Z",
        "evidence_update": {"catalyst_id": catalyst, "change": "new"},
        "trajectory_score": {"event_delta": value, "baseline_score": 0, "validation_type": "mapped_condition"},
    }
    row.update(changes)
    return row


def evaluate(rows):
    apply_cumulative_scores(rows, as_of=NOW)
    return max(rows, key=lambda row: (row["published_at_utc"], row["event_id"]))["trajectory_score"]


def test_independent_catalysts_are_order_independent_and_repeat_cannot_refill_cap():
    for order in permutations([("A", 3), ("B", 3), ("C", -3)]):
        rows = [filing(key, value, published_at_utc=f"2026-09-0{i + 1}T00:00:00Z") for i, (key, value) in enumerate(order)]
        assert evaluate(rows)["cumulative_delta"] == 2.89
        rows.append(filing("B", 3, event_id="repeat", published_at_utc="2026-09-07T00:00:00Z"))
        score = evaluate(rows)
        assert score["cumulative_delta"] == 2.89
        assert score["event_delta"] == 0


def test_publication_date_controls_expiry_and_durable_facts_survive():
    old = filing("permit", 3, published_at_utc="2025-01-01T00:00:00Z")
    assert evaluate([old])["contribution_status"] == "expired"
    old["evidence_update"]["durable"] = True
    assert evaluate([old])["cumulative_delta"] == 2.89


def test_progression_replaces_state_and_baseline_inclusion_has_no_increment():
    rows = [filing("permit", 3)]
    rows.append(filing("permit", 1, event_id="update", published_at_utc="2026-09-02T00:00:00Z", evidence_update={"catalyst_id": "permit", "change": "progression"}))
    assert evaluate(rows)["cumulative_delta"] == .96
    included = filing("permit", 3, run_id="run-2", evidence_update={"catalyst_id": "permit", "change": "baseline_included"})
    assert evaluate([included])["event_delta"] == 0


def test_fixed_weights_and_repeated_projection_are_stable():
    rows = [filing("primary", 4), filing("secondary", 1.5)]
    rows[1]["trajectory_score"]["validation_type"] = "related_unmapped"
    score = evaluate(rows)
    assert score["cumulative_primary_delta"] / score["cumulative_delta"] == pytest.approx(.7)
    assert score["cumulative_secondary_delta"] / score["cumulative_delta"] == pytest.approx(.3)
    before = deepcopy(rows)
    evaluate(rows)
    assert rows == before


def test_cross_run_repeat_carries_once_without_refreshing_original_date():
    update = {"catalyst_id": "permit", "change": "repeat", "prior_run_id": "run-0", "effective_at_utc": "2026-08-01T00:00:00Z"}
    row = filing("permit", 3, evidence_update=update)
    assert evaluate([row])["cumulative_delta"] == 2.89
    update["effective_at_utc"] = "2025-01-01T00:00:00Z"
    assert evaluate([row])["contribution_status"] == "expired"


def test_expiring_reversal_does_not_resurrect_old_durable_fact():
    rows = [filing("permit", 3, published_at_utc="2025-01-01T00:00:00Z", evidence_update={"catalyst_id": "permit", "change": "new", "durable": True}),
            filing("permit", -3, event_id="revoked", published_at_utc="2025-02-01T00:00:00Z", evidence_update={"catalyst_id": "permit", "change": "reversal"})]
    assert evaluate(rows)["cumulative_delta"] == 0


def test_model_id_migrates_existing_condition_without_double_counting():
    original = filing("permit", 3, evidence_update={}, matched_conditions=[{"condition_id": "permit"}])
    updated = filing("permit", 4, event_id="update", published_at_utc="2026-09-02T00:00:00Z", evidence_update={"catalyst_id": "validated:condition:permit", "change": "progression"})
    assert evaluate([original, updated])["cumulative_delta"] == 3.85


def test_neutral_repeat_displays_already_reflected_and_can_carry_prior_run_state():
    update = {"catalyst_id": "permit", "change": "repeat", "prior_run_id": "old-run", "prior_validation_type": "mapped_condition", "prior_assessment": 3}
    row = filing("permit", 0, evidence_update=update)
    row["trajectory_score"]["validation_type"] = "none"
    assert evaluate([row])["cumulative_delta"] == 2.89
    update["prior_run_id"] = "run-1"
    assert evaluate([row])["contribution_status"] == "repeat_suppressed"
