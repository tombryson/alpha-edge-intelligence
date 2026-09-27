import asyncio
import json

from backend.scenario_router.model_thesis_judge import ModelAnnouncementThesisJudge, normalize_model_thesis_payload
from backend.scenario_router.models import AnnouncementFacts, BaselineRunPacket


def test_judge_receives_prior_context_and_repeat_provenance_survives_replay():
    prior = [{"catalyst_id": "mine-permit", "run_id": "old-run", "published_at_utc": "2026-01-01T00:00:00Z", "durable": True}]
    async def query(_model, messages, *_args):
        request = json.loads(messages[1]["content"].split("INPUT_JSON:\n")[1])
        assert request["previous_catalyst_evidence"] == prior
        return {"content": json.dumps({
            "one_sentence_summary": "Permit was already issued.",
            "evidence_update": {"catalyst_id": "mine-permit", "change": "repeat", "durable": False, "reason": "Same permit", "evidence_quote": "Permit was already issued."},
            "trajectory_verdict": {"state": "thesis_strengthened", "direction": "positive", "materiality": "medium"},
        })}
    judge = ModelAnnouncementThesisJudge(model="test", query_fn=query, evidence_loader=lambda *_: prior)
    result = asyncio.run(judge.interpret(AnnouncementFacts(event_id="event", ticker="ASX:TST"), BaselineRunPacket(run_id="new-run", ticker="ASX:TST")))
    update = result.model_judgement["evidence_update"]
    assert update["prior_run_id"] == "old-run"
    assert update["effective_at_utc"] == "2026-01-01T00:00:00Z"
    assert update["durable"] is True
    replay, error = normalize_model_thesis_payload(result.model_judgement)
    assert not error
    assert replay["evidence_update"] == update


def test_unknown_repeat_id_cannot_suppress_a_new_filing():
    async def query(*_args):
        return {"content": json.dumps({"one_sentence_summary": "A new permit", "evidence_update": {"catalyst_id": "invented", "change": "repeat", "reason": "Duplicate", "evidence_quote": "A new permit"}})}
    judge = ModelAnnouncementThesisJudge(model="test", query_fn=query)
    result = asyncio.run(judge.interpret(AnnouncementFacts(event_id="event", ticker="ASX:TST"), BaselineRunPacket(run_id="run", ticker="ASX:TST")))
    assert "evidence_update" not in result.model_judgement
