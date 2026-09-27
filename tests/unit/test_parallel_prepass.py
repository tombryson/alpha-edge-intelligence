import asyncio
import json
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from backend import model_routing
from backend.research.providers.parallel_prepass import ParallelPrepassProvider


@pytest.fixture(autouse=True)
def local_routing(tmp_path, monkeypatch):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    monkeypatch.delenv("COUNCIL_PREPASS_WEB_PROCESSOR", raising=False)


def test_structured_discovery_reuses_paid_task_and_preserves_basis(tmp_path):
    calls = []
    source = {"url": "https://announcements.asx.com.au/a.pdf", "title": "Funding",
              "published_at": "2026-08-19", "content": "Up to US$18m subject to negotiation, not received."}

    def handle(request):
        calls.append(request)
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["processor"] == "ultra2x"
            assert body["task_spec"]["output_schema"]["type"] == "json"
            assert "cash/burn" in body["input"]
            return httpx.Response(202, json={"run_id": "trun_test"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, json={"output": {"content": {"sources": [source, source,
                {**source, "url": "file:///etc/passwd"}], "unanswered_questions": ["Award execution?"]},
                "basis": [{"citations": [{"url": source["url"]}]}]}})
        return httpx.Response(200, json={"status": "completed"})

    checkpoint = tmp_path / "task.json"
    provider = ParallelPrepassProvider(checkpoint, api_key="not-a-secret", transport=httpx.MockTransport(handle))
    result = asyncio.run(provider.gather("AT4 filings", ticker="ASX:AT4"))
    assert result["result_count"] == 1
    assert result["results"][0]["content"] == source["content"]
    assert asyncio.run(provider.gather("AT4 filings", ticker="ASX:AT4")) == result
    assert len(calls) == 3
    stored = json.loads(checkpoint.read_text())
    assert stored["result"]["output"]["basis"]
    assert "not-a-secret" not in checkpoint.read_text()


@pytest.mark.parametrize("status", [402, 500])
def test_rejected_or_uncertain_post_is_never_repeated(tmp_path, status):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "provider failure"})

    provider = ParallelPrepassProvider(tmp_path / "task.json", api_key="test", transport=httpx.MockTransport(handle))
    assert asyncio.run(provider.gather("AT4"))["error"]
    assert asyncio.run(provider.gather("AT4"))["error"]
    assert len(calls) == 1


def test_pending_task_resumes_gets_without_new_post(tmp_path):
    calls = []

    def handle(request):
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": "trun_saved"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, json={"output": {"content": {"sources": [], "unanswered_questions": []}}})
        return httpx.Response(200, json={"status": "completed"})

    provider = ParallelPrepassProvider(tmp_path / "task.json", api_key="test",
        transport=httpx.MockTransport(handle), timeout_seconds=0)
    assert "pending" in asyncio.run(provider.gather("EIQ"))["error"]
    provider.timeout_seconds = 60
    assert asyncio.run(provider.gather("EIQ"))["provider_metadata"]["status"] == "completed"
    assert calls == ["POST", "GET", "GET"]


def test_processor_visible_and_editable_in_routing(tmp_path):
    route = next(row for row in model_routing.list_model_routes()["routes"]
                 if row["id"] == "council.prepass-web-research")
    assert route["provider"] == "Parallel"
    assert route["effective_value"] == "ultra2x"
    model_routing.update_model_route(route["id"], "ultra")
    assert ParallelPrepassProvider(tmp_path / "task.json", api_key="test").model == "ultra"
    assert model_routing.runtime_model_environment()[route["key"]] == "ultra"


@pytest.mark.parametrize("web_success", [True, False])
def test_pipeline_keeps_native_asx_lane_and_web_discoveries(tmp_path, monkeypatch, web_success):
    from tests.integration import test_perplexity_pdf_dump as pipeline

    args = pipeline._build_parser().parse_args([
        "--query", "AT4 filings", "--ticker", "ASX:AT4", "--exchange", "asx",
        "--output-dir", str(tmp_path / "prepass"),
    ])
    assert args.web_research_provider == "parallel"
    native_url = "https://announcements.asx.com.au/asxpdf/20260819/pdf/native.pdf"
    web_url = "https://announcements.asx.com.au/asxpdf/20260817/pdf/discovered.pdf"
    provider = Mock()
    provider.gather = AsyncMock(return_value={"results": [
        {"url": web_url, "title": "Financing", "content": "Conditional", "published_at": "2026-08-17"}
    ] if web_success else [], "error": "" if web_success else "Insufficient credit"})
    monkeypatch.setattr(pipeline, "ParallelPrepassProvider", Mock(return_value=provider))
    legacy = Mock(side_effect=AssertionError("Perplexity must not run"))
    monkeypatch.setattr(pipeline, "PerplexityResearchProvider", legacy)
    monkeypatch.setattr(pipeline, "load_dotenv", lambda: None)
    monkeypatch.setattr(pipeline, "_resolve_official_issuer_site", lambda **kwargs: {})
    market = AsyncMock(return_value=[])
    native = AsyncMock(return_value=[{"url": native_url, "title": "Quarterly", "published_at": "2026-08-19",
                                      "deterministic_source_kind": "asx_direct_announcement_pdf"}])
    monkeypatch.setattr(pipeline, "scrape_marketindex_announcements", market)
    monkeypatch.setattr(pipeline, "_discover_direct_asx_primary_sources", native)

    class CapturedSources(Exception):
        pass

    async def capture(**kwargs):
        urls = {row["url"] for row in kwargs["rows"]}
        assert native_url in urls
        if web_success:
            assert web_url in urls
        raise CapturedSources

    monkeypatch.setattr(pipeline, "_apply_issuer_source_mini_filter", capture)
    with pytest.raises(CapturedSources):
        asyncio.run(pipeline._run(args))
    provider.gather.assert_awaited_once()
    market.assert_awaited_once()
    native.assert_awaited_once()
    legacy.assert_not_called()
