from datetime import date
import pytest

from backend import model_routing


def test_parallel_portfolio_source_processor_is_visible_and_exported(tmp_path, monkeypatch):
    from backend.portfolio_retrieval import source_processor
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    monkeypatch.delenv("PORTFOLIO_POSITIONING_SOURCE_PROCESSOR", raising=False)
    route = next(row for row in model_routing.list_model_routes()["routes"] if row["id"] == "portfolio.source-retrieval")
    assert route["provider"] == "Parallel" and route["effective_value"] == "ultra2x"
    assert source_processor() == "ultra2x"
    model_routing.update_model_route("portfolio.source-retrieval", "ultra")
    assert source_processor() == "ultra"
    assert model_routing.runtime_model_environment()[route["key"]] == "ultra"


@pytest.mark.parametrize("value", ["ultra4x", "  ultra4x  ", "ultra2x", "ultra4x-fast"])
def test_macro_news_uses_parallel_processor(tmp_path, monkeypatch, value):
    from backend.portfolio_retrieval import market_context_processor
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    expected = value.strip()
    result = model_routing.update_model_route("portfolio.macro-news", value)
    route = next(row for row in result["routes"] if row["id"] == "portfolio.macro-news")
    assert route["effective_value"] == expected
    assert route["provider"] == "Parallel"
    assert market_context_processor() == expected
    assert model_routing._load_store()["overrides"][route["key"]] == expected
    assert model_routing.runtime_model_environment()[route["key"]] == expected


def test_legacy_grok_override_does_not_become_parallel_processor(tmp_path, monkeypatch):
    from backend.portfolio_retrieval import market_context_processor
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    monkeypatch.delenv("PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR", raising=False)
    key = "PORTFOLIO_POSITIONING_MACRO_NEWS_MODEL"
    monkeypatch.setenv(key, "x-ai/grok-4.6")
    model_routing._save_store({"version": 1, "overrides": {key: "x-ai/grok-4.6"}, "audit": []})
    route = next(row for row in model_routing.list_model_routes()["routes"] if row["id"] == "portfolio.macro-news")
    assert route["effective_value"] == market_context_processor() == "ultra2x"
    assert key not in model_routing.runtime_model_environment()
    assert model_routing._load_store()["overrides"][key] == "x-ai/grok-4.6"
    result = model_routing.update_model_route("council.chairman", "x-ai/grok-4.6")
    assert next(row for row in result["routes"] if row["id"] == "council.chairman")["effective_value"] == "x-ai/grok-4.6"


@pytest.mark.parametrize("value", ["x-ai/grok-4.6", "ultra 4x", "~provider/model", ""])
def test_macro_news_rejects_model_ids_in_processor_field(tmp_path, monkeypatch, value):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    with pytest.raises(ValueError):
        model_routing.update_model_route("portfolio.macro-news", value)


@pytest.mark.parametrize("route_id", ["council.openrouter-stage1", "council.local-stage1-and-stage2"])
def test_shared_pool_accepts_provider_suffix_and_updates_both_routes(tmp_path, monkeypatch, route_id):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    models = ["inclusionai/ling-3.0-flash-fin:free", "provider/model:thinking"]
    result = model_routing.update_model_route(route_id, models)
    for route in result["routes"]:
        if route["key"] in model_routing._SHARED_COUNCIL_KEYS:
            assert route["effective_value"] == models
    for key in model_routing._SHARED_COUNCIL_KEYS:
        assert model_routing.get_runtime_model_list(key, ["wrong/model"]) == models
        assert model_routing.runtime_model_environment()[key] == ",".join(models)
    model_routing.clear_model_route_override(route_id)
    assert not model_routing._load_store()["overrides"]


def test_shared_pool_migrates_latest_edit_and_unifies_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    lane, pool = model_routing._SHARED_COUNCIL_KEYS
    monkeypatch.setenv(lane, "provider/lane")
    monkeypatch.setenv(pool, "provider/pool")
    assert model_routing.get_runtime_model_list(pool, []) == ["provider/lane"]
    model_routing._save_store({"version": 1, "overrides": {lane: ["provider/old"], pool: ["provider/new"]}, "audit": [{"key": lane}, {"key": pool}]})
    assert model_routing.get_runtime_model_list(lane, []) == ["provider/new"]
    assert model_routing.get_runtime_model_list(pool, []) == ["provider/new"]


@pytest.mark.parametrize("model", ["provider/model:", "provider/model:free:bad", "provider/model bad", "provider/model\nother", "~", "~~provider/model", "provider/~model", "~provider/model bad"])
def test_model_suffix_validation_rejects_malformed_identifiers(tmp_path, monkeypatch, model):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    with pytest.raises(ValueError):
        model_routing.update_model_route("council.chairman", model)


@pytest.mark.parametrize("route_id,kind", [
    ("council.openrouter-stage1", "list"),
    ("council.chairman", "single"),
    ("portfolio.allocator-macro-prior", "role"),
])
@pytest.mark.parametrize("model", ["~deepseek/deepseek-flash-latest", "~openai/gpt-astra-latest", "~provider/model:free"])
def test_alias_round_trip_preserves_prefix(tmp_path, monkeypatch, route_id, kind, model):
    import json
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    value = [model] if kind == "list" else {"model": model} if kind == "role" else model
    result = model_routing.update_model_route(route_id, value)
    route = next(row for row in result["routes"] if row["id"] == route_id)
    assert route["effective_value"] == value
    persisted = next(row for row in model_routing.list_model_routes()["routes"] if row["id"] == route_id)
    assert persisted["effective_value"] == value
    runtime = model_routing.runtime_model_environment()[route["key"]]
    assert (json.loads(runtime) if kind == "role" else runtime) == ({"model": model} if kind == "role" else model)


def test_runtime_override_round_trip_and_subprocess_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "model_routing.json")

    updated = model_routing.update_model_route(
        "council.openrouter-stage1",
        "x-ai/grok-4.6, qwen/qwen3.8-flash",
    )
    route = next(row for row in updated["routes"] if row["id"] == "council.openrouter-stage1")

    assert route["effective_value"] == ["x-ai/grok-4.6", "qwen/qwen3.8-flash"]
    assert route["source"] == "runtime_override"
    assert model_routing.runtime_model_environment()["PERPLEXITY_STAGE1_OPENROUTER_MODELS"] == (
        "x-ai/grok-4.6,qwen/qwen3.8-flash"
    )

    cleared = model_routing.clear_model_route_override("council.openrouter-stage1")
    route = next(row for row in cleared["routes"] if row["id"] == "council.openrouter-stage1")
    assert route["source"] != "runtime_override"


def test_runtime_override_rejects_invalid_model_identifier(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "model_routing.json")

    try:
        model_routing.update_model_route("council.chairman", "not a valid model")
    except ValueError as exc:
        assert "valid model identifier" in str(exc)
    else:
        raise AssertionError("expected invalid model identifier to be rejected")


def test_model_freshness_exposes_reviewed_and_unverified_dates() -> None:
    current = model_routing._model_freshness(
        "openai/gpt-5.6-sol", today=date(2026, 8, 30)
    )
    assert current == {
        "model": "openai/gpt-5.6-sol",
        "status": "current",
        "released_at": "2026-07-09",
        "age_days": 52,
        "date_basis": "Provider release",
        "last_verified_at": "2026-08-30",
        "source_url": "https://openai.com/index/gpt-5-6/",
    }

    ageing = model_routing._model_freshness(
        "openai/gpt-5.6-sol", today=date(2026, 12, 10)
    )
    assert ageing["status"] == "ageing"
    stale = model_routing._model_freshness(
        "openai/gpt-5.6-sol", today=date(2027, 1, 6)
    )
    assert stale["status"] == "stale"

    unverified = model_routing._model_freshness("example/unreviewed-model")
    assert unverified["status"] == "unverified"
    assert unverified["released_at"] is None


def test_model_routes_include_freshness_for_each_effective_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "model_routing.json")
    route = next(
        row
        for row in model_routing.list_model_routes()["routes"]
        if row["id"] == "council.perplexity-stage1"
    )

    assert route["model_freshness"]["openai/gpt-5.6-sol"]["released_at"] == "2026-07-09"
