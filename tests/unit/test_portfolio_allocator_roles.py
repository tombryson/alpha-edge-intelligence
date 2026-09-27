import argparse
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from backend import model_routing
from backend.jobs import executor
from backend.portfolio_roles import (
    ALLOCATOR_ROLES,
    ALLOCATOR_JUDGE_KEY,
    LEGACY_ALLOCATOR_KEY,
    allocator_assignments_from_environment,
    legacy_allocator_assignments,
    normalize_allocator_assignment,
)
from backend.routers import analysis_jobs, model_routing as routing_api
import portfolio_positioning_memo as memo


LEGACY_MODELS = ["openai/gpt-5.5", "google/gemini-3.8-flash", "x-ai/grok-4.6"]


@pytest.fixture(autouse=True)
def routing_store(tmp_path, monkeypatch):
    monkeypatch.setattr(memo, "query_model", AsyncMock(side_effect=AssertionError("Live model calls are forbidden in unit tests")))
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    for role in ALLOCATOR_ROLES:
        monkeypatch.delenv(role["key"], raising=False)
    monkeypatch.delenv(ALLOCATOR_JUDGE_KEY, raising=False)
    monkeypatch.setenv(LEGACY_ALLOCATOR_KEY, ",".join(LEGACY_MODELS))


def install_runtime(monkeypatch):
    for key, value in model_routing.runtime_model_environment().items():
        monkeypatch.setenv(key, value)


def corrupt_role(index=3):
    store = model_routing._load_portfolio_store()
    store["overrides"][ALLOCATOR_ROLES[index]["key"]] = {"model": ""}
    model_routing._save_store(store)


def test_migration_preserves_live_assignments_and_assigns_every_role(monkeypatch):
    model_routing._save_store({
        "version": 1, "overrides": {LEGACY_ALLOCATOR_KEY: LEGACY_MODELS}, "audit": [],
    })
    monkeypatch.setenv(LEGACY_ALLOCATOR_KEY, "wrong/default")
    result = model_routing.list_model_routes()
    rows = [row for row in result["routes"] if row["kind"] == "role"]
    assert len(rows) == 4
    assert [row["effective_value"]["model"] for row in rows] == LEGACY_MODELS + [LEGACY_MODELS[0]]
    assert all(set(row["effective_value"]) == {"model"} for row in rows)
    assert not result["configuration_errors"]
    assert not any(row["id"] == "portfolio.deep-allocator" for row in result["routes"])
    assert len(result["audit"]) == 4
    assert model_routing._load_store()["version"] == 3
    assert model_routing.list_model_routes() == result


def test_portfolio_labels_do_not_imply_multiple_modes():
    routes = [row for row in model_routing.list_model_routes()["routes"] if row["app"] == "Portfolio Analysis"]
    labels = {row["id"]: row["layer"] for row in routes}
    assert labels["portfolio.deep-summary"] == "Evidence summary"
    assert labels["portfolio.deep-chairman"] == "Allocator judge"
    assert labels["portfolio.deep-commentary"] == "Commentary"
    assert labels["portfolio.synthesis"] == "Final allocation synthesis"
    assert all("deep mode" not in f"{row['layer']} {row['description']}".lower() for row in routes)
    assert all("deep" not in row["layer"].lower() for row in routes)


def test_edit_and_reset_never_shift_another_role(monkeypatch):
    original = model_routing.get_portfolio_allocator_assignments()
    model_routing.update_model_route(ALLOCATOR_ROLES[0]["id"], {"model": "provider/replacement"})
    model_routing.update_model_route(ALLOCATOR_ROLES[3]["id"], {"model": LEGACY_MODELS[1]})
    updated = model_routing.get_portfolio_allocator_assignments()
    assert updated[1:3] == original[1:3]
    assert updated[3]["model"] == updated[1]["model"]
    assert updated[0]["model"] == "provider/replacement"
    monkeypatch.setenv(LEGACY_ALLOCATOR_KEY, "changed/legacy,changed/order")
    model_routing.clear_model_route_override(ALLOCATOR_ROLES[0]["id"])
    assert model_routing.get_portfolio_allocator_assignments()[:3] == original[:3]
    model_routing.clear_model_route_override(ALLOCATOR_ROLES[3]["id"])
    assert model_routing.get_portfolio_allocator_assignments() == original


@pytest.mark.parametrize("value", [
    {"model": ""}, {"model": "bad model"}, {},
    {"enabled": False, "model": "provider/model"},
    {"enabled": True, "model": "provider/model"},
    {"model": ["provider/model"]}, None,
])
def test_invalid_role_saves_are_rejected_without_changing_store(value):
    model_routing.list_model_routes()
    before = model_routing._load_store()
    with pytest.raises(ValueError):
        model_routing.update_model_route(ALLOCATOR_ROLES[3]["id"], value)
    assert model_routing._load_store() == before


@pytest.mark.parametrize("index", range(4))
def test_every_role_requires_a_model(index):
    corrupt_role(index)
    with pytest.raises(ValueError, match="a model is required"):
        model_routing.get_portfolio_allocator_assignments()


def test_optional_role_preview_migrates_to_required_models_without_losing_edits():
    defaults = {
        role["key"]: {"enabled": index < 3, "model": LEGACY_MODELS[index] if index < 3 else ""}
        for index, role in enumerate(ALLOCATOR_ROLES)
    }
    model_routing._save_store({
        "version": 2, "portfolio_allocator_defaults": defaults, "audit": [],
        "overrides": {
            ALLOCATOR_JUDGE_KEY: "provider/judge",
            ALLOCATOR_ROLES[0]["key"]: {"enabled": False, "model": "provider/edited"},
            ALLOCATOR_ROLES[3]["key"]: {"enabled": False, "model": ""},
        },
    })
    assignments = model_routing.get_portfolio_allocator_assignments()
    assert [row["model"] for row in assignments] == ["provider/edited", *LEGACY_MODELS[1:], "provider/judge"]
    assert all("enabled" not in row for row in assignments)
    model_routing.update_model_route("portfolio.deep-chairman", "provider/new-judge")
    assert model_routing.get_portfolio_allocator_assignments() == assignments
    model_routing.clear_model_route_override(ALLOCATOR_ROLES[3]["id"])
    assert model_routing.get_portfolio_allocator_assignments()[3]["model"] == "provider/judge"


def test_initial_missing_role_uses_effective_judge_model():
    model_routing._save_store({"version": 1, "overrides": {ALLOCATOR_JUDGE_KEY: "provider/judge"}, "audit": []})
    assert model_routing.get_portfolio_allocator_assignments()[3]["model"] == "provider/judge"


def test_invalid_saved_role_is_visible_and_does_not_block_company_jobs():
    corrupt_role()
    result = model_routing.list_model_routes()
    row = next(row for row in result["routes"] if row["id"] == ALLOCATOR_ROLES[3]["id"])
    assert "a model is required" in row["validation_error"]
    assert "Defensive-regime reviewer" in result["configuration_errors"][0]["detail"]
    assert "COUNCIL_MODELS" in executor._build_analysis_job_env("company_analysis")
    with pytest.raises(ValueError, match="Defensive-regime reviewer"):
        executor._build_analysis_job_env(" Portfolio_Positioning ")
    model_routing.update_model_route(ALLOCATOR_ROLES[3]["id"], {"model": "provider/repaired"})
    assert not model_routing.list_model_routes()["configuration_errors"]


def test_named_environment_must_be_complete(monkeypatch):
    monkeypatch.setenv(ALLOCATOR_ROLES[0]["key"], '{"model":"named/model"}')
    with pytest.raises(ValueError, match="Portfolio-aware allocator"):
        model_routing.get_portfolio_allocator_assignments()
    with pytest.raises(ValueError, match="Portfolio-aware allocator"):
        allocator_assignments_from_environment()
    assert model_routing.list_model_routes()["configuration_errors"]


def test_explicit_named_environment_precedes_migration_and_override_precedes_environment(monkeypatch):
    model_routing.list_model_routes()
    values = legacy_allocator_assignments("named/model")
    for key, value in values.items():
        monkeypatch.setenv(key, json.dumps(value))
    assert model_routing.get_portfolio_allocator_assignments()[0]["model"] == "named/model"
    model_routing.update_model_route(ALLOCATOR_ROLES[0]["id"], {"model": "operator/model"})
    assert model_routing.get_portfolio_allocator_assignments()[0]["model"] == "operator/model"
    model_routing.clear_model_route_override(ALLOCATOR_ROLES[0]["id"])
    assert model_routing.get_portfolio_allocator_assignments()[0]["model"] == "named/model"


def test_legacy_deduplication_and_excess_models_are_explicit():
    values = legacy_allocator_assignments("provider/a, provider/a, provider/b")
    assert values[ALLOCATOR_ROLES[1]["key"]]["model"] == "provider/b"
    assert values[ALLOCATOR_ROLES[2]["key"]]["model"] == LEGACY_MODELS[0]
    with pytest.raises(ValueError, match="More than four"):
        legacy_allocator_assignments([f"provider/{index}" for index in range(5)])
    assert normalize_allocator_assignment({"model": "provider/model:free"}, "Test")["model"] == "provider/model:free"


@pytest.mark.asyncio
async def test_role_api_round_trip_and_retired_pool_errors():
    app = FastAPI()
    app.include_router(routing_api.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        path = f"/api/model-routing/{ALLOCATOR_ROLES[3]['id']}"
        response = await client.put(path, json={"value": {"model": ""}})
        assert response.status_code == 422
        assert "a model is required" in response.json()["detail"]
        response = await client.put(path, json={"value": {"model": "provider/model:free"}})
        assert response.status_code == 200
        assert model_routing.get_portfolio_allocator_assignments()[3]["model"] == "provider/model:free"
        response = await client.put(path, json={"value": {"enabled": False, "model": "provider/model:free"}})
        assert response.status_code == 422
        assert "every allocator role runs" in response.json()["detail"]
        assert (await client.delete(path)).status_code == 200
        for method in ("put", "delete"):
            response = await client.request(method, "/api/model-routing/portfolio.deep-allocator", json={"value": ["provider/model"]})
            assert response.status_code == 422
            assert "retired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_job_submission_rejects_bad_roles_before_creating_files(monkeypatch):
    corrupt_role()
    monkeypatch.setattr(analysis_jobs, "_ensure_system_enabled", lambda: None)
    monkeypatch.setattr(analysis_jobs, "_ensure_analysis_job_dirs", lambda: pytest.fail("Created job files before validation"))
    app = FastAPI()
    app.include_router(analysis_jobs.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analysis-jobs", json={
            "job_type": "portfolio_positioning", "portfolio_context": {"portfolio": {"cash_pct": 100}},
        })
    assert response.status_code == 422
    assert "Defensive-regime reviewer" in response.json()["detail"]


@pytest.mark.asyncio
async def test_executor_rechecks_before_supplementary_calls_or_spawn(monkeypatch, tmp_path):
    corrupt_role()
    fields = AsyncMock(return_value={})
    prepare = AsyncMock()
    spawn = AsyncMock()
    monkeypatch.setattr(executor, "_set_job_fields", fields)
    monkeypatch.setattr(executor, "_prepare_generated_supplementary_for_job", prepare)
    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", spawn)
    await executor._run_analysis_job(job_id="test", command=["unused"], output_path=tmp_path / "unused.json", request_payload={"job_type": "portfolio_positioning"})
    prepare.assert_not_awaited()
    spawn.assert_not_awaited()
    assert fields.call_args.kwargs["status"] == "failed"
    assert "Defensive-regime reviewer" in fields.call_args.kwargs["error"]


@pytest.mark.asyncio
async def test_dispatch_always_runs_all_four_roles_even_when_models_repeat(monkeypatch):
    model_routing.update_model_route(ALLOCATOR_ROLES[0]["id"], {"model": "provider/replacement"})
    model_routing.update_model_route(ALLOCATOR_ROLES[3]["id"], {"model": LEGACY_MODELS[1]})
    install_runtime(monkeypatch)
    chairman = AsyncMock(side_effect=[
        {"asset_class_targets": [{"asset_class": "cash"}]},
        {"asset_class_targets": [{"asset_class": "cash"}], "lane_strategy": "wrong"},
        RuntimeError("provider unavailable"),
        {"asset_class_targets": [{"asset_class": "gold"}]},
    ])
    judge = AsyncMock(return_value={"judged": True})
    monkeypatch.setattr(memo, "_run_chairman", chairman)
    monkeypatch.setattr(memo, "_run_allocator_judge", judge)
    from backend.portfolio_runtime import PortfolioRuntime, CURRENT_RUNTIME, CURRENT_LANE, PortfolioDependencyError
    runtime = PortfolioRuntime()
    token = CURRENT_RUNTIME.set(runtime)
    try:
        with pytest.raises(PortfolioDependencyError, match="required allocator"):
            await memo._run_allocator_council(query="test", mode="deep", evidence_brief={}, asset_class_vocabulary=[])
        outputs = runtime.partial["retained_allocations"][CURRENT_LANE.get()]
    finally:
        CURRENT_RUNTIME.reset(token)
    expected_roles = [role["role"] for role in ALLOCATOR_ROLES]
    assert [call.kwargs["lane_strategy"] for call in chairman.call_args_list] == expected_roles
    assert [call.kwargs["model_override"] for call in chairman.call_args_list] == ["provider/replacement", LEGACY_MODELS[1], LEGACY_MODELS[2], LEGACY_MODELS[1]]
    assert [row["lane_strategy"] for row in outputs] == expected_roles
    assert [row["council_lane"] for row in outputs] == expected_roles
    assert outputs[2]["error"] == "provider unavailable"
    judge.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_validates_before_research(monkeypatch):
    monkeypatch.setenv(ALLOCATOR_ROLES[0]["key"], '{"model":""}')
    monkeypatch.setattr(memo, "_read_context", lambda _: {})
    evidence = AsyncMock()
    monkeypatch.setattr(memo, "_run_evidence_ensemble", evidence)
    with pytest.raises(ValueError):
        await memo._run_pipeline(argparse.Namespace(portfolio_context_file="unused", query="test", mode="deep"))
    evidence.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_records_all_four_required_roles(monkeypatch):
    install_runtime(monkeypatch)
    monkeypatch.setattr(memo, "_read_context", lambda _: {})
    monkeypatch.setattr(memo, "_ensemble_runs_for_mode", lambda _: 1)
    monkeypatch.setattr(memo, "_run_evidence_ensemble", AsyncMock(return_value=({"evidence_status": "complete", "facts": [{"id": "f1"}]}, [], [])))
    monkeypatch.setattr(memo, "_run_chairman", AsyncMock(return_value={"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}]}))
    monkeypatch.setattr(memo, "_run_single_portfolio_memo_lane", AsyncMock(return_value={
        "macro_positioning": {}, "structured_data": {}, "allocator_commentary": {},
        "markdown": "test memo", "allocator_council_runs": [],
    }))
    artifact = await memo._run_pipeline(argparse.Namespace(
        portfolio_context_file="unused", query="test", mode="deep", dump_json="test.json", run_label="test",
    ))
    assert artifact["allocator_role_assignments"] == allocator_assignments_from_environment()
    assert len(artifact["allocator_role_assignments"]) == 4
    assert artifact["allocator_role_assignments"][3]["model"] == LEGACY_MODELS[0]
    assert all("enabled" not in row for row in artifact["allocator_role_assignments"])
