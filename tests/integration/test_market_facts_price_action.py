import json
import sys
import types
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from backend.market_facts import (
    _build_price_action_packet,
    _commodity_profile_from_core_asset_packet,
    _commodity_values_from_core_asset_packet,
    _gather_yfinance_facts,
    _requires_resource_exposure_resolution,
    _resolve_commodity_profile,
    format_market_facts_query_prefix,
    gather_market_facts_prepass,
    minimal_market_facts_payload,
)


def _weekly_points(values):
    start = date(2025, 5, 30)
    return [
        {
            "date": (start + timedelta(days=7 * idx)).isoformat(),
            "close": value,
        }
        for idx, value in enumerate(values)
    ]


class MarketFactsPriceActionTests(unittest.TestCase):
    def test_price_action_packet_computes_bounded_market_context(self):
        values = [1.00 + (idx * 0.01) for idx in range(30)]
        values.extend([1.60, 1.55, 1.40, 1.20, 1.05, 0.92, 0.88, 0.95])
        values.extend([1.02 + (idx * 0.015) for idx in range(20)])

        packet = _build_price_action_packet(
            weekly_points=_weekly_points(values),
            current_price=1.12,
            source_url="https://finance.yahoo.com/quote/STK.AX",
            as_of_utc="2026-05-24T00:00:00Z",
        )

        self.assertEqual(packet["sample"], "weekly_adjusted_close")
        self.assertEqual(packet["points_available"], 52)
        self.assertEqual(packet["history_status"], "ok")
        self.assertEqual(len(packet["weekly_closes"]), 52)
        self.assertEqual(packet["week_52_high"]["price"], 1.6)
        self.assertEqual(packet["week_52_low"]["price"], 0.88)
        self.assertEqual(packet["current_vs_52w_high_pct"], -30.0)
        self.assertEqual(packet["current_vs_52w_low_pct"], 27.27)
        self.assertLess(packet["max_drawdown_52w_pct"], -40.0)
        self.assertIsNotNone(packet["volatility_13w_annualized_pct"])
        self.assertIn("do not infer causes", packet["interpretation_note"])

    def test_minimal_market_facts_payload_includes_price_action(self):
        price_action = _build_price_action_packet(
            weekly_points=_weekly_points([1.0 + idx * 0.01 for idx in range(52)]),
            current_price=1.5,
            source_url="https://finance.yahoo.com/quote/ABC.AX",
            as_of_utc="2026-05-24T00:00:00Z",
        )
        market_facts = {
            "normalized_facts": {
                "current_price": 1.5,
                "market_cap": None,
                "shares_outstanding": None,
                "currency": "AUD",
            },
            "price_action": price_action,
        }

        payload = minimal_market_facts_payload(market_facts)
        self.assertIn("price_action", payload)
        self.assertEqual(payload["price_action"]["current_price"], 1.5)
        self.assertEqual(len(payload["price_action"]["weekly_closes"]), 52)

        prefix = format_market_facts_query_prefix(market_facts)
        parsed = json.loads(prefix)
        self.assertIn("price_action", parsed)
        self.assertIn("weekly_closes", parsed["price_action"])

    def test_short_history_is_labeled_partial_for_recent_listing_or_ticker_change(self):
        packet = _build_price_action_packet(
            weekly_points=_weekly_points([0.20, 0.24, 0.18, 0.22, 0.27]),
            current_price=0.27,
            source_url="https://finance.yahoo.com/quote/NEW.AX",
            as_of_utc="2026-05-24T00:00:00Z",
        )

        self.assertEqual(packet["points_available"], 5)
        self.assertEqual(packet["history_status"], "partial_history")
        self.assertEqual(len(packet["weekly_closes"]), 5)
        self.assertIsNone(packet["return_13w_pct"])
        self.assertIn("partial_history", packet["interpretation_note"])

    def test_empty_price_action_is_not_injected(self):
        market_facts = {
            "normalized_facts": {
                "current_price": None,
                "market_cap": None,
                "shares_outstanding": None,
                "currency": "AUD",
            },
            "price_action": {},
        }

        payload = minimal_market_facts_payload(market_facts)
        self.assertNotIn("price_action", payload)
        self.assertEqual(format_market_facts_query_prefix(market_facts), "")


class CriticalMineralsMarketFactsTests(unittest.IsolatedAsyncioTestCase):
    def test_resource_exposure_resolver_scope_is_limited_to_ambiguous_templates(self):
        self.assertTrue(_requires_resource_exposure_resolution("rare_earths_critical_minerals", None))
        self.assertTrue(_requires_resource_exposure_resolution("base_metals_miner", None))
        self.assertTrue(_requires_resource_exposure_resolution("diversified_miner", None))
        self.assertFalse(_requires_resource_exposure_resolution("gold_miner", None))
        self.assertFalse(_requires_resource_exposure_resolution("copper_miner", None))

    def test_critical_minerals_template_resolves_at4_core_assets(self):
        profile = _resolve_commodity_profile(
            "rare_earths_critical_minerals",
            "rare_earths_critical_minerals",
            company_name="American Tungsten & Antimony",
            ticker="ASX:AT4",
        )

        self.assertEqual(profile, "antimony_tungsten")

    def test_critical_minerals_template_does_not_default_to_ndpr(self):
        profile = _resolve_commodity_profile(
            "rare_earths_critical_minerals",
            "rare_earths_critical_minerals",
            company_name="Generic Critical Minerals Ltd",
            ticker="ASX:GCM",
        )

        self.assertIsNone(profile)

    def test_supplementary_macro_lane_resolves_at4_core_assets(self):
        from backend.council.stage1_xai_lane import _resolve_template_commodity_profile

        profile = _resolve_template_commodity_profile(
            "rare_earths_critical_minerals",
            context_text="Run full analysis on American Tungsten & Antimony (ASX:AT4)",
        )

        self.assertEqual(profile, "antimony_tungsten")

    def test_grok_core_asset_packet_digest_maps_primary_commodities(self):
        packet = {
            "status": "ok",
            "core_assets": [
                {"asset_name": "Refinery", "commodity": "antimony", "role": "processing"},
                {"asset_name": "Mine", "commodity": "tungsten", "role": "secondary"},
            ],
            "primary_commodities": ["antimony", "tungsten"],
            "commodity_profile": "unknown",
            "confidence": 0.91,
        }

        self.assertEqual(_commodity_profile_from_core_asset_packet(packet), "antimony_tungsten")

    def test_grok_core_asset_packet_digest_maps_market_prices(self):
        packet = {
            "status": "ok",
            "primary_commodities": ["antimony", "tungsten"],
            "commodity_profile": "antimony_tungsten",
            "market_prices": [
                {
                    "commodity": "antimony",
                    "benchmark": "antimony metal",
                    "price_usd": "17,250",
                    "unit": "usd_per_tonne",
                    "source_url": "https://example.com/antimony",
                },
                {
                    "commodity": "tungsten",
                    "benchmark": "APT",
                    "price_usd": 3087.5,
                    "unit": "usd_per_mtu",
                    "source_url": "https://example.com/tungsten",
                },
                {
                    "commodity": "antimony",
                    "benchmark": "invalid precious-metals unit",
                    "price_usd": 536.6,
                    "unit": "usd_per_oz",
                    "source_url": "https://example.com/bad-unit",
                },
            ],
        }

        values = _commodity_values_from_core_asset_packet(packet, "antimony_tungsten")

        self.assertEqual(values, {
            "antimony_price_usd_t": 17_250,
            "tungsten_apt_price_usd_mtu": 3087.5,
        })

    @patch("backend.market_facts._fetch_critical_minerals_core_asset_packet_xai", new_callable=AsyncMock)
    @patch("backend.market_facts._tavily_search", new_callable=AsyncMock)
    @patch("backend.market_facts._gather_yfinance_facts", new_callable=AsyncMock)
    async def test_at4_injects_grok_antimony_tungsten_prices_not_ndpr(
        self,
        mock_yfinance: AsyncMock,
        mock_tavily: AsyncMock,
        mock_core_assets: AsyncMock,
    ):
        mock_core_assets.return_value = {
            "attempted": True,
            "success": True,
            "model": "grok-4-1-fast-reasoning",
            "resolved_profile": "antimony_tungsten",
            "confidence": 0.94,
            "packet": {
                "status": "ok",
                "company_name": "American Tungsten & Antimony",
                "ticker": "ASX:AT4",
                "core_assets": [
                    {"asset_name": "Del Sol", "commodity": "antimony", "role": "processing"},
                    {"asset_name": "White Spar", "commodity": "tungsten", "role": "exploration"},
                ],
                "primary_commodities": ["antimony", "tungsten"],
                "commodity_profile": "antimony_tungsten",
                "market_prices": [
                    {
                        "commodity": "antimony",
                        "benchmark": "antimony metal",
                        "price_usd": 17_250,
                        "unit": "usd_per_tonne",
                        "source_url": "https://example.com/antimony",
                    },
                    {
                        "commodity": "tungsten",
                        "benchmark": "tungsten APT",
                        "price_usd": 3087.5,
                        "unit": "usd_per_mtu",
                        "source_url": "https://example.com/tungsten",
                    },
                ],
                "confidence": 0.94,
                "evidence_urls": ["https://example.com/at4"],
                "notes": [],
            },
            "price_values": {
                "antimony_price_usd_t": 17_250,
                "tungsten_apt_price_usd_mtu": 3087.5,
            },
            "source_urls": [
                "https://example.com/at4",
                "https://example.com/antimony",
                "https://example.com/tungsten",
            ],
        }
        mock_yfinance.return_value = {
            "normalized_facts": {
                "current_price": 0.069,
                "market_cap": 125_832_864,
                "market_cap_m": 125.832864,
                "shares_outstanding": 1_823_664_739,
                "shares_outstanding_m": 1823.664739,
                "enterprise_value": None,
                "enterprise_value_m": None,
                "currency": "AUD",
                "commodity_profile": "antimony_tungsten",
                "antimony_price_usd_t": None,
                "antimony_price_aud_t": None,
                "tungsten_apt_price_usd_mtu": None,
                "tungsten_apt_price_aud_mtu": None,
            },
            "price_action": {},
            "source_urls": ["https://finance.yahoo.com/quote/AT4.AX"],
            "notes": [],
            "error": "",
        }

        market_facts = await gather_market_facts_prepass(
            ticker="ASX:AT4",
            company_name="American Tungsten & Antimony",
            exchange="ASX",
            template_id="rare_earths_critical_minerals",
            company_type="rare_earths_critical_minerals",
        )

        normalized = market_facts.get("normalized_facts") or {}
        classification = market_facts.get("core_asset_classification") or {}
        self.assertEqual(normalized.get("commodity_profile"), "antimony_tungsten")
        self.assertEqual(normalized.get("core_commodity_focus"), "antimony and tungsten")
        self.assertEqual(classification.get("resolved_profile"), "antimony_tungsten")
        self.assertEqual((classification.get("packet") or {}).get("primary_commodities"), ["antimony", "tungsten"])
        self.assertAlmostEqual(normalized.get("antimony_price_usd_t"), 17_250)
        self.assertAlmostEqual(normalized.get("tungsten_apt_price_usd_mtu"), 3087.5)
        self.assertIsNone(normalized.get("antimony_price_aud_t"))
        self.assertIsNone(normalized.get("tungsten_apt_price_aud_mtu"))
        self.assertIsNone(normalized.get("ndpr_oxide_price_usd_kg"))
        self.assertIn("Grok commodity-exposure resolver selected antimony_tungsten.", market_facts.get("reason") or "")
        self.assertIn("Applied Grok commodity benchmark prices.", market_facts.get("reason") or "")
        self.assertIn("https://example.com/antimony", market_facts.get("source_urls") or [])
        mock_tavily.assert_not_awaited()

        prefix = format_market_facts_query_prefix(market_facts)
        self.assertIn("core_commodity_focus", prefix)
        self.assertIn("antimony and tungsten", prefix)
        self.assertIn("antimony_price_usd_t", prefix)
        self.assertIn("tungsten_apt_price_usd_mtu", prefix)
        self.assertNotIn("ndpr_oxide", prefix)

    @patch("backend.market_facts._fetch_critical_minerals_core_asset_packet_xai", new_callable=AsyncMock)
    @patch("backend.market_facts._tavily_search", new_callable=AsyncMock)
    @patch("backend.market_facts._gather_yfinance_facts", new_callable=AsyncMock)
    async def test_base_metals_uses_resolver_and_only_injects_supported_prices(
        self,
        mock_yfinance: AsyncMock,
        mock_tavily: AsyncMock,
        mock_core_assets: AsyncMock,
    ):
        mock_core_assets.return_value = {
            "attempted": True,
            "success": True,
            "model": "grok-4-1-fast-reasoning",
            "resolved_profile": "copper",
            "confidence": 0.88,
            "packet": {
                "core_assets": [
                    {"asset_name": "Main mine", "commodity": "copper", "role": "primary"},
                    {"asset_name": "Main mine", "commodity": "zinc", "role": "secondary"},
                ],
                "primary_commodities": ["copper", "zinc"],
                "commodity_profile": "copper",
            },
            "price_values": {"copper_price_usd_lb": 4.5},
            "source_urls": ["https://example.com/copper"],
        }
        mock_yfinance.return_value = {
            "normalized_facts": {
                "current_price": 1.0,
                "market_cap": 1_000_000,
                "market_cap_m": 1.0,
                "shares_outstanding": 1_000_000,
                "shares_outstanding_m": 1.0,
                "enterprise_value": None,
                "enterprise_value_m": None,
                "currency": "AUD",
                "commodity_profile": None,
                "copper_price_usd_lb": None,
                "copper_price_aud_lb": None,
            },
            "price_action": {},
            "source_urls": ["https://finance.yahoo.com/quote/BML.AX"],
            "notes": [],
            "error": "",
        }

        market_facts = await gather_market_facts_prepass(
            ticker="ASX:BML",
            company_name="Base Metals Ltd",
            exchange="ASX",
            template_id="base_metals_miner",
            company_type="base_metals_miner",
        )

        normalized = market_facts.get("normalized_facts") or {}
        classification = market_facts.get("core_asset_classification") or {}
        self.assertEqual(classification.get("scope"), "ambiguous_resource_exposure")
        self.assertEqual(normalized.get("commodity_profile"), "copper")
        self.assertAlmostEqual(normalized.get("copper_price_usd_lb"), 4.5)
        self.assertEqual((classification.get("packet") or {}).get("primary_commodities"), ["copper", "zinc"])
        self.assertIn("https://example.com/copper", market_facts.get("source_urls") or [])
        mock_core_assets.assert_awaited_once()
        mock_tavily.assert_not_awaited()

    @patch("backend.market_facts._fetch_critical_minerals_core_asset_packet_xai", new_callable=AsyncMock)
    @patch("backend.market_facts._tavily_search", new_callable=AsyncMock)
    @patch("backend.market_facts._gather_yfinance_facts", new_callable=AsyncMock)
    async def test_critical_minerals_does_not_guess_commodity_when_grok_fails(
        self,
        mock_yfinance: AsyncMock,
        mock_tavily: AsyncMock,
        mock_core_assets: AsyncMock,
    ):
        mock_core_assets.return_value = {
            "attempted": True,
            "success": False,
            "model": "grok-4-1-fast-reasoning",
            "error": "ReadTimeout",
            "resolved_profile": None,
        }
        mock_yfinance.return_value = {
            "normalized_facts": {
                "current_price": 0.069,
                "market_cap": 125_832_864,
                "market_cap_m": 125.832864,
                "shares_outstanding": 1_823_664_739,
                "shares_outstanding_m": 1823.664739,
                "enterprise_value": None,
                "enterprise_value_m": None,
                "currency": "AUD",
                "commodity_profile": None,
            },
            "price_action": {},
            "source_urls": ["https://finance.yahoo.com/quote/AT4.AX"],
            "notes": [],
            "error": "",
        }

        market_facts = await gather_market_facts_prepass(
            ticker="ASX:AT4",
            company_name="American Tungsten & Antimony",
            exchange="ASX",
            template_id="rare_earths_critical_minerals",
            company_type="rare_earths_critical_minerals",
        )

        normalized = market_facts.get("normalized_facts") or {}
        self.assertIsNone(normalized.get("commodity_profile"))
        self.assertIsNone(normalized.get("core_commodity_focus"))
        self.assertIsNone(normalized.get("antimony_price_usd_t"))
        self.assertIsNone(normalized.get("tungsten_apt_price_usd_mtu"))
        self.assertIsNone(normalized.get("ndpr_oxide_price_usd_kg"))
        mock_tavily.assert_not_awaited()


class MarketFactsYfinanceEdgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_yfinance_no_data_returns_explicit_error(self):
        original_yfinance = sys.modules.get("yfinance")

        class EmptySeries:
            def dropna(self):
                return self

            def __len__(self):
                return 0

        class EmptyHistory:
            empty = True

            def get(self, _key):
                return EmptySeries()

        class EmptyTicker:
            fast_info = {}
            info = {}

            def __init__(self, _symbol):
                pass

            def history(self, *args, **kwargs):
                return EmptyHistory()

        sys.modules["yfinance"] = types.SimpleNamespace(Ticker=EmptyTicker)
        try:
            result = await _gather_yfinance_facts(
                {"yahoo_symbol": "MISSING.AX", "exchange": "ASX"},
                timeout=1.0,
            )
        finally:
            if original_yfinance is None:
                sys.modules.pop("yfinance", None)
            else:
                sys.modules["yfinance"] = original_yfinance

        self.assertEqual(result["normalized_facts"], {})
        self.assertNotEqual(result.get("error"), "")
        self.assertNotIn("price_action", result)
        self.assertIn("No yfinance data returned", result["error"])


if __name__ == "__main__":
    unittest.main()
