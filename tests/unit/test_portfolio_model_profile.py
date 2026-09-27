import json
from pathlib import Path

import pytest
from dotenv import dotenv_values

from backend import model_routing
from backend.jobs.executor import _build_analysis_job_env
from backend.portfolio_roles import ALLOCATOR_ROLES, allocator_assignments_from_environment
from backend.portfolio_retrieval import market_context_processor, source_processor
from scripts.configure_portfolio_models import PORTFOLIO_MODEL_PROFILE, RETRIEVAL_PROFILE, PRIMARY_MODEL, FINANCIAL_REVIEW_MODEL, REVIEW_MODEL, EVIDENCE_MODEL, configure


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    for role in ALLOCATOR_ROLES:
        monkeypatch.delenv(role["key"], raising=False)


def test_profile_preview_does_not_change_existing_assignments():
    model_routing.list_model_routes()
    before = model_routing._load_store()
    report = configure()
    assert report["changes"] and not report["applied"]
    assert model_routing._load_store() == before


def test_profile_changes_only_portfolio_routes_and_is_idempotent():
    model_routing.update_model_route("council.chairman", "provider/keep-chairman")
    model_routing.update_model_route("router.semantic-adjudicator", "provider/keep-router")
    before = model_routing.list_model_routes()
    report = configure(apply=True)
    after = model_routing.list_model_routes()
    assert report["applied"]
    assert [row for row in before["routes"] if row["app"] != "Portfolio Analysis"] == [
        row for row in after["routes"] if row["app"] != "Portfolio Analysis"]
    actual = {row["id"]: row["effective_value"] for row in after["routes"]}
    assert all(actual[key] == value for key, value in PORTFOLIO_MODEL_PROFILE.items())
    audit = model_routing._load_store()["audit"]
    assert all(row["actor"] == "operator:portfolio-research-direction-profile" for row in audit[-len(report["changes"]):])
    assert not configure(apply=True)["changes"]
    assert model_routing._load_store()["audit"] == audit


def test_job_environment_separates_luna_evidence_sol_analysis_and_opus_direction():
    configure(apply=True)
    env = _build_analysis_job_env("portfolio_positioning")
    roles = allocator_assignments_from_environment(env)
    assert [row["model"] for row in roles] == [PRIMARY_MODEL] * 4
    assert env["PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR"] == "ultra2x"
    assert market_context_processor() == source_processor() == "ultra2x"
    assert env["PORTFOLIO_POSITIONING_DEEP_SUMMARY_MODEL"] == EVIDENCE_MODEL
    for suffix in ("DEEP_CHAIRMAN_MODEL", "DEEP_COMMENTARY_MODEL", "SYNTHESIS_MODEL"):
        assert env[f"PORTFOLIO_POSITIONING_{suffix}"] == REVIEW_MODEL
    assert all("enabled" not in json.loads(env[role["key"]]) for role in ALLOCATOR_ROLES)


def test_profile_replaces_old_exposure_reviewer_without_new_lane():
    model_routing.update_model_route("portfolio.allocator-exposure-equivalence", {"model": "inclusionai/ling-3.0-flash-fin:free"})
    configure(apply=True)
    roles = allocator_assignments_from_environment(model_routing.runtime_model_environment())
    assert len(roles) == 4
    assert [row["model"] for row in roles] == [PRIMARY_MODEL] * 4


def test_reviewer_only_update_preserves_retrieval_and_other_routes():
    route_id = "portfolio.allocator-exposure-equivalence"
    model_routing.update_model_route(route_id, {"model": "inclusionai/ling-3.0-flash-fin:free"})
    for retrieval_id in RETRIEVAL_PROFILE:
        model_routing.update_model_route(retrieval_id, "ultra2x")
    before = model_routing.list_model_routes()["routes"]
    model_routing.update_model_route(route_id, {"model": FINANCIAL_REVIEW_MODEL})
    after = model_routing.list_model_routes()["routes"]
    assert [row for row in before if row["id"] != route_id] == [
        row for row in after if row["id"] != route_id]
    roles = allocator_assignments_from_environment(_build_analysis_job_env("portfolio_positioning"))
    reviewer = next(row for row in roles if row["role"] == "exposure_equivalence_reviewer")
    assert reviewer["model"] == PRIMARY_MODEL
    assert market_context_processor() == source_processor() == "ultra2x"


def test_retrieval_only_preserves_every_analysis_assignment():
    model_routing.update_model_route("portfolio.allocator-portfolio-aware", {"model": "provider/keep-operator-choice"})
    model_routing.update_model_route("portfolio.source-retrieval", "ultra2x")
    before = model_routing.list_model_routes()["routes"]
    report = configure(apply=True, retrieval_only=True)
    after = model_routing.list_model_routes()["routes"]
    assert report["profile"] == RETRIEVAL_PROFILE
    assert [row for row in before if row["id"] not in RETRIEVAL_PROFILE] == [
        row for row in after if row["id"] not in RETRIEVAL_PROFILE]
    assert market_context_processor() == source_processor() == "ultra2x"
    assert not configure(apply=True, retrieval_only=True)["changes"]


def test_example_environment_matches_the_approved_profile():
    env = dotenv_values(Path(__file__).resolve().parents[2] / ".env.example")
    specs = {row["id"]: row for row in model_routing.MODEL_ROUTE_SPECS}
    for route_id, expected in PORTFOLIO_MODEL_PROFILE.items():
        actual = env[specs[route_id]["key"]]
        assert (json.loads(actual) if isinstance(expected, dict) else actual) == expected
