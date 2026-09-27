import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.scenario_router.artifact_replay import _coerce_facts
from backend.scenario_router.display_contract import build_router_display_contract
from backend.scenario_router.model_thesis_judge import ModelAnnouncementThesisJudge
from backend.scenario_router.models import AnnouncementFacts, BaselineRunPacket


VERDICT = {
    "one_sentence_summary": "The company received committed funding.",
    "document_type": "financing_update",
    "trajectory_verdict": {
        "state": "risk_reduced", "direction": "positive", "materiality": "medium",
        "confidence": 0.9, "reason": "The funding was received.",
    },
}


def interpret(query, **kwargs):
    return asyncio.run(ModelAnnouncementThesisJudge(
        model="test/model", query_fn=query, **kwargs,
    ).interpret(
        AnnouncementFacts(event_id="event", ticker="ASX:TST"),
        BaselineRunPacket(run_id="run", ticker="ASX:TST"),
    ))


@pytest.mark.parametrize("initial,expected", [(1800, 6000), (6000, 12000)])
def test_truncated_response_retries_original_request_with_more_output_room(initial, expected):
    calls = []

    async def query(_model, messages, _timeout, tokens, _effort):
        calls.append((messages, tokens))
        return {
            "content": json.dumps(VERDICT),
            "finish_reason": "length" if len(calls) == 1 else "stop",
            "usage": {"completion_tokens": tokens if len(calls) == 1 else 3200},
        }

    result = interpret(query, max_output_tokens=initial)
    assert [tokens for _, tokens in calls] == [initial, expected]
    assert calls[0][0] == calls[1][0]
    assert result.model_judgement["status"] == "valid"
    assert [a["finish_reason"] for a in result.model_judgement["response_attempts"]] == ["length", "stop"]


def test_repeated_truncation_is_not_reported_as_low_confidence_or_scored():
    async def query(*_args):
        return {"content": json.dumps(VERDICT), "finish_reason": "length"}

    result = interpret(query)
    assert result.model_judgement["status"] == "invalid"
    assert result.model_judgement["reason"] == "output_truncated"
    assert "cut off" in result.filing_summary
    assert len(result.model_judgement["response_attempts"]) == 2
    assert result.classification_confidence == 0


@pytest.mark.parametrize("retryable,expected_calls", [(False, 1), (True, 2)])
def test_provider_errors_keep_their_actual_cause(retryable, expected_calls):
    query = AsyncMock(return_value={
        "error": "openrouter_http_429", "error_type": "http_error",
        "error_status": 429, "error_retryable": retryable,
    })
    result = interpret(query)
    assert query.await_count == expected_calls
    assert result.model_judgement["reason"] == "openrouter_http_429"
    assert result.model_judgement["response_attempts"][0]["error_status"] == 429


def test_real_query_requests_structured_failure_details():
    with patch("backend.scenario_router.model_thesis_judge.query_model", new_callable=AsyncMock) as query:
        query.return_value = {"content": json.dumps(VERDICT), "finish_reason": "stop"}
        result = asyncio.run(ModelAnnouncementThesisJudge(model="test/model").interpret(
            AnnouncementFacts(event_id="event", ticker="ASX:TST"),
            BaselineRunPacket(run_id="run", ticker="ASX:TST"),
        ))
    assert query.call_args.kwargs["include_error_details"] is True
    assert result.model_judgement["status"] == "valid"


def test_valid_assessment_with_zero_score_does_not_need_reclassification():
    report = {
        "trajectory_state": "risk_reduced", "impact_verdict": "positive",
        "thesis_relationship": "direct_match", "relationship_strength": "partial",
        "trajectory_score": {"event_delta": 0, "validation_type": "none", "mapped_condition": False},
    }
    display = build_router_display_contract(report, {"action": "annotate_run"}, model_judgement={"status": "valid"})
    assert display["queue_bucket"] == "positive_movement"
    assert display["assessment_status"] == "valid"
    assert not display["is_user_action_required"]
    assert report["trajectory_score"]["event_delta"] == 0


def test_failure_display_does_not_claim_the_model_was_uncertain():
    display = build_router_display_contract(
        {"trajectory_state": "needs_classification", "impact_verdict": "uncertain"},
        {"action": "annotate_run"},
        model_judgement={"status": "invalid", "reason": "output_truncated"},
    )
    assert display["trajectory_label"] == "AI assessment failed"
    assert "cut off" in display["primary_reason"]
    assert display["is_user_action_required"]


def test_replay_preserves_filing_date_for_previous_evidence_context():
    facts = _coerce_facts({"event_id": "event", "ticker": "ASX:TST", "published_at_utc": "2026-09-09T01:00:00Z"})
    assert facts.published_at_utc == "2026-09-09T01:00:00Z"


def test_failed_ai_reassessment_does_not_overwrite_stored_event(tmp_path):
    from fastapi import HTTPException
    from backend.routers import scenario_router_routes as routes

    path = tmp_path / "event.json"
    original = json.dumps({"event": {"event_id": "event"}, "original": True})
    path.write_text(original)
    failed = {"announcement_facts": {"model_judgement": {"status": "invalid", "reason": "output_truncated"}}}
    with (
        patch.object(routes, "OPENROUTER_API_KEY", "test-key"),
        patch.object(routes, "_scenario_router_artifact_paths_for_event", return_value=[path]),
        patch.object(routes, "_choose_primary_scenario_router_artifact", return_value=path),
        patch("backend.scenario_router.rejudge_artifacts.rejudge_payload", new_callable=AsyncMock, return_value=failed),
    ):
        with pytest.raises(HTTPException) as error:
            asyncio.run(routes.post_scenario_router_reassess("event"))
    assert error.value.status_code == 502
    assert path.read_text() == original
