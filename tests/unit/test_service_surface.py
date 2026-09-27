"""Regression tests for the public and protected Intelligence service surface."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("AUTH_DISABLED", "true")

from fastapi.testclient import TestClient

from backend import main, middleware
from backend.routers import health


class ServiceSurfaceTest(unittest.TestCase):
    def _client(self, *, api_docs_enabled: bool = False) -> TestClient:
        return TestClient(main.create_app(api_docs_enabled=api_docs_enabled))

    def test_public_health_endpoints_are_minimal(self):
        with self._client() as client:
            health_response = client.get("/healthz")
            ready_response = client.get("/readyz")
            legacy_response = client.get("/api/health")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(
            health_response.json(),
            {"status": "ok", "service": "alpha-edge-intelligence"},
        )
        self.assertEqual(ready_response.status_code, 200)
        self.assertEqual(
            ready_response.json(),
            {"status": "ready", "service": "alpha-edge-intelligence"},
        )
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(legacy_response.json(), health_response.json())

    def test_readiness_hides_storage_details_when_unavailable(self):
        with self._client() as client:
            with patch.object(
                health,
                "_storage_readiness_issues",
                return_value=["outputs directory is unavailable"],
            ):
                response = client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "not_ready", "service": "alpha-edge-intelligence"},
        )

    def test_protected_status_keeps_control_state_out_of_public_health(self):
        with self._client() as client:
            with (
                patch.object(middleware, "_AUTH_DISABLED", False),
                patch.object(middleware, "_API_TOKEN", "service-token"),
            ):
                denied = client.get("/api/v1/status")
                authorized = client.get(
                    "/api/v1/status",
                    headers={"Authorization": "Bearer service-token"},
                )

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("system_enabled", authorized.json())
        self.assertIn("shutdown_reason", authorized.json())

    def test_spa_fallback_is_limited_to_known_human_routes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            static_dir = Path(temp_dir)
            (static_dir / "assets").mkdir()
            (static_dir / "index.html").write_text("<html>Alpha Edge</html>", encoding="utf-8")
            (static_dir / "alpha-edge-intelligence.svg").write_text("<svg/>", encoding="utf-8")

            with patch.object(main, "_STATIC_DIR", static_dir):
                with self._client() as client:
                    app_route = client.get("/gantt-lab")
                    council_route = client.get("/council")
                    council_runs_route = client.get("/council/runs")
                    demo_route = client.get("/gantt-demo")
                    router_route = client.get("/announcement-router")
                    router_alias = client.get("/scenario-router")
                    portfolio_route = client.get("/portfolio-analysis")
                    portfolio_alias = client.get("/portfolio-positioning-memos")
                    mark = client.get("/alpha-edge-intelligence.svg")
                    unknown_api = client.get("/api/not-a-real-route")
                    unknown_page = client.get("/not-a-real-page")
                    disabled_docs = client.get("/docs")

        self.assertEqual(app_route.status_code, 200)
        self.assertEqual(app_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(council_route.status_code, 200)
        self.assertEqual(council_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(council_runs_route.status_code, 200)
        self.assertEqual(council_runs_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(demo_route.status_code, 200)
        self.assertEqual(demo_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(router_route.status_code, 200)
        self.assertEqual(router_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(router_alias.status_code, 200)
        self.assertEqual(router_alias.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(portfolio_route.status_code, 200)
        self.assertEqual(portfolio_route.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(portfolio_alias.status_code, 200)
        self.assertEqual(portfolio_alias.headers["content-type"].split(";", 1)[0], "text/html")
        self.assertEqual(mark.status_code, 200)
        self.assertEqual(mark.headers["content-type"].split(";", 1)[0], "image/svg+xml")
        self.assertEqual(unknown_api.status_code, 404)
        self.assertEqual(unknown_api.headers["content-type"].split(";", 1)[0], "application/json")
        self.assertEqual(unknown_page.status_code, 404)
        self.assertEqual(disabled_docs.status_code, 404)

    def test_api_docs_are_an_explicit_application_option(self):
        with self._client(api_docs_enabled=False) as disabled_client:
            disabled = disabled_client.get("/openapi.json")

        with self._client(api_docs_enabled=True) as enabled_client:
            enabled = enabled_client.get("/openapi.json")

        self.assertEqual(disabled.status_code, 404)
        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(enabled.headers["content-type"].split(";", 1)[0], "application/json")

    def test_delta_check_endpoint_has_one_canonical_handler(self):
        app = main.create_app(api_docs_enabled=True)
        matching_routes = [
            route
            for route in app.routes
            if getattr(route, "path", "") == "/api/gantt-runs/{run_id}/delta-check/latest"
        ]

        self.assertEqual(len(matching_routes), 1)
        self.assertEqual(
            matching_routes[0].endpoint.__module__,
            "backend.routers.runs",
        )
