import asyncio
import copy
import json
import threading
import time

import httpx
import pytest
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import StreamingResponse

from backend.portfolio_read_store import PortfolioReadStore
from backend.routers import runs


def artifact():
    return {"analysis_kind": "portfolio_positioning", "updated_at": "2026-09-17T12:00:00Z",
            "structured_data": {"analysis_kind": "portfolio_positioning", "executive_summary": "Saved summary",
                "asset_class_targets": [{"asset_class": "cash", "target_pct": 100, "min_pct": 100,
                    "max_pct": 100, "rationale": "Preserved rationale", "fact_ids": ["fact-a"]}],
                "current_sleeve_decisions": []},
            "chairman_memo_markdown": "# Saved memo\n\n" + "Original text. " * 1000,
            "evidence_brief": {"facts": [{"id": "fact-a", "metric": "yield"}],
                "source_packet": {"sources": [{"url": "https://example.org", "excerpt": "Source text. " * 10000}]}},
            "stage_receipts": [{"stage": "research", "status": "complete"}]}


def write(path, payload):
    path.write_text(json.dumps(payload))
    return path


def build(path, payload):
    if not payload.get("memo"):
        return None
    return {"summary": {"id": path.name, "label": payload["memo"]}, "memo": payload}


def test_index_persists_and_only_reparses_changed_files(tmp_path):
    a = write(tmp_path / "a.json", {"memo": "A"})
    b = write(tmp_path / "b.json", {"memo": "B"})
    write(tmp_path / "stock.json", {"stock": True})
    write(tmp_path / "a.checkpoint.json", {"memo": "Not a memo"})
    calls = []

    def track(path, payload):
        calls.append(path.name)
        return build(path, payload)

    first = PortfolioReadStore()
    assert len(first.list([tmp_path], 50, track)) == 2
    assert set(calls) == {"a.json", "b.json", "stock.json"}
    calls.clear()
    for store in (first, PortfolioReadStore()):
        assert len(store.list([tmp_path], 50, track)) == 2
        assert store.memo(a, track) == {"memo": "A"}
        assert calls == [], "Neither a warm request nor a restart reopens unchanged artifacts"
    write(a, {"memo": "Revised A"})
    b.unlink()
    assert first.list([tmp_path], 50, track) == [{"id": "a.json", "label": "Revised A"}]
    assert calls == ["a.json"]
    assert first.memo(a, track)["memo"] == "Revised A"
    assert not first._memo_path(b).exists()


def test_corrupt_derived_cache_falls_back_to_original(tmp_path):
    path = write(tmp_path / "memo.json", {"memo": "Original"})
    store = PortfolioReadStore()
    store.list([tmp_path], 50, build)
    (tmp_path / ".portfolio-index-v1.json").write_text("not json")
    store._memo_path(path).write_text("[]")
    restarted = PortfolioReadStore()
    assert restarted.memo(path, build) == {"memo": "Original"}
    assert len(restarted.list([tmp_path], 50, build)) == 1


def test_delete_clears_persistent_and_memory_read_models(tmp_path):
    path = write(tmp_path / "memo.json", {"memo": "Original"})
    store = PortfolioReadStore()
    store.list([tmp_path], 50, build)
    path.unlink()
    store.forget(path)
    assert not store._memo_path(path).exists()
    assert str(path.resolve()) not in store._memos
    assert PortfolioReadStore().list([tmp_path], 50, build) == []


def test_read_only_cache_does_not_break_reading(tmp_path, monkeypatch):
    import backend.portfolio_read_store as module
    path = write(tmp_path / "memo.json", {"memo": "Original"})

    def unavailable(*args, **kwargs):
        raise PermissionError("Read-only cache")

    monkeypatch.setattr(module.tempfile, "NamedTemporaryFile", unavailable)
    store = PortfolioReadStore()
    assert store.memo(path, build)["memo"] == "Original"
    assert len(store.list([tmp_path], 50, build)) == 1


@pytest.fixture
def read_api(tmp_path, monkeypatch):
    source = artifact()
    path = write(tmp_path / "memo.json", source)
    monkeypatch.setattr(runs, "portfolio_read_store", PortfolioReadStore())
    monkeypatch.setattr(runs, "_portfolio_positioning_search_roots", lambda: [tmp_path])
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: tmp_path / name)
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    app.include_router(runs.router)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/events")
    async def events():
        async def stream():
            yield "data: " + "x" * 2000 + "\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream")

    return app, path, source


@pytest.mark.asyncio
async def test_reader_is_small_and_full_research_remains_available(read_api):
    app, path, source = read_api
    original = path.read_bytes()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        light = await client.get("/api/portfolio-positioning-runs/memo.json?view=memo")
        full = await client.get("/api/portfolio-positioning-runs/memo.json")
        research = await client.get("/api/portfolio-positioning-runs/memo.json?view=research")
    assert light.status_code == full.status_code == research.status_code == 200
    memo = light.json()
    assert memo["memo_markdown"] == full.json()["memo_markdown"]
    assert memo["structured_data"]["executive_summary"] == source["structured_data"]["executive_summary"]
    assert memo["structured_data"]["asset_class_targets"][0]["rationale"] == "Preserved rationale"
    assert "evidence_brief" not in memo and "stage_receipts" not in memo
    assert len(light.content) < len(full.content) / 4
    assert research.json()["evidence_brief"] == source["evidence_brief"]
    for key, value in source["structured_data"].items():
        assert research.json()["structured_data"][key] == value
    assert "memo_markdown" not in research.json()
    assert light.headers["content-encoding"] == "gzip"
    assert light.headers["cache-control"] == "private, no-cache"
    assert research.headers["cache-control"] == "private, no-store"
    assert path.read_bytes() == original, "Read models must never rewrite the saved analysis"


@pytest.mark.asyncio
async def test_etag_revalidates_without_reading_artifacts_and_changes_on_updates(read_api, monkeypatch):
    app, path, source = read_api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/api/portfolio-positioning-runs/memo.json?view=memo")
        original_builder = runs._build_portfolio_read_models

        def unexpected(*args):
            raise AssertionError("Unchanged memo should not be rebuilt")

        monkeypatch.setattr(runs, "_build_portfolio_read_models", unexpected)
        cached = await client.get("/api/portfolio-positioning-runs/memo.json?view=memo", headers={"If-None-Match": first.headers["etag"]})
        assert cached.status_code == 304 and not cached.content
        for validator in ("*", first.headers["etag"].removeprefix("W/")):
            assert (await client.get("/api/portfolio-positioning-runs/memo.json?view=memo", headers={"If-None-Match": validator})).status_code == 304
        assert (await client.get("/api/portfolio-positioning-runs/memo.json?view=memo")).json() == first.json()
        monkeypatch.setattr(runs, "_build_portfolio_read_models", original_builder)
        source["chairman_memo_markdown"] = "Updated memo"
        write(path, source)
        changed = await client.get("/api/portfolio-positioning-runs/memo.json?view=memo", headers={"If-None-Match": first.headers["etag"]})
        assert changed.status_code == 200 and changed.json()["memo_markdown"] == "Updated memo"
        assert changed.headers["etag"] != first.headers["etag"]
        path.unlink()
        assert (await client.get("/api/portfolio-positioning-runs/memo.json?view=memo")).status_code == 404


@pytest.mark.asyncio
async def test_cold_index_does_not_block_other_requests(read_api, monkeypatch):
    app, _, _ = read_api
    entered, release = threading.Event(), threading.Event()
    original = runs.portfolio_read_store.list

    def slow(*args):
        entered.set()
        release.wait(2)
        return original(*args)

    monkeypatch.setattr(runs.portfolio_read_store, "list", slow)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        listing = asyncio.create_task(client.get("/api/portfolio-positioning-runs"))
        await asyncio.to_thread(entered.wait, 1)
        try:
            start = time.perf_counter()
            memo = await client.get("/api/portfolio-positioning-runs/memo.json?view=memo")
            assert memo.status_code == 200
            assert time.perf_counter() - start < .5
            assert not listing.done()
        finally:
            release.set()
        assert (await listing).status_code == 200


@pytest.mark.asyncio
async def test_compression_does_not_buffer_event_streams(read_api):
    app, _, _ = read_api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/events", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers
    assert response.text.startswith("data: ")


def test_reader_supports_nested_legacy_documents(tmp_path):
    source = artifact()
    original = copy.deepcopy(source)
    source.pop("chairman_memo_markdown")
    source["stage3_result_primary"] = {"structured_data": source.pop("structured_data"),
        "chairman_document": {"content_markdown": original["chairman_memo_markdown"]}}
    path = write(tmp_path / "old.json", source)
    assert runs._build_portfolio_read_models(path, source)["memo"]["memo_markdown"] == original["chairman_memo_markdown"].strip()


def test_reader_moves_old_generated_conditions_to_research_without_rewriting_saved_memo(tmp_path):
    source = artifact()
    source["workflow_version"] = 4
    source["structured_data"]["asset_class_targets"][0]["research_gaps"] = [
        {"question_id": "cash-yield", "question": "What yield is available on the cash account?"}]
    source["chairman_memo_markdown"] = "# Portfolio Positioning Memo\n\nAny change remains conditional on the outstanding research below.\n\n- What yield is available on the cash account?"
    path = write(tmp_path / "generated.json", source)
    original = path.read_bytes()
    saved = copy.deepcopy(source)
    markdown = runs._build_portfolio_read_models(path, source)["memo"]["memo_markdown"]
    main, supporting = markdown.split("## Supporting Research", 1)
    assert "Preserved rationale" in main
    assert "Any change remains conditional" not in markdown
    assert "What yield" not in main and "What yield" in supporting
    assert source == saved and path.read_bytes() == original


def test_current_sleeve_reader_uses_final_decisions_and_snapshot_not_sealed_baseline(tmp_path):
    source = artifact()
    source.update(workflow_version=4, portfolio_snapshot={"portfolio": {"cash_pct": 10}, "asset_classes": [
        {"asset_class": "energy", "display_name": "Energy producers", "portfolio_pct": 70},
        {"asset_class": "silver", "portfolio_pct": 15}, {"asset_class": "other", "portfolio_pct": 5}]},
        macro_positioning={"asset_class_targets": [{"asset_class": "energy", "target_pct": 30, "thesis_conviction": "MEDIUM"},
            {"asset_class": "cash", "target_pct": 70}], "current_sleeve_actions": [
            {"asset_class": "energy", "action": "TRIM", "rationale": "Final concentration judgment"},
            {"asset_class": "silver", "action": "EXIT", "target_pct": 0, "rationale": "Explicit final exit"},
            {"asset_class": "cash", "action": "ADD", "rationale": "Retain liquidity"}]})
    source["structured_data"]["current_sleeve_decisions"] = [
        {"asset_class": "energy", "action": "ADD", "current_pct": 90, "rationale": "Stale baseline"},
        {"asset_class": "other", "action": "EXIT", "rationale": "Earlier proposal"}]
    original = copy.deepcopy(source)
    path = write(tmp_path / "settled.json", source)
    rows = runs._build_portfolio_read_models(path, source)["memo"]["structured_data"]["current_sleeve_decisions"]
    by_asset = {row["asset_class"]: row for row in rows}
    assert set(by_asset) == {"energy", "silver", "other", "cash"}
    assert by_asset["energy"] == {"asset_class": "energy", "display_name": "Energy producers", "current_pct": 70,
        "action": "TRIM", "rationale": "Final concentration judgment", "model_thesis_conviction": "MEDIUM"}
    assert by_asset["silver"]["action"] == "EXIT"
    assert by_asset["other"]["action"] == "REVIEW" and "rationale" not in by_asset["other"]
    assert by_asset["cash"]["current_pct"] == 10
    assert source == original, "Presentation must not revise the archive or its sealed baseline"


def test_legacy_current_sleeve_rows_remain_as_recorded(tmp_path):
    source = artifact()
    source["structured_data"]["current_sleeve_decisions"] = [
        {"asset_class": "energy", "current_pct": 34, "action": "TRIM", "rationale": "Legacy judgment"}]
    path = write(tmp_path / "legacy.json", source)
    rows = runs._build_portfolio_read_models(path, source)["memo"]["structured_data"]["current_sleeve_decisions"]
    assert rows == source["structured_data"]["current_sleeve_decisions"]
