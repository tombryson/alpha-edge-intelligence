import json
from copy import deepcopy
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI

from backend import model_routing as routing
from backend.portfolio_roles import allocator_assignments_from_environment
from backend.routers.model_routing import router


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(routing, "_STORE_PATH", tmp_path / "routing.json")
    for spec in routing.MODEL_ROUTE_SPECS:
        monkeypatch.delenv(spec["key"], raising=False)
    monkeypatch.delenv(routing.LEGACY_ALLOCATOR_KEY, raising=False)
    routing.list_model_routes()
    return routing._STORE_PATH


def group(payload, name):
    return next(row for row in payload["route_groups"] if row["id"] == f"portfolio.group-{name}")


def test_four_groups_cover_each_portfolio_stage_exactly_once(store):
    payload = routing.list_model_routes()
    assert len(payload["route_groups"]) == 4
    members = [member["id"] for row in payload["route_groups"] for member in row["members"]]
    portfolio = [row["id"] for row in payload["routes"] if row["app"] == "Portfolio Analysis"]
    assert len(members) == len(set(members)) == len(portfolio) == 10
    assert set(members) == set(portfolio)
    assert all(row["provider"] == member["provider"] for row in payload["route_groups"]
        for member in payload["routes"] if member["id"] in {item["id"] for item in row["members"]})


def test_reading_groups_preserves_mixed_models_and_exposes_the_members(store):
    routing.update_model_route("portfolio.allocator-macro-prior", {"model": "provider/first"})
    routing.update_model_route("portfolio.allocator-defensive-review", {"model": "provider/second"})
    before = store.read_bytes()
    row = group(routing.list_model_routes(), "analysis")
    assert row["mixed"] and row["effective_value"] == {"model": ""}
    assert {member["model"] for member in row["members"]} >= {"provider/first", "provider/second"}
    assert row["has_override"] and row["source"] == "mixed"
    assert store.read_bytes() == before


@pytest.mark.parametrize("name,value", [("research", "ultra2x"), ("evidence", "~deepseek/deepseek-flash-latest"),
    ("analysis", "provider/model:free"), ("decision", "provider/final")])
def test_group_save_is_one_write_and_reaches_the_real_runner(store, monkeypatch, name, value):
    before = deepcopy(routing._load_store())
    save = Mock(wraps=routing._save_store)
    monkeypatch.setattr(routing, "_save_store", save)
    result = routing.update_model_route(f"portfolio.group-{name}", {"model": value})
    assert save.call_count == 1
    row = group(result, name)
    assert row["effective_value"] == {"model": value} and not row["mixed"]
    assert row["source"] == "runtime_override"
    assert value in row["model_freshness"]
    spec = routing._GROUPS_BY_ID[row["id"]]
    keys = {routing._SPECS_BY_ID[identifier]["key"] for identifier in spec["members"]}
    after = routing._load_store()
    assert set(after["overrides"]) - set(before["overrides"]) == keys
    assert len(after["audit"]) == len(before["audit"]) + 1
    assert len(after["audit"][-1]["member_changes"]) == len(keys)
    environment = routing.runtime_model_environment()
    for key in keys:
        exported = json.loads(environment[key])["model"] if routing._SPECS_BY_KEY[key]["kind"] == "role" else environment[key]
        assert exported == value
    if name == "analysis":
        assert {role["model"] for role in allocator_assignments_from_environment(environment)} == {value}


def test_group_reset_restores_configured_members_without_flattening_them(store):
    original = group(routing.list_model_routes(), "analysis")
    routing.update_model_route("portfolio.group-analysis", "provider/shared")
    routing.update_model_route("portfolio.group-decision", "provider/leave-alone")
    result = routing.clear_model_route_override("portfolio.group-analysis")
    restored = group(result, "analysis")
    assert [row["model"] for row in restored["members"]] == [row["model"] for row in original["members"]]
    assert restored["mixed"] and not restored["has_override"]
    assert group(result, "decision")["effective_value"] == {"model": "provider/leave-alone"}


@pytest.mark.parametrize("name,value", [("research", "provider/model"), ("analysis", "bad value"),
    ("decision", ["provider/a", "provider/b"]), ("evidence", {"model": None})])
def test_bad_group_input_never_partially_changes_assignments(store, name, value):
    before = store.read_bytes()
    with pytest.raises(ValueError):
        routing.update_model_route(f"portfolio.group-{name}", value)
    assert store.read_bytes() == before


def test_reset_validation_failure_is_atomic(store, monkeypatch):
    routing.update_model_route("portfolio.group-analysis", "provider/shared")
    monkeypatch.setenv(routing.ALLOCATOR_ROLES[0]["key"], "bad json")
    before = store.read_bytes()
    with pytest.raises(ValueError):
        routing.clear_model_route_override("portfolio.group-analysis")
    assert store.read_bytes() == before


@pytest.mark.asyncio
async def test_group_api_roundtrip_and_legacy_member_edits_remain_visible(store):
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.put("/api/model-routing/portfolio.group-decision", json={"value": {"model": "provider/final"}})
        assert result.status_code == 200
        assert not group(result.json(), "decision")["mixed"]
        await client.put("/api/model-routing/portfolio.synthesis", json={"value": "provider/exception"})
        result = await client.get("/api/model-routing")
        assert group(result.json(), "decision")["mixed"]
        assert (await client.put("/api/model-routing/portfolio.group-decision", json={"value": "bad value"})).status_code == 422
        assert (await client.delete("/api/model-routing/portfolio.group-decision")).status_code == 200
