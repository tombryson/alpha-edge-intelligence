from copy import deepcopy
import json

import pytest

from backend.portfolio_evidence import FACT_CHECK_SCHEMA, fact_fingerprint, normalize_facts, review_fields
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, digest, load_checkpoint
from scripts import portfolio_positioning_memo as memo


@pytest.mark.asyncio
async def test_checked_observation_reuses_across_batches_and_models_but_not_changed_source(tmp_path, monkeypatch):
    source = {"id": "s", "url": "https://example.test/gdp", "excerpt": "GDP growth 3.1 percent", "published_at": "2026-09-15"}
    packet = {"as_of": "2026-09-22", "sources": [source]}
    fact = {"id": "a", "kind": "observed_macro", "metric": "GDP growth", "value": 3.1, "unit": "percent",
        "currency": "not_applicable", "benchmark": "GDP", "observed_at": "2026-09-15", "published_at": "2026-09-15",
        "source_ids": ["s"], "source_excerpt": source["excerpt"]}
    brief = {"facts": normalize_facts([fact], packet), "source_packet": packet, "evidence_status": "complete"}
    calls, prompts = [], []
    async def query(model, messages, **kwargs):
        prompt = json.loads(messages[0]["content"])
        prompts.append(prompt)
        assert "user_query" not in prompt
        rows = prompt["evidence"]["facts"]
        calls.append([row["id"] for row in rows])
        return {"stage_status": "complete", "content": json.dumps({"fact_checks": [{"fact_id": row["id"],
            "checks": {field: "unresolved" for field in review_fields(row)}, "reason": "Source lacks some metadata"} for row in rows]})}
    monkeypatch.setattr(memo, "_query_stage", query)
    monkeypatch.setattr(memo, "_summary_model_for_mode", lambda mode: "same-model")
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    async def check(raw):
        return await memo._run_evidence_reconciliation(query="portfolio", mode="deep", evidence_briefs=[deepcopy(raw)],
            asset_class_vocabulary=[], review_fact_ids={row["id"] for row in raw["facts"]})
    try:
        first = await check(brief)
        assert calls == [["a"]]
        assert runtime.partial["observation_checks"]
        assert load_checkpoint(runtime.checkpoint)["partial_artifact"]["observation_checks"]
        # A source-support verdict is bound to its observation, not a batch number or ID alias.
        renamed = deepcopy(brief)
        renamed["facts"][0]["id"] = "alias"
        await check(renamed)
        assert calls == [["a"]]
        from unittest.mock import AsyncMock
        ready = AsyncMock()
        await memo._run_evidence_reconciliation(query="portfolio", mode="deep", evidence_briefs=[deepcopy(renamed)],
            asset_class_vocabulary=[], review_fact_ids={"alias"}, on_observations=ready)
        ready.assert_awaited_once()
        ready_evidence, ready_ids = ready.call_args.args
        assert ready_ids == {"alias"}
        assert ready_evidence["facts"][0]["claim_review"]["check_model"] == "same-model"
        assert ready_evidence["facts"][0]["claim_review"]["checks"]
        changed = deepcopy(renamed)
        changed["source_packet"]["sources"][0]["excerpt"] += " Revised publication."
        await check(changed)
        assert len(calls) == 2
        monkeypatch.setattr(memo, "_summary_model_for_mode", lambda mode: "other-model")
        reused = await check(brief)
        assert len(calls) == 2
        assert reused["facts"][0]["claim_review"]["check_model"] == "same-model"
        # Embedded checks also survive a model change without the separate cache.
        runtime.partial["observation_checks"] = {}
        reused = await check(first)
        assert len(calls) == 2
        assert reused["facts"][0]["claim_review"]["check_model"] == "same-model"

        # Migrate both old embedded and old per-observation contracts. The exact
        # same rules/schema are required; a different rule contract must rerun.
        spec = {"rules": prompts[0]["rules"], "schema": FACT_CHECK_SCHEMA, "contract": "source-support-v2"}
        legacy = digest({**spec, "model": "same-model"})
        embedded = deepcopy(first)
        embedded["facts"][0]["claim_review"]["check_contract"] = legacy
        assert (await check(embedded))["facts"][0]["claim_review"]["check_model"] == "same-model"
        assert len(calls) == 2
        old_key = digest({"observation": fact_fingerprint(brief["facts"][0]), "contract": legacy})
        runtime.partial["observation_checks"] = {old_key: {
            "fact_id": "a", "checks": first["facts"][0]["claim_review"]["checks"],
            "reason": "Source lacks some metadata", "check_contract": legacy, "check_model": "same-model"}}
        assert (await check(brief))["facts"][0]["claim_review"]["check_model"] == "same-model"
        assert len(calls) == 2
        runtime.partial["observation_checks"] = {}
        embedded["facts"][0]["claim_review"]["check_contract"] = digest({**spec, "model": "same-model", "rules": ["Different rules"]})
        await check(embedded)
        assert len(calls) == 3
        changed = deepcopy(brief)
        changed["facts"][0]["value"] = 5.1
        await check(changed)
        assert len(calls) == 4
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("source_ids", [["s"], None, []])
async def test_absent_source_stays_unresolved_without_model_call_and_reopens_when_added(tmp_path, monkeypatch, source_ids):
    from unittest.mock import AsyncMock
    query = AsyncMock(return_value={"stage_status": "complete", "content": '{"fact_checks": []}'})
    monkeypatch.setattr(memo, "_query_stage", query)
    runtime = PortfolioRuntime(tmp_path / "missing.checkpoint.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    brief = {"evidence_status": "complete", "source_packet": {"sources": []},
        "facts": [{"id": "a", "metric": "GDP", "value": 3.1, "source_ids": source_ids, "source_excerpt": "GDP 3.1"}]}
    async def check(raw):
        return await memo._run_evidence_reconciliation(query="portfolio", mode="deep", evidence_briefs=[raw],
            asset_class_vocabulary=[], review_fact_ids={"a"})
    try:
        result = await check(brief)
        query.assert_not_awaited()
        assert result["facts"][0]["claim_status"] == "unresolved"
        assert result["facts"][0]["claim_review"]["check_model"] is None
        assert set(result["facts"][0]["claim_review"]["checks"].values()) == {"unresolved"}
        result["facts"][0]["source_ids"] = ["s"]
        result["source_packet"]["sources"] = [{"id": "s", "excerpt": "GDP 3.1"}]
        await check(result)
        query.assert_awaited_once()
    finally:
        CURRENT_RUNTIME.reset(token)
