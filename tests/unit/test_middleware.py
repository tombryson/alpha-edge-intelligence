"""Focused regression tests for the Council API authentication boundary."""

import asyncio
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AUTH_DISABLED", "true")

from fastapi import HTTPException, Response

from backend import middleware
from backend.routers import scenario_router_routes


class _Request:
    def __init__(self, method: str, path: str, headers=None):
        self.method = method
        self.url = type("URL", (), {"path": path})()
        self.headers = headers or {}


async def _ok_response(_request):
    return Response(status_code=204)


class MiddlewareTest(unittest.TestCase):
    def test_scenario_router_ingest_bypasses_only_global_bearer_gate(self):
        with (
            patch.object(middleware, "_AUTH_DISABLED", False),
            patch.object(middleware, "_API_TOKEN", "broad-api-token"),
        ):
            for path in (
                "/api/announcement-router/process-announcement",
                "/api/scenario-router/enqueue-announcement",
            ):
                response = asyncio.run(
                    middleware.auth_middleware(
                        _Request("POST", path),
                        _ok_response,
                    )
                )
                self.assertEqual(response.status_code, 204)

    def test_other_api_routes_still_require_the_global_bearer_token(self):
        with (
            patch.object(middleware, "_AUTH_DISABLED", False),
            patch.object(middleware, "_API_TOKEN", "broad-api-token"),
        ):
            response = asyncio.run(
                middleware.auth_middleware(
                    _Request("POST", "/api/announcement-router/mock-evaluate"),
                    _ok_response,
                )
            )

        self.assertEqual(response.status_code, 401)

    def test_public_operational_endpoints_bypass_the_global_bearer_token(self):
        with (
            patch.object(middleware, "_AUTH_DISABLED", False),
            patch.object(middleware, "_API_TOKEN", "broad-api-token"),
        ):
            for path in ("/healthz", "/readyz", "/api/health"):
                response = asyncio.run(
                    middleware.auth_middleware(
                        _Request("GET", path),
                        _ok_response,
                    )
                )
                self.assertEqual(response.status_code, 204)

    def test_auth_status_requires_a_valid_token(self):
        with (
            patch.object(middleware, "_AUTH_DISABLED", False),
            patch.object(middleware, "_API_TOKEN", "test-api-token"),
        ):
            for token, status in ((None, 401), ("wrong-token", 401), ("test-api-token", 204)):
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                response = asyncio.run(middleware.auth_middleware(_Request("GET", "/api/auth/status", headers), _ok_response))
                self.assertEqual(response.status_code, status)

    def test_only_post_is_treated_as_scenario_router_ingress(self):
        self.assertTrue(
            middleware._is_scenario_router_ingest_request(
                _Request("POST", "/api/scenario-router/process-announcement")
            )
        )
        self.assertFalse(
            middleware._is_scenario_router_ingest_request(
                _Request("GET", "/api/scenario-router/process-announcement")
            )
        )
        self.assertTrue(
            middleware._is_scenario_router_ingest_request(
                _Request("POST", "/api/freshness/process-announcement/")
            )
        )
        self.assertTrue(
            middleware._is_scenario_router_ingest_request(
                _Request("POST", "/api/announcement-router/enqueue-announcement")
            )
        )

    def test_scenario_router_ingest_still_requires_its_dedicated_secret(self):
        with (
            patch.object(
                scenario_router_routes,
                "SCENARIO_ROUTER_WEBHOOK_SECRET",
                "router-secret",
            ),
            patch.object(
                scenario_router_routes,
                "SCENARIO_ROUTER_WEBHOOK_REQUIRE_SECRET",
                True,
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                scenario_router_routes._check_scenario_router_webhook_secret(
                    _Request("POST", "/api/scenario-router/process-announcement")
                )

            self.assertEqual(raised.exception.status_code, 401)
            self.assertEqual(
                raised.exception.detail,
                "Invalid scenario router webhook secret.",
            )

            scenario_router_routes._check_scenario_router_webhook_secret(
                _Request(
                    "POST",
                    "/api/scenario-router/process-announcement",
                    {"x-scenario-router-secret": "router-secret"},
                )
            )
