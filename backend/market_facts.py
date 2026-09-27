"""Deterministic market-facts prepass for ticker-level baseline fields."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
import re
import statistics
from typing import Any, Dict, Optional, Tuple, List
from urllib.parse import urlparse

import httpx

from .config import (
    CRITICAL_MINERALS_CORE_ASSET_XAI_ENABLED,
    CRITICAL_MINERALS_CORE_ASSET_XAI_MAX_TOKENS,
    CRITICAL_MINERALS_CORE_ASSET_XAI_MODEL,
    CRITICAL_MINERALS_CORE_ASSET_XAI_TEMPERATURE,
    CRITICAL_MINERALS_CORE_ASSET_XAI_TIMEOUT_SECONDS,
    MARKET_FACTS_TIMEOUT_SECONDS,
    TAVILY_API_KEY,
    XAI_API_KEY,
    XAI_API_URL,
)
from .model_routing import get_runtime_model_value


CRITICAL_MINERALS_DYNAMIC_PROFILE = "company_core_critical_minerals"

# These templates deliberately do not imply one reliable commodity benchmark.
# Resolve their actual economic exposure before injecting any supported prices;
# single-commodity resource templates stay on deterministic provider paths.
RESOURCE_EXPOSURE_DYNAMIC_TEMPLATE_IDS = frozenset(
    {
        "rare_earths_critical_minerals",
        "base_metals_miner",
        "diversified_miner",
    }
)

SUPPORTED_CRITICAL_MINERALS_PROFILES = {
    "antimony_tungsten",
    "antimony",
    "tungsten",
    "rare_earths",
    "lithium",
    "copper",
    "uranium",
    "silver",
    "gold",
    "iron_ore",
    "coal",
    "oil_gas",
}

CRITICAL_MINERALS_COMMODITY_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("antimony_tungsten", ("antimony_tungsten", "antimony and tungsten", "antimony/tungsten")),
    ("antimony", ("antimony", "stibnite")),
    ("tungsten", ("tungsten", "wolfram", "apt", "ammonium paratungstate")),
    ("rare_earths", ("rare earth", "ree", "ndpr", "neodymium", "praseodymium", "dysprosium", "terbium", "monazite")),
    ("lithium", ("lithium", "spodumene", "brine", "lce", "carbonate", "hydroxide")),
    ("copper", ("copper", "cu ", "cu-", "cu/", "cathode", "concentrate")),
    ("uranium", ("uranium", "u3o8")),
    ("silver", ("silver", " ag ", "ag-", "ag/")),
    ("gold", ("gold", " au ", "au-", "au/")),
)


EXCHANGE_TO_YAHOO_SUFFIX = {
    "ASX": ".AX",
    "NYSE": "",
    "NASDAQ": "",
    "TSX": ".TO",
    "TSXV": ".V",
    "LSE": ".L",
    "AIM": ".L",
}

TEMPLATE_COMMODITY_PROFILE = {
    "gold_miner": "gold",
    "copper_miner": "copper",
    "lithium_miner": "lithium",
    "silver_miner": "silver",
    "uranium_miner": "uranium",
    "iron_ore_miner": "iron_ore",
    "rare_earths_critical_minerals": CRITICAL_MINERALS_DYNAMIC_PROFILE,
    "coal_miner": "coal",
    "energy_oil_gas": "oil_gas",
}

COMPANY_TYPE_COMMODITY_PROFILE = {
    "gold_miner": "gold",
    "copper_miner": "copper",
    "lithium_miner": "lithium",
    "silver_miner": "silver",
    "uranium_miner": "uranium",
    "iron_ore_miner": "iron_ore",
    "rare_earths_critical_minerals": CRITICAL_MINERALS_DYNAMIC_PROFILE,
    "coal_miner": "coal",
    "energy_oil_gas": "oil_gas",
}

COMMODITY_FIELDS: Tuple[str, ...] = (
    "gold_price_usd_oz",
    "gold_price_aud_oz",
    "copper_price_usd_lb",
    "copper_price_aud_lb",
    "lithium_price_usd_kg",
    "lithium_price_aud_kg",
    "silver_price_usd_oz",
    "silver_price_aud_oz",
    "uranium_price_usd_lb",
    "uranium_price_aud_lb",
    "brent_price_usd_bbl",
    "brent_price_aud_bbl",
    "wti_price_usd_bbl",
    "wti_price_aud_bbl",
    "henry_hub_price_usd_mmbtu",
    "henry_hub_price_aud_mmbtu",
    "iron_ore_price_usd_t",
    "iron_ore_price_aud_t",
    "newcastle_coal_price_usd_t",
    "newcastle_coal_price_aud_t",
    "hard_coking_coal_price_usd_t",
    "hard_coking_coal_price_aud_t",
    "ndpr_oxide_price_usd_kg",
    "ndpr_oxide_price_aud_kg",
    "antimony_price_usd_t",
    "antimony_price_aud_t",
    "tungsten_apt_price_usd_mtu",
    "tungsten_apt_price_aud_mtu",
)
PRICE_ACTION_WEEKLY_POINTS = 52

COMMODITY_FALLBACK_CONFIG: Dict[str, Dict[str, Any]] = {
    "uranium": {
        "usd_key": "uranium_price_usd_lb",
        "aud_key": "uranium_price_aud_lb",
        "price_queries": (
            "current uranium spot price usd per lb",
            "current U3O8 spot price usd/lb",
        ),
        "price_patterns": (
            r"(?:uranium|u3o8)[^\n]{0,80}?(?:US\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:lb|lbs|pound)",
            r"(?:US\$|USD\s*)([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:lb|lbs|pound)",
        ),
    },
    "iron_ore": {
        "usd_key": "iron_ore_price_usd_t",
        "aud_key": "iron_ore_price_aud_t",
        "price_queries": (
            "current iron ore 62% Fe spot price USD per tonne",
            "current iron ore benchmark 62 Fe price USD/t",
        ),
        "price_patterns": (
            r"(?:iron ore|62% fe|62 fe)[^\n]{0,100}?(?:US\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton)",
            r"(?:US\$|USD\s*)([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton)",
        ),
    },
    "coal": {
        "usd_key": "newcastle_coal_price_usd_t",
        "aud_key": "newcastle_coal_price_aud_t",
        "price_queries": (
            "current Newcastle thermal coal spot price USD per tonne",
            "current hard coking coal price USD per tonne",
        ),
        "price_patterns": (
            r"(?:newcastle|thermal coal|coal)[^\n]{0,100}?(?:US\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton)",
            r"(?:US\$|USD\s*)([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton)",
        ),
    },
    "rare_earths": {
        "usd_key": "ndpr_oxide_price_usd_kg",
        "aud_key": "ndpr_oxide_price_aud_kg",
        "price_queries": (
            "current NdPr oxide price USD per kg",
            "current neodymium praseodymium oxide price USD/kg",
        ),
        "price_patterns": (
            r"(?:ndpr|neodymium praseodymium|praseodymium neodymium)[^\n]{0,100}?(?:US\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:kg|kilogram)",
            r"(?:US\$|USD\s*)([0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:kg|kilogram)",
        ),
    },
    "antimony": {
        "usd_key": "antimony_price_usd_t",
        "aud_key": "antimony_price_aud_t",
        "price_queries": (
            "current antimony metal price USD per tonne",
            "current antimony ingot price USD per tonne",
        ),
        "price_patterns": (
            r"(?:antimony|sb)[^\n]{0,120}?(?:US\$|USD\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton|mt)",
            r"(?:US\$|USD\s*)([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton|mt)",
        ),
    },
    "tungsten": {
        "usd_key": "tungsten_apt_price_usd_mtu",
        "aud_key": "tungsten_apt_price_aud_mtu",
        "price_queries": (
            "current tungsten APT price USD per mtu",
            "current ammonium paratungstate APT price USD per mtu",
        ),
        "price_patterns": (
            r"(?:tungsten|apt|ammonium paratungstate)[^\n]{0,120}?(?:US\$|USD\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:mtu)",
            r"(?:US\$|USD\s*)([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:mtu)",
        ),
    },
    "antimony_tungsten": {
        "price_items": [
            {
                "profile": "antimony",
                "usd_key": "antimony_price_usd_t",
                "aud_key": "antimony_price_aud_t",
                "price_queries": (
                    "current antimony metal price USD per tonne",
                    "current antimony ingot price USD per tonne",
                ),
                "price_patterns": (
                    r"(?:antimony|sb)[^\n]{0,120}?(?:US\$|USD\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton|mt)",
                    r"(?:US\$|USD\s*)([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:t|tonne|metric ton|mt)",
                ),
            },
            {
                "profile": "tungsten",
                "usd_key": "tungsten_apt_price_usd_mtu",
                "aud_key": "tungsten_apt_price_aud_mtu",
                "price_queries": (
                    "current tungsten APT price USD per mtu",
                    "current ammonium paratungstate APT price USD per mtu",
                ),
                "price_patterns": (
                    r"(?:tungsten|apt|ammonium paratungstate)[^\n]{0,120}?(?:US\$|USD\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:mtu)",
                    r"(?:US\$|USD\s*)([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:/|per)?\s*(?:mtu)",
                ),
            },
        ],
    },
}

AUDUSD_PATTERNS: Tuple[str, ...] = (
    r"(?:AUD\s*/\s*USD|AUDUSD|Australian Dollar[^\\n]{0,40}US Dollar)[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
    r"\b1\s*AUD[^0-9]{0,20}(?:=|≈|about)?[^0-9]{0,20}(?:US\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)",
)


def _infer_critical_minerals_commodity_profile(context_text: str) -> Optional[str]:
    """Infer the actual commodity focus for the generic critical-minerals template."""
    text = f" {str(context_text or '').strip().lower()} "
    if not text.strip():
        return None
    has_antimony = any(token in text for token in ("antimony", "stibnite"))
    has_tungsten = any(token in text for token in ("tungsten", "wolfram", "ammonium paratungstate"))
    if has_antimony and has_tungsten:
        return "antimony_tungsten"
    for profile, tokens in CRITICAL_MINERALS_COMMODITY_PATTERNS:
        if any(token in text for token in tokens):
            return profile
    return None


def _commodity_focus_label(profile: Optional[str]) -> Optional[str]:
    labels = {
        "antimony_tungsten": "antimony and tungsten",
        "antimony": "antimony",
        "tungsten": "tungsten",
        "rare_earths": "rare earths/NdPr",
        "lithium": "lithium",
        "copper": "copper",
        "uranium": "uranium",
        "silver": "silver",
        "gold": "gold",
        "iron_ore": "iron ore",
        "coal": "coal",
        "oil_gas": "oil and gas",
    }
    return labels.get(str(profile or "").strip().lower())


def _extract_responses_output_text(data: Dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    output = data.get("output")
    texts: List[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            item_text = item.get("text")
            if isinstance(item_text, str) and item_text.strip():
                texts.append(item_text.strip())
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    txt = part.get("text")
                    if isinstance(txt, str) and txt.strip():
                        texts.append(txt.strip())
    return texts[-1] if texts else ""


def _parse_json_object_from_text(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _commodity_profile_from_core_asset_packet(packet: Dict[str, Any]) -> Optional[str]:
    """Digest a Grok core-assets JSON packet into the market-facts commodity profile."""
    if not isinstance(packet, dict):
        return None
    explicit_profile = str(packet.get("commodity_profile") or "").strip().lower()
    explicit_profile = explicit_profile.replace("-", "_").replace(" ", "_")
    if explicit_profile in SUPPORTED_CRITICAL_MINERALS_PROFILES:
        return explicit_profile

    commodities: List[str] = []
    for key in ("primary_commodities", "core_commodities", "commodities"):
        values = packet.get(key)
        if isinstance(values, list):
            commodities.extend(str(value or "") for value in values)
    assets = packet.get("core_assets")
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            for key in ("commodity", "commodity_name", "material", "mineral", "asset_type"):
                value = str(asset.get(key) or "").strip()
                if value:
                    commodities.append(value)

    text = " ".join(commodities)
    return _infer_critical_minerals_commodity_profile(text)


def _normalize_market_price_unit(unit: Any, benchmark: Any = "") -> str:
    text = f"{unit or ''} {benchmark or ''}".strip().lower()
    if not text:
        return ""
    text = text.replace("us$", "usd").replace("$", "usd")
    text = re.sub(r"[\s_\-]+", " ", text)
    if re.search(r"\b(oz|ounce|ounces|troy ounce|troy ounces)\b", text):
        return "usd_per_oz"
    if re.search(r"\b(lb|lbs|pound|pounds)\b", text):
        return "usd_per_lb"
    if re.search(r"\b(mtu)\b", text):
        return "usd_per_mtu"
    if re.search(r"\b(kg|kilogram|kilograms)\b", text):
        return "usd_per_kg"
    if re.search(r"\b(bbl|barrel|barrels)\b", text):
        return "usd_per_bbl"
    if re.search(r"\b(mmbtu)\b", text):
        return "usd_per_mmbtu"
    if re.search(r"\b(t|tonne|tonnes|metric ton|metric tons|mt)\b", text):
        return "usd_per_tonne"
    return ""


def _commodity_price_field_for_item(item: Dict[str, Any], profile: Optional[str]) -> Optional[str]:
    commodity = str(item.get("commodity") or "").strip().lower()
    benchmark = str(item.get("benchmark") or "").strip().lower()
    haystack = f"{commodity} {benchmark} {profile or ''}".lower()
    unit = _normalize_market_price_unit(item.get("unit"), benchmark)

    if re.search(r"\b(antimony|sb|stibnite)\b", haystack) and unit == "usd_per_tonne":
        return "antimony_price_usd_t"
    if re.search(r"\b(tungsten|apt|ammonium paratungstate|wolfram)\b", haystack) and unit == "usd_per_mtu":
        return "tungsten_apt_price_usd_mtu"
    if re.search(r"\b(ndpr|rare earth|rare-earth|neodymium|praseodymium)\b", haystack) and unit == "usd_per_kg":
        return "ndpr_oxide_price_usd_kg"
    if "lithium" in haystack and unit == "usd_per_kg":
        return "lithium_price_usd_kg"
    if re.search(r"\b(copper|cu)\b", haystack) and unit == "usd_per_lb":
        return "copper_price_usd_lb"
    if re.search(r"\b(uranium|u3o8)\b", haystack) and unit == "usd_per_lb":
        return "uranium_price_usd_lb"
    if "silver" in haystack and unit == "usd_per_oz":
        return "silver_price_usd_oz"
    if "gold" in haystack and unit == "usd_per_oz":
        return "gold_price_usd_oz"
    if "iron ore" in haystack and unit == "usd_per_tonne":
        return "iron_ore_price_usd_t"
    if "coal" in haystack and unit == "usd_per_tonne":
        return "newcastle_coal_price_usd_t"
    if ("brent" in haystack or profile == "oil_gas") and unit == "usd_per_bbl":
        return "brent_price_usd_bbl"
    if "wti" in haystack and unit == "usd_per_bbl":
        return "wti_price_usd_bbl"
    if "henry hub" in haystack and unit == "usd_per_mmbtu":
        return "henry_hub_price_usd_mmbtu"
    return None


def _commodity_values_from_core_asset_packet(
    packet: Dict[str, Any],
    profile: Optional[str],
) -> Dict[str, float]:
    if not isinstance(packet, dict):
        return {}
    market_prices = packet.get("market_prices")
    if not isinstance(market_prices, list):
        return {}

    values: Dict[str, float] = {}
    for item in market_prices:
        if not isinstance(item, dict):
            continue
        field = _commodity_price_field_for_item(item, profile)
        if not field or field not in COMMODITY_FIELDS:
            continue
        value = _to_float(item.get("price_usd"))
        if value is None:
            value = _to_float(item.get("price"))
        if value is None or not math.isfinite(value) or value <= 0:
            continue
        values[field] = value
    return values


def _core_asset_packet_urls(packet: Dict[str, Any]) -> List[str]:
    if not isinstance(packet, dict):
        return []
    urls: List[str] = []
    candidates = list(packet.get("evidence_urls") or [])
    market_prices = packet.get("market_prices")
    if isinstance(market_prices, list):
        for item in market_prices:
            if not isinstance(item, dict):
                continue
            source_url = item.get("source_url")
            if isinstance(source_url, list):
                candidates.extend(source_url)
            else:
                candidates.append(source_url)
    for raw_url in candidates:
        url = str(raw_url or "").strip()
        if url and url.startswith(("http://", "https://")) and url not in urls:
            urls.append(url)
    return urls


def _build_critical_minerals_core_asset_prompt(
    *,
    ticker: str,
    company_name: str,
    exchange: str,
) -> str:
    return f"""You are classifying a listed resources company with potentially ambiguous or multi-commodity exposure for an investment-analysis market-data prepass.

Use web search and primary/company/exchange sources where possible. Identify the commodities that actually drive valuation for the company, not the broad template category.
After the core commodities are identified, explicitly search public commodity benchmark sources for current/recent prices for those commodities.

Company: {company_name or "unknown"}
Ticker: {ticker or "unknown"}
Exchange: {exchange or "unknown"}

Return ONLY a valid JSON object with this exact shape:
{{
  "status": "ok|uncertain|not_resources",
  "company_name": "string",
  "ticker": "string",
  "core_assets": [
    {{
      "asset_name": "string",
      "commodity": "antimony|tungsten|rare_earths|lithium|copper|uranium|silver|gold|iron_ore|coal|oil_gas|zinc|nickel|lead|tin|manganese|bauxite|other",
      "role": "primary|secondary|byproduct|processing|exploration",
      "evidence": "short factual basis"
    }}
  ],
  "primary_commodities": ["commodity strings"],
  "commodity_profile": "antimony_tungsten|antimony|tungsten|rare_earths|lithium|copper|uranium|silver|gold|iron_ore|coal|oil_gas|none|unknown",
  "market_prices": [
    {{
      "commodity": "commodity string",
      "benchmark": "short benchmark name",
      "price_usd": 0.0,
      "unit": "usd_per_oz|usd_per_lb|usd_per_tonne|usd_per_kg|usd_per_mtu|usd_per_bbl|usd_per_mmbtu",
      "as_of_date": "YYYY-MM-DD|null",
      "source_url": "https://...",
      "evidence": "short factual basis"
    }}
  ],
  "confidence": 0.0,
  "evidence_urls": ["https://..."],
  "notes": ["short strings"]
}}

Rules:
- If the company is antimony/tungsten, return "commodity_profile": "antimony_tungsten".
- Do not return rare_earths unless NdPr/REE/monazite/separation/magnet rare-earth exposure is genuinely valuation-driving.
- Keep the exact commodity in core_assets and primary_commodities. For zinc, nickel, lead, tin, manganese, bauxite, or another commodity without a supported benchmark field, set commodity_profile to unknown unless a supported primary commodity also drives valuation. Do not fabricate or force an unsupported price into another commodity's field.
- In market_prices, use the native benchmark unit for each commodity. Use usd_per_oz only for precious metals such as gold or silver; use usd_per_tonne for antimony metal, usd_per_mtu for tungsten APT, usd_per_kg for NdPr oxide or lithium chemicals, and usd_per_lb for copper or uranium.
- For antimony_tungsten companies, search separately for antimony metal/ingot USD per tonne and tungsten APT USD per mtu, and include both entries when current/recent public benchmarks can be sourced.
- Do not leave market_prices empty merely because the company does not publish commodity prices; use public commodity benchmark sources where available.
- Include market_prices only when you can identify a current/recent benchmark price and source. Do not invent prices, convert units, or use stale values without making the date explicit.
- If the core commodity cannot be determined from reliable sources, return "commodity_profile": "unknown" and "confidence" below 0.5.
- Do not include markdown, commentary, or citations outside JSON.
""".strip()


async def _fetch_critical_minerals_core_asset_packet_xai(
    *,
    ticker: str,
    company_name: str,
    exchange: str,
    timeout: float,
) -> Dict[str, Any]:
    """Ask Grok/xAI for a strict JSON packet describing company core assets."""
    if not CRITICAL_MINERALS_CORE_ASSET_XAI_ENABLED:
        return {"attempted": False, "success": False, "error": "core_asset_xai_disabled"}
    if not XAI_API_KEY:
        return {"attempted": False, "success": False, "error": "xai_api_key_missing"}

    prompt = _build_critical_minerals_core_asset_prompt(
        ticker=ticker,
        company_name=company_name,
        exchange=exchange,
    )
    model = str(
        get_runtime_model_value(
            "CRITICAL_MINERALS_CORE_ASSET_XAI_MODEL",
            CRITICAL_MINERALS_CORE_ASSET_XAI_MODEL or "grok-4-1-fast-reasoning",
        )
    ).strip()
    endpoint = str(XAI_API_URL or "https://api.x.ai/v1/responses").strip()
    timeout_seconds = max(10.0, float(CRITICAL_MINERALS_CORE_ASSET_XAI_TIMEOUT_SECONDS))
    max_tokens = max(256, int(CRITICAL_MINERALS_CORE_ASSET_XAI_MAX_TOKENS))
    temperature = max(0.0, min(1.5, float(CRITICAL_MINERALS_CORE_ASSET_XAI_TEMPERATURE)))

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": prompt,
                    "tools": [{"type": "web_search"}, {"type": "x_search"}],
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            http_status = int(response.status_code)
            if response.status_code >= 400:
                return {
                    "attempted": True,
                    "success": False,
                    "model": model,
                    "http_status": http_status,
                    "error": f"xai_http_{response.status_code}:{(response.text or '').strip()[:800]}",
                    "prompt": prompt,
                }
            data = response.json() if response.content else {}
    except Exception as exc:
        return {
            "attempted": True,
            "success": False,
            "model": model,
            "http_status": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "prompt": prompt,
        }

    output_text = _extract_responses_output_text(data if isinstance(data, dict) else {})
    packet = _parse_json_object_from_text(output_text)
    profile = _commodity_profile_from_core_asset_packet(packet)
    confidence = _to_float(packet.get("confidence")) if isinstance(packet, dict) else None
    success = bool(profile and (confidence is None or confidence >= 0.45))
    price_values = _commodity_values_from_core_asset_packet(packet, profile)
    source_urls = _core_asset_packet_urls(packet)
    return {
        "attempted": True,
        "success": success,
        "model": model,
        "http_status": http_status,
        "error": "" if packet else "xai_json_parse_failed",
        "prompt": prompt,
        "response_text": output_text[:4000],
        "packet": packet,
        "resolved_profile": profile,
        "confidence": confidence,
        "price_values": price_values,
        "source_urls": source_urls,
    }


def _resolve_commodity_profile(
    template_id: Optional[str],
    company_type: Optional[str],
    company_name: Optional[str] = None,
    ticker: Optional[str] = None,
) -> Optional[str]:
    template_key = str(template_id or "").strip().lower()
    company_key = str(company_type or "").strip().lower()
    allowed_profiles = {
        "gold",
        "copper",
        "lithium",
        "silver",
        "uranium",
        "iron_ore",
        "rare_earths",
        "coal",
        "oil_gas",
        "antimony",
        "tungsten",
        "antimony_tungsten",
        CRITICAL_MINERALS_DYNAMIC_PROFILE,
        "none",
        "",
    }
    if template_key == "rare_earths_critical_minerals" or company_key == "rare_earths_critical_minerals":
        inferred = _infer_critical_minerals_commodity_profile(
            " ".join(
                item
                for item in (company_name, ticker, company_type, template_id)
                if item
            )
        )
        if inferred:
            return inferred
    if template_key:
        try:
            from .template_loader import get_template_loader

            loader = get_template_loader()
            behavior = loader.get_template_behavior(template_key) or {}
            profile = str(behavior.get("commodity_profile") or "").strip().lower()
            if profile in allowed_profiles:
                if profile == CRITICAL_MINERALS_DYNAMIC_PROFILE:
                    return None
                return None if profile in {"none", ""} else profile
        except Exception:
            pass
    if template_key and template_key in TEMPLATE_COMMODITY_PROFILE:
        fallback_profile = TEMPLATE_COMMODITY_PROFILE[template_key]
        return None if fallback_profile == CRITICAL_MINERALS_DYNAMIC_PROFILE else fallback_profile
    if company_key and company_key in COMPANY_TYPE_COMMODITY_PROFILE:
        fallback_profile = COMPANY_TYPE_COMMODITY_PROFILE[company_key]
        return None if fallback_profile == CRITICAL_MINERALS_DYNAMIC_PROFILE else fallback_profile
    return None


def _requires_resource_exposure_resolution(
    template_id: Optional[str],
    company_type: Optional[str],
) -> bool:
    """Limit the xAI resolver to resource templates with ambiguous exposure."""
    return any(
        str(value or "").strip().lower() in RESOURCE_EXPOSURE_DYNAMIC_TEMPLATE_IDS
        for value in (template_id, company_type)
    )


def _parse_ticker(ticker: str) -> Dict[str, str]:
    raw = str(ticker or "").strip().upper()
    exchange = ""
    symbol = ""

    if ":" in raw:
        prefix, rest = raw.split(":", 1)
        exchange = prefix.strip().upper()
        symbol = rest.strip().upper()
    else:
        symbol = raw

    # Handle suffix-coded symbols (e.g., WWI.AX, FM.TO) when exchange prefix is missing.
    if not exchange and symbol:
        for candidate_exchange, suffix in EXCHANGE_TO_YAHOO_SUFFIX.items():
            suffix_norm = str(suffix or "").strip().upper()
            if not suffix_norm:
                continue
            if symbol.endswith(suffix_norm) and len(symbol) > len(suffix_norm):
                exchange = candidate_exchange
                symbol = symbol[: -len(suffix_norm)]
                break

    suffix = EXCHANGE_TO_YAHOO_SUFFIX.get(exchange, "")
    yahoo_symbol = f"{symbol}{suffix}" if symbol else ""
    normalized_ticker = f"{exchange}:{symbol}" if exchange and symbol else symbol

    return {
        "raw": raw,
        "exchange": exchange,
        "symbol": symbol,
        "normalized_ticker": normalized_ticker,
        "yahoo_symbol": yahoo_symbol,
    }


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "")
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale_suffix(value: float, suffix: str) -> float:
    suffix_clean = (suffix or "").strip().upper()
    scales = {
        "": 1.0,
        "K": 1_000.0,
        "THOUSAND": 1_000.0,
        "M": 1_000_000.0,
        "MM": 1_000_000.0,
        "MN": 1_000_000.0,
        "MILLION": 1_000_000.0,
        "B": 1_000_000_000.0,
        "BN": 1_000_000_000.0,
        "BILLION": 1_000_000_000.0,
        "T": 1_000_000_000_000.0,
        "TRILLION": 1_000_000_000_000.0,
    }
    return value * scales.get(suffix_clean, 1.0)


def _parse_numeric_with_suffix(raw_value: str, raw_suffix: str = "") -> Optional[float]:
    clean = (raw_value or "").strip().replace(",", "")
    if not clean:
        return None
    try:
        value = float(clean)
    except (TypeError, ValueError):
        return None
    return _scale_suffix(value, raw_suffix)


def _pick_numeric(mapping: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key not in mapping:
            continue
        parsed = _to_float(mapping.get(key))
        if parsed is not None:
            return parsed
    return None


def _pick_string(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_facts(
    *,
    current_price: Optional[float],
    market_cap: Optional[float],
    shares_outstanding: Optional[float],
    enterprise_value: Optional[float],
    currency: Optional[str],
    commodity_profile: Optional[str] = None,
    commodity_values: Optional[Dict[str, Optional[float]]] = None,
) -> Dict[str, Any]:
    normalized = {
        "current_price": current_price,
        "market_cap": market_cap,
        "market_cap_m": (market_cap / 1_000_000.0) if market_cap is not None else None,
        "shares_outstanding": shares_outstanding,
        "shares_outstanding_m": (
            shares_outstanding / 1_000_000.0
            if shares_outstanding is not None
            else None
        ),
        "enterprise_value": enterprise_value,
        "enterprise_value_m": (
            enterprise_value / 1_000_000.0
            if enterprise_value is not None
            else None
        ),
        "currency": (currency or "").strip().upper() or None,
        "commodity_profile": commodity_profile,
        "core_commodity_focus": _commodity_focus_label(commodity_profile),
    }
    for key in COMMODITY_FIELDS:
        normalized[key] = None
    if commodity_values:
        for key, value in commodity_values.items():
            if key in COMMODITY_FIELDS:
                normalized[key] = value
    return normalized


def _available_field_count(normalized_facts: Dict[str, Any]) -> int:
    keys = (
        "current_price",
        "market_cap",
        "shares_outstanding",
        "enterprise_value",
        "currency",
    )
    return sum(1 for key in keys if normalized_facts.get(key) is not None)


def _extract_positive_number(text: str, patterns: Tuple[str, ...]) -> Optional[float]:
    payload = str(text or "")
    if not payload:
        return None
    for pattern in patterns:
        for match in re.finditer(pattern, payload, flags=re.IGNORECASE):
            value = _to_float(match.group(1))
            if value is not None and math.isfinite(value) and value > 0:
                return value
    return None


def _commodity_keys_for_profile(profile: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    config = COMMODITY_FALLBACK_CONFIG.get(str(profile or "").strip().lower()) or {}
    price_items = config.get("price_items")
    if isinstance(price_items, list) and price_items:
        first = price_items[0] if isinstance(price_items[0], dict) else {}
        usd_key = str(first.get("usd_key") or "").strip() or None
        aud_key = str(first.get("aud_key") or "").strip() or None
        return usd_key, aud_key
    usd_key = str(config.get("usd_key") or "").strip() or None
    aud_key = str(config.get("aud_key") or "").strip() or None
    return usd_key, aud_key


def _commodity_key_pairs_for_profile(profile: Optional[str]) -> List[Tuple[str, Optional[str]]]:
    config = COMMODITY_FALLBACK_CONFIG.get(str(profile or "").strip().lower()) or {}
    price_items = config.get("price_items")
    if isinstance(price_items, list) and price_items:
        pairs: List[Tuple[str, Optional[str]]] = []
        for item in price_items:
            if not isinstance(item, dict):
                continue
            usd_key = str(item.get("usd_key") or "").strip()
            aud_key = str(item.get("aud_key") or "").strip() or None
            if usd_key:
                pairs.append((usd_key, aud_key))
        return pairs
    usd_key, aud_key = _commodity_keys_for_profile(profile)
    return [(usd_key, aud_key)] if usd_key else []


def _collect_tavily_payload_text(payload: Dict[str, Any]) -> str:
    pieces: List[str] = []
    answer = str(payload.get("answer") or "").strip()
    if answer:
        pieces.append(answer)
    for row in payload.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        content = str(row.get("content") or "").strip()
        if title:
            pieces.append(title)
        if content:
            pieces.append(content)
    return "\n".join(piece for piece in pieces if piece)


async def _gather_commodity_price_fallback(
    commodity_profile: Optional[str],
    timeout: float,
) -> Dict[str, Any]:
    profile = str(commodity_profile or "").strip().lower()
    config = COMMODITY_FALLBACK_CONFIG.get(profile)
    if not config:
        return {"commodity_values": {}, "source_urls": [], "notes": []}

    price_items = config.get("price_items")
    if not isinstance(price_items, list) or not price_items:
        price_items = [config]
    normalized_price_items = [item for item in price_items if isinstance(item, dict)]
    if not normalized_price_items:
        return {"commodity_values": {}, "source_urls": [], "notes": []}

    source_urls: List[str] = []
    notes: List[str] = []
    usd_values: Dict[str, float] = {}

    for item in normalized_price_items:
        usd_key = str(item.get("usd_key") or "").strip()
        price_patterns = tuple(item.get("price_patterns") or ())
        if not usd_key or usd_key not in COMMODITY_FIELDS or not price_patterns:
            continue
        usd_value: Optional[float] = None
        for query in item.get("price_queries", ()) or ():
            payload = await _tavily_search(query=str(query), timeout=timeout, max_results=4)
            if payload.get("error"):
                notes.append(f"Commodity fallback query failed: {query} ({payload['error']})")
                continue
            for result in payload.get("results", []) or []:
                url = str((result or {}).get("url") or "").strip()
                if url and url not in source_urls:
                    source_urls.append(url)
            usd_value = _extract_positive_number(
                _collect_tavily_payload_text(payload),
                price_patterns,
            )
            if usd_value is not None:
                break
        if usd_value is not None:
            usd_values[usd_key] = usd_value

    if not usd_values:
        return {"commodity_values": {}, "source_urls": source_urls, "notes": notes}

    audusd_rate: Optional[float] = None
    fx_payload = await _tavily_search("current AUD/USD exchange rate", timeout=timeout, max_results=4)
    if fx_payload.get("error"):
        notes.append(f"FX fallback query failed: {fx_payload['error']}")
    else:
        for result in fx_payload.get("results", []) or []:
            url = str((result or {}).get("url") or "").strip()
            if url and url not in source_urls:
                source_urls.append(url)
        audusd_rate = _extract_positive_number(
            _collect_tavily_payload_text(fx_payload),
            AUDUSD_PATTERNS,
        )

    commodity_values: Dict[str, Optional[float]] = {}
    for item in normalized_price_items:
        usd_key = str(item.get("usd_key") or "").strip()
        aud_key = str(item.get("aud_key") or "").strip()
        if usd_key not in usd_values:
            continue
        usd_value = usd_values[usd_key]
        commodity_values[usd_key] = usd_value
        if aud_key:
            commodity_values[aud_key] = (usd_value / audusd_rate) if (audusd_rate and audusd_rate > 0) else None
    notes.append(f"Applied {profile} commodity fallback.")
    return {
        "commodity_values": commodity_values,
        "source_urls": source_urls,
        "notes": notes,
    }


def _sanitize_normalized_facts(normalized_facts: Dict[str, Any]) -> Dict[str, Any]:
    """Drop implausible parsed values from fallback snippets."""
    out = dict(normalized_facts or {})

    price = _to_float(out.get("current_price"))
    if price is not None and not (0.00001 <= price <= 100_000):
        out["current_price"] = None

    market_cap = _to_float(out.get("market_cap"))
    # Market cap should be at least in low millions for listed equities.
    if market_cap is not None and market_cap < 1_000_000:
        out["market_cap"] = None
        out["market_cap_m"] = None

    shares = _to_float(out.get("shares_outstanding"))
    if shares is not None and shares < 1_000_000:
        out["shares_outstanding"] = None
        out["shares_outstanding_m"] = None

    enterprise_value = _to_float(out.get("enterprise_value"))
    if enterprise_value is not None and enterprise_value < 1_000_000:
        out["enterprise_value"] = None
        out["enterprise_value_m"] = None

    if out.get("market_cap") is not None and out.get("market_cap_m") is None:
        out["market_cap_m"] = out["market_cap"] / 1_000_000.0
    if out.get("shares_outstanding") is not None and out.get("shares_outstanding_m") is None:
        out["shares_outstanding_m"] = out["shares_outstanding"] / 1_000_000.0
    if out.get("enterprise_value") is not None and out.get("enterprise_value_m") is None:
        out["enterprise_value_m"] = out["enterprise_value"] / 1_000_000.0

    return out


def _round_price_action_value(value: Any, digits: int = 4) -> Optional[float]:
    parsed = _to_float(value)
    if parsed is None or not math.isfinite(parsed):
        return None
    return round(parsed, digits)


def _pct_change(current: Optional[float], base: Optional[float]) -> Optional[float]:
    if current is None or base is None or base <= 0:
        return None
    return round(((current / base) - 1.0) * 100.0, 2)


def _extract_weekly_price_points_from_history(
    history: Any,
    *,
    max_points: int = PRICE_ACTION_WEEKLY_POINTS,
) -> List[Dict[str, Any]]:
    """
    Convert a yfinance history DataFrame into bounded weekly close points.

    Prefer adjusted close when present; otherwise use close. Kept intentionally
    duck-typed so tests do not need pandas as a direct dependency.
    """
    if history is None:
        return []
    try:
        if getattr(history, "empty", False):
            return []
    except Exception:
        pass

    points: List[Dict[str, Any]] = []
    try:
        series = None
        for column in ("Adj Close", "Close"):
            try:
                candidate = history.get(column)
            except Exception:
                candidate = None
            if candidate is None:
                continue
            try:
                candidate = candidate.dropna()
            except Exception:
                pass
            try:
                if len(candidate) > 0:
                    series = candidate
                    break
            except Exception:
                continue
        if series is None:
            return []

        items = series.items() if hasattr(series, "items") else enumerate(series)
        for date_value, close_value in items:
            close = _round_price_action_value(close_value)
            if close is None or close <= 0:
                continue
            try:
                if hasattr(date_value, "date"):
                    date_text = date_value.date().isoformat()
                else:
                    date_text = str(date_value)[:10]
            except Exception:
                date_text = str(date_value)[:10]
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
                continue
            points.append({"date": date_text, "close": close})
    except Exception:
        return []

    return points[-max(1, int(max_points)) :]


def _max_drawdown_pct(points: List[Dict[str, Any]]) -> Optional[float]:
    peak: Optional[float] = None
    max_drawdown = 0.0
    for point in points:
        close = _to_float(point.get("close"))
        if close is None or close <= 0:
            continue
        if peak is None or close > peak:
            peak = close
            continue
        drawdown = ((close / peak) - 1.0) * 100.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return round(max_drawdown, 2) if peak is not None else None


def _annualized_volatility_pct(points: List[Dict[str, Any]], weeks: int = 13) -> Optional[float]:
    cleaned = [_to_float(point.get("close")) for point in points]
    closes = [value for value in cleaned if value is not None and value > 0]
    if len(closes) < 3:
        return None
    window = closes[-max(3, int(weeks) + 1) :]
    returns: List[float] = []
    for idx in range(1, len(window)):
        prev = window[idx - 1]
        cur = window[idx]
        if prev > 0:
            returns.append((cur / prev) - 1.0)
    if len(returns) < 2:
        return None
    return round(statistics.stdev(returns) * math.sqrt(52.0) * 100.0, 2)


def _build_price_action_packet(
    *,
    weekly_points: List[Dict[str, Any]],
    current_price: Optional[float],
    source_url: str,
    as_of_utc: Optional[str] = None,
) -> Dict[str, Any]:
    points = [
        {
            "date": str(point.get("date", "")).strip(),
            "close": _round_price_action_value(point.get("close")),
        }
        for point in list(weekly_points or [])
        if str(point.get("date", "")).strip()
        and _round_price_action_value(point.get("close")) is not None
    ]
    points = points[-PRICE_ACTION_WEEKLY_POINTS:]
    if not points:
        return {}

    latest_close = _to_float(points[-1].get("close"))
    reference_price = _to_float(current_price) or latest_close
    valid_points = [point for point in points if _to_float(point.get("close")) is not None]
    if not valid_points:
        return {}
    high_point = max(valid_points, key=lambda point: float(point.get("close") or 0.0))
    low_point = min(valid_points, key=lambda point: float(point.get("close") or 0.0))

    def _return_for_weeks(weeks: int) -> Optional[float]:
        if reference_price is None or len(points) <= weeks:
            return None
        base = _to_float(points[-1 - weeks].get("close"))
        return _pct_change(reference_price, base)

    return {
        "source": "yfinance",
        "source_url": source_url,
        "sample": "weekly_adjusted_close",
        "period_weeks": PRICE_ACTION_WEEKLY_POINTS,
        "points_available": len(points),
        "history_status": "ok" if len(points) >= PRICE_ACTION_WEEKLY_POINTS else "partial_history",
        "as_of_utc": as_of_utc or datetime.now(timezone.utc).isoformat(),
        "latest_week": {
            "date": points[-1]["date"],
            "close": _round_price_action_value(latest_close),
        },
        "current_price": _round_price_action_value(reference_price),
        "week_52_high": {
            "date": str(high_point.get("date", "")),
            "price": _round_price_action_value(high_point.get("close")),
        },
        "week_52_low": {
            "date": str(low_point.get("date", "")),
            "price": _round_price_action_value(low_point.get("close")),
        },
        "current_vs_52w_high_pct": _pct_change(reference_price, _to_float(high_point.get("close"))),
        "current_vs_52w_low_pct": _pct_change(reference_price, _to_float(low_point.get("close"))),
        "return_4w_pct": _return_for_weeks(4),
        "return_13w_pct": _return_for_weeks(13),
        "return_26w_pct": _return_for_weeks(26),
        "return_52w_pct": (
            _pct_change(reference_price, _to_float(points[0].get("close")))
            if len(points) >= 2
            else None
        ),
        "max_drawdown_52w_pct": _max_drawdown_pct(points),
        "volatility_13w_annualized_pct": _annualized_volatility_pct(points, weeks=13),
        "weekly_closes": points,
        "interpretation_note": (
            "Use price action as market-context only; do not infer causes of moves "
            "without dated source evidence. If history_status is partial_history, "
            "treat unavailable older history as a data limitation, not a flat prior."
        ),
    }


def _select_better(
    bucket: Dict[str, Tuple[float, float, str]],
    key: str,
    value: Optional[float],
    score: float,
    source_url: str,
) -> None:
    if value is None:
        return
    current = bucket.get(key)
    if current is None or score > current[0]:
        bucket[key] = (score, value, source_url)


def _source_domain_score(url: str) -> float:
    lower = (url or "").lower()
    if "marketindex.com.au" in lower:
        return 3.0
    if "asx.com.au/markets/company" in lower:
        return 2.5
    if "announcements.asx.com.au" in lower:
        return 2.0
    if "asx.com.au" in lower:
        return 1.6
    return 1.0


def _url_matches_ticker(url: str, parsed: Dict[str, str]) -> bool:
    """
    Require strong ticker match for fallback snippets to avoid near-symbol pollution
    (for example, WWI vs WWIN pages).
    """
    symbol = str(parsed.get("symbol") or "").strip().upper()
    if not symbol:
        return True

    try:
        parsed_url = urlparse(url or "")
    except Exception:
        return False

    host = (parsed_url.netloc or "").lower()
    path = (parsed_url.path or "").lower()
    symbol_lower = symbol.lower()
    symbol_upper = symbol.upper()

    if "marketindex.com.au" in host:
        # Require exact company slug path segment.
        return re.search(rf"/asx/{re.escape(symbol_lower)}(?:/|$)", path) is not None

    if "asx.com.au" in host:
        if "/markets/company/" in path:
            return re.search(
                rf"/markets/company/{re.escape(symbol_lower)}(?:/|$)",
                path,
            ) is not None
        # announcements/data-api URLs may not use a fixed path; require symbol token.
        return (
            re.search(
                rf"(?<![A-Z0-9]){re.escape(symbol_upper)}(?![A-Z0-9])",
                f"{host}{path}".upper(),
            )
            is not None
        )

    # Generic strict token match fallback.
    return (
        re.search(
            rf"(?<![A-Z0-9]){re.escape(symbol_upper)}(?![A-Z0-9])",
            (url or "").upper(),
        )
        is not None
    )


def _extract_metrics_from_text(text: str) -> Dict[str, Optional[float]]:
    payload = {
        "current_price": None,
        "market_cap": None,
        "shares_outstanding": None,
        "enterprise_value": None,
    }
    haystack = (text or "")
    if not haystack:
        return payload

    market_cap_patterns = [
        r"(?:market\s*cap(?:itali[sz]ation)?|market\s*capitalisation)\D{0,40}(?:A\$|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([KMBT]?)\b",
        r"(?:market\s*cap(?:itali[sz]ation)?|market\s*capitalisation)\D{0,40}(?:A\$|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|billion|thousand|trillion|mn|bn)\b",
    ]
    shares_patterns = [
        r"(?:shares\s*(?:on\s*issue|in\s*issue|outstanding|issued))\D{0,35}([0-9][0-9,]*(?:\.[0-9]+)?)\s*([KMBT]?)\b",
        r"(?:shares\s*(?:on\s*issue|in\s*issue|outstanding|issued))\D{0,35}([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|billion|thousand|trillion|mn|bn)\b",
    ]
    enterprise_patterns = [
        r"(?:enterprise\s*value)\D{0,40}(?:A\$|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([KMBT]?)\b",
        r"(?:enterprise\s*value)\D{0,40}(?:A\$|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|billion|thousand|trillion|mn|bn)\b",
    ]
    price_patterns = [
        r"(?:last\s*price|share\s*price|price\s*/\s*today'?s\s*change|close(?:d)?\s*at)\D{0,20}(?:A\$|\$)?\s*([0-9]+(?:\.[0-9]+)?)\s*(c|¢)?",
        r"(?:@|at)\s*([0-9]+(?:\.[0-9]+)?)\s*(c|¢)\s*per\s*share",
        r"(?:A\$|\$)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:per\s*share)?",
    ]

    for pattern in market_cap_patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            payload["market_cap"] = _parse_numeric_with_suffix(match.group(1), match.group(2))
            break

    for pattern in shares_patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            payload["shares_outstanding"] = _parse_numeric_with_suffix(match.group(1), match.group(2))
            break

    for pattern in enterprise_patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            payload["enterprise_value"] = _parse_numeric_with_suffix(match.group(1), match.group(2))
            break

    for pattern in price_patterns:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if match:
            cents = match.lastindex and match.lastindex >= 2 and (match.group(2) or "").strip()
            parsed = _parse_numeric_with_suffix(match.group(1), "")
            if parsed is not None:
                payload["current_price"] = (parsed / 100.0) if cents else parsed
                break

    return payload


async def _gather_yfinance_facts(
    parsed: Dict[str, str],
    timeout: float,
    commodity_profile: Optional[str] = None,
) -> Dict[str, Any]:
    yahoo_symbol = parsed.get("yahoo_symbol") or parsed.get("symbol")
    if not yahoo_symbol:
        return {
            "normalized_facts": {},
            "source_urls": [],
            "notes": ["No symbol for yfinance prepass."],
            "error": "",
        }

    quote_page_url = f"https://finance.yahoo.com/quote/{yahoo_symbol}"

    async def _run_thread_call(
        label: str,
        fn: Any,
        call_timeout: float,
        notes: List[str],
    ) -> Any:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(fn),
                timeout=max(1.0, float(call_timeout)),
            )
        except Exception as exc:
            notes.append(f"yfinance {label} failed: {type(exc).__name__}: {exc}")
            return None

    async def _fetch_once(call_timeout: float) -> Dict[str, Any]:
        import yfinance as yf

        notes: List[str] = []
        ticker = yf.Ticker(yahoo_symbol)

        fast_info = await _run_thread_call(
            "fast_info",
            lambda: dict(ticker.fast_info or {}),
            min(call_timeout, 8.0),
            notes,
        )
        if not isinstance(fast_info, dict):
            fast_info = {}

        history_close: Optional[float] = None
        history = await _run_thread_call(
            "history",
            lambda: ticker.history(period="5d", interval="1d", auto_adjust=False),
            min(call_timeout, 8.0),
            notes,
        )
        try:
            if history is not None:
                closes = history.get("Close")
                if closes is not None:
                    closes = closes.dropna()
                    if len(closes) > 0:
                        history_close = _to_float(closes.iloc[-1])
        except Exception as exc:
            notes.append(f"yfinance history parse failed: {type(exc).__name__}: {exc}")

        weekly_points: List[Dict[str, Any]] = []
        weekly_history = await _run_thread_call(
            "weekly_history",
            lambda: ticker.history(period="1y", interval="1wk", auto_adjust=False),
            min(call_timeout, 10.0),
            notes,
        )
        try:
            weekly_points = _extract_weekly_price_points_from_history(
                weekly_history,
                max_points=PRICE_ACTION_WEEKLY_POINTS,
            )
        except Exception as exc:
            notes.append(f"yfinance weekly history parse failed: {type(exc).__name__}: {exc}")

        # Avoid the heavy .info call unless core fields are still missing.
        has_fast_market_cap = _pick_numeric(fast_info, "marketCap") is not None
        has_fast_shares = _pick_numeric(fast_info, "shares", "sharesOutstanding") is not None
        has_fast_price = _pick_numeric(fast_info, "lastPrice", "regularMarketPrice", "currentPrice") is not None
        need_info = not (has_fast_market_cap and has_fast_shares and (has_fast_price or history_close is not None))

        info: Dict[str, Any] = {}
        if need_info:
            info_raw = await _run_thread_call(
                "info",
                lambda: dict(ticker.info or {}),
                min(call_timeout, 12.0),
                notes,
            )
            if isinstance(info_raw, dict):
                info = info_raw

        async def _fetch_last_close(symbol: str, label: str) -> Optional[float]:
            history = await _run_thread_call(
                label,
                lambda: yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False),
                min(call_timeout, 8.0),
                notes,
            )
            try:
                if history is None:
                    return None
                closes = history.get("Close")
                if closes is None:
                    return None
                closes = closes.dropna()
                if len(closes) <= 0:
                    return None
                return _to_float(closes.iloc[-1])
            except Exception as exc:
                notes.append(f"yfinance {label} parse failed: {type(exc).__name__}: {exc}")
                return None

        commodity_values: Dict[str, Optional[float]] = {}
        audusd_rate: Optional[float] = None

        if commodity_profile:
            audusd_rate = await _fetch_last_close("AUDUSD=X", "audusd_history")

        def _set_usd_and_aud(usd_key: str, aud_key: str, usd_value: Optional[float]) -> None:
            commodity_values[usd_key] = usd_value
            if usd_value is not None and audusd_rate is not None and audusd_rate > 0:
                commodity_values[aud_key] = usd_value / audusd_rate
            else:
                commodity_values[aud_key] = None

        if commodity_profile == "gold":
            gold_usd_oz = await _fetch_last_close("GC=F", "gold_history")
            _set_usd_and_aud("gold_price_usd_oz", "gold_price_aud_oz", gold_usd_oz)
        elif commodity_profile == "copper":
            copper_usd_lb = await _fetch_last_close("HG=F", "copper_history")
            _set_usd_and_aud("copper_price_usd_lb", "copper_price_aud_lb", copper_usd_lb)
        elif commodity_profile == "lithium":
            lithium_usd_kg: Optional[float] = None
            for symbol in ("LIT=F", "LTH=F"):
                lithium_usd_kg = await _fetch_last_close(symbol, f"lithium_history_{symbol}")
                if lithium_usd_kg is not None:
                    break
            if lithium_usd_kg is None:
                notes.append("yfinance lithium commodity proxy unavailable for configured symbols.")
            _set_usd_and_aud("lithium_price_usd_kg", "lithium_price_aud_kg", lithium_usd_kg)
        elif commodity_profile == "silver":
            silver_usd_oz = await _fetch_last_close("SI=F", "silver_history")
            _set_usd_and_aud("silver_price_usd_oz", "silver_price_aud_oz", silver_usd_oz)
        elif commodity_profile == "uranium":
            uranium_usd_lb: Optional[float] = None
            for symbol in ("UX1=F", "UX2=F", "U=F"):
                uranium_usd_lb = await _fetch_last_close(symbol, f"uranium_history_{symbol}")
                if uranium_usd_lb is not None:
                    break
            if uranium_usd_lb is None:
                notes.append("yfinance uranium commodity feed unavailable for configured symbols.")
            _set_usd_and_aud("uranium_price_usd_lb", "uranium_price_aud_lb", uranium_usd_lb)
        elif commodity_profile == "oil_gas":
            brent_usd = await _fetch_last_close("BZ=F", "brent_history")
            wti_usd = await _fetch_last_close("CL=F", "wti_history")
            henry_hub_usd = await _fetch_last_close("NG=F", "henry_hub_history")
            _set_usd_and_aud("brent_price_usd_bbl", "brent_price_aud_bbl", brent_usd)
            _set_usd_and_aud("wti_price_usd_bbl", "wti_price_aud_bbl", wti_usd)
            _set_usd_and_aud(
                "henry_hub_price_usd_mmbtu",
                "henry_hub_price_aud_mmbtu",
                henry_hub_usd,
            )

        return {
            "fast_info": fast_info,
            "info": info,
            "history_close": history_close,
            "weekly_price_points": weekly_points,
            "commodity_profile": commodity_profile,
            "commodity_values": commodity_values,
            "notes": notes,
        }

    def _is_transient_note(note: str) -> bool:
        text = (note or "").lower()
        transient_tokens = (
            "timeout",
            "timed out",
            "readtimeout",
            "connecttimeout",
            "connectionerror",
            "temporar",
            "429",
            "503",
            "504",
        )
        return any(token in text for token in transient_tokens)

    fetch_error = ""
    recovered_error = ""
    payload: Dict[str, Any] = {}
    last_notes: List[str] = []
    has_yfinance_payload_data = False
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            payload = await _fetch_once(timeout)
        except Exception as exc:
            payload = {}
            last_notes = [f"yfinance prepass failed: {type(exc).__name__}: {exc}"]
        else:
            last_notes = payload.get("notes") or []

        fast_info_attempt = payload.get("fast_info") or {}
        info_attempt = payload.get("info") or {}
        history_close_attempt = _to_float(payload.get("history_close"))
        has_any_payload_data = bool(
            fast_info_attempt
            or info_attempt
            or history_close_attempt is not None
        )
        if has_any_payload_data:
            has_yfinance_payload_data = True
            if recovered_error:
                last_notes = list(last_notes) + [f"yfinance transient retry recovered after: {recovered_error}"]
            fetch_error = ""
            break

        fetch_error = "; ".join(last_notes[:2]).strip() or "No yfinance data returned"
        if attempt < max_attempts and any(_is_transient_note(note) for note in last_notes):
            recovered_error = fetch_error
            await asyncio.sleep(0.8 * attempt)
            continue
        break

    if fetch_error and not has_yfinance_payload_data:
        return {
            "normalized_facts": {},
            "source_urls": [quote_page_url],
            "notes": [f"yfinance prepass failed: {fetch_error}"],
            "error": fetch_error,
        }

    fast_info = payload.get("fast_info") or {}
    info = payload.get("info") or {}
    history_close = _to_float(payload.get("history_close"))
    commodity_values_raw = payload.get("commodity_values") or {}
    weekly_price_points = list(payload.get("weekly_price_points") or [])
    commodity_values = {
        key: _to_float(value)
        for key, value in commodity_values_raw.items()
        if key in COMMODITY_FIELDS
    }
    last_notes = payload.get("notes") or []

    current_price = (
        _pick_numeric(fast_info, "lastPrice", "regularMarketPrice", "currentPrice")
        or _pick_numeric(info, "currentPrice", "regularMarketPrice", "previousClose")
        or history_close
    )
    market_cap = _pick_numeric(fast_info, "marketCap") or _pick_numeric(info, "marketCap")
    shares_outstanding = (
        _pick_numeric(fast_info, "shares", "sharesOutstanding")
        or _pick_numeric(info, "sharesOutstanding", "impliedSharesOutstanding")
    )
    enterprise_value = _pick_numeric(fast_info, "enterpriseValue") or _pick_numeric(info, "enterpriseValue")
    currency = _pick_string(fast_info, "currency") or _pick_string(info, "currency")

    normalized_facts = _normalize_facts(
        current_price=current_price,
        market_cap=market_cap,
        shares_outstanding=shares_outstanding,
        enterprise_value=enterprise_value,
        currency=currency or ("AUD" if parsed.get("exchange") == "ASX" else ""),
        commodity_profile=commodity_profile,
        commodity_values=commodity_values,
    )
    normalized_facts = _sanitize_normalized_facts(normalized_facts)
    price_action = _build_price_action_packet(
        weekly_points=weekly_price_points,
        current_price=normalized_facts.get("current_price"),
        source_url=quote_page_url,
    )

    notes = list(last_notes)
    if fetch_error:
        notes.append(f"yfinance transient retry recovered after: {fetch_error}")

    return {
        "normalized_facts": normalized_facts,
        "price_action": price_action,
        "source_urls": [quote_page_url],
        "notes": notes,
        "error": "",
    }


async def _tavily_search(query: str, timeout: float, max_results: int = 4) -> Dict[str, Any]:
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured", "results": []}

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json() or {}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "results": []}


async def _gather_asx_marketindex_fallback(
    parsed: Dict[str, str],
    timeout: float,
) -> Dict[str, Any]:
    symbol = parsed.get("symbol", "")
    exchange = parsed.get("exchange", "")
    if not symbol:
        return {"normalized_facts": {}, "source_urls": [], "notes": ["No symbol for fallback queries."]}

    queries = [
        f"site:marketindex.com.au ASX:{symbol} market cap shares on issue last price",
        f"site:asx.com.au/markets/company/{symbol} key statistics market cap share price",
        f"site:announcements.asx.com.au ASX:{symbol} investor presentation market capitalisation shares",
    ]
    if exchange and exchange != "ASX":
        queries = [
            f"site:asx.com.au {symbol} market cap shares",
            f"site:marketindex.com.au {symbol} market cap shares",
        ]

    best_values: Dict[str, Tuple[float, float, str]] = {}
    source_urls: List[str] = []
    notes: List[str] = []

    for query in queries:
        payload = await _tavily_search(query=query, timeout=timeout, max_results=4)
        if payload.get("error"):
            notes.append(f"Tavily fallback query failed: {query} ({payload['error']})")
            continue

        for result in payload.get("results", []) or []:
            url = str(result.get("url") or "").strip()
            title = str(result.get("title") or "")
            content = str(result.get("content") or "")
            if not url:
                continue
            if not _url_matches_ticker(url, parsed):
                notes.append(f"Skipped fallback URL due ticker mismatch: {url}")
                continue
            if url not in source_urls:
                source_urls.append(url)

            text = f"{title}\n{content}"
            extracted = _extract_metrics_from_text(text)
            base_score = _source_domain_score(url)

            for metric_key in ("current_price", "market_cap", "shares_outstanding", "enterprise_value"):
                value = extracted.get(metric_key)
                if value is None:
                    continue
                confidence = base_score + 0.2
                if metric_key in title.lower():
                    confidence += 0.1
                _select_better(best_values, metric_key, value, confidence, url)

    normalized_facts = _normalize_facts(
        current_price=best_values.get("current_price", (0.0, None, ""))[1],
        market_cap=best_values.get("market_cap", (0.0, None, ""))[1],
        shares_outstanding=best_values.get("shares_outstanding", (0.0, None, ""))[1],
        enterprise_value=best_values.get("enterprise_value", (0.0, None, ""))[1],
        currency="AUD" if exchange == "ASX" else "",
    )
    normalized_facts = _sanitize_normalized_facts(normalized_facts)

    return {
        "normalized_facts": normalized_facts,
        "source_urls": source_urls,
        "notes": notes,
    }


async def gather_market_facts_prepass(
    ticker: Optional[str],
    company_name: Optional[str] = None,
    exchange: Optional[str] = None,
    template_id: Optional[str] = None,
    company_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch deterministic market baseline fields using a provider chain.

    Provider order:
      1) yfinance (Yahoo-backed, library mediated)
      2) Tavily + exchange-specific fallback snippets
    """
    resolved_ticker = str(ticker or "").strip()
    if not resolved_ticker:
        return {
            "status": "skipped",
            "reason": "No ticker provided for market facts prepass.",
            "normalized_facts": {},
            "source_urls": [],
            "as_of_utc": datetime.now(timezone.utc).isoformat(),
        }

    parsed = _parse_ticker(resolved_ticker)
    if exchange and not parsed["exchange"]:
        parsed["exchange"] = str(exchange).strip().upper()
        suffix = EXCHANGE_TO_YAHOO_SUFFIX.get(parsed["exchange"], "")
        parsed["yahoo_symbol"] = f"{parsed['symbol']}{suffix}" if parsed["symbol"] else parsed["symbol"]
        if parsed["exchange"] and parsed["symbol"]:
            parsed["normalized_ticker"] = f"{parsed['exchange']}:{parsed['symbol']}"

    yahoo_symbol = parsed["yahoo_symbol"] or parsed["symbol"]
    if not yahoo_symbol:
        return {
            "status": "skipped",
            "reason": "Ticker parsing failed for market facts prepass.",
            "normalized_facts": {},
            "source_urls": [],
            "as_of_utc": datetime.now(timezone.utc).isoformat(),
        }

    quote_page_url = f"https://finance.yahoo.com/quote/{yahoo_symbol}"
    as_of = datetime.now(timezone.utc).isoformat()

    timeout = max(5.0, float(MARKET_FACTS_TIMEOUT_SECONDS))
    template_key = str(template_id or "").strip().lower()
    company_key = str(company_type or "").strip().lower()
    core_asset_classification: Dict[str, Any] = {}
    if _requires_resource_exposure_resolution(template_key, company_key):
        core_asset_classification = await _fetch_critical_minerals_core_asset_packet_xai(
            ticker=parsed["normalized_ticker"] or resolved_ticker,
            company_name=company_name or "",
            exchange=parsed["exchange"] or exchange or "",
            timeout=timeout,
        )
        commodity_profile = (
            str(core_asset_classification.get("resolved_profile") or "").strip()
            if core_asset_classification.get("success")
            else ""
        )
        if not commodity_profile:
            commodity_profile = None
            core_asset_classification["fallback_profile"] = None
            core_asset_classification["fallback_reason"] = "no_commodity_profile_without_successful_grok_resource_exposure_packet"
        core_asset_classification["scope"] = "ambiguous_resource_exposure"
    else:
        commodity_profile = _resolve_commodity_profile(
            template_id,
            company_type,
            company_name=company_name,
            ticker=resolved_ticker,
        )
    yfinance_error = ""
    yfinance_notes: List[str] = []
    normalized_facts = _normalize_facts(
        current_price=None,
        market_cap=None,
        shares_outstanding=None,
        enterprise_value=None,
        currency="AUD" if parsed.get("exchange") == "ASX" else "",
        commodity_profile=commodity_profile,
        commodity_values={},
    )
    source_urls: List[str] = [quote_page_url]
    price_action: Dict[str, Any] = {}
    grok_price_used = False
    for url in core_asset_classification.get("source_urls", []) or []:
        if url and url not in source_urls:
            source_urls.append(url)

    yfinance_result = await _gather_yfinance_facts(
        parsed,
        timeout=timeout,
        commodity_profile=commodity_profile,
    )
    yfinance_facts = yfinance_result.get("normalized_facts", {}) or {}
    if isinstance(yfinance_result.get("price_action"), dict):
        price_action = dict(yfinance_result.get("price_action") or {})
    yfinance_sources = yfinance_result.get("source_urls", []) or []
    yfinance_notes = yfinance_result.get("notes", []) or []
    yfinance_error = str(yfinance_result.get("error") or "").strip()
    for key, value in yfinance_facts.items():
        if normalized_facts.get(key) is None and value is not None:
            normalized_facts[key] = value
    for key, value in (core_asset_classification.get("price_values", {}) or {}).items():
        if key in COMMODITY_FIELDS and normalized_facts.get(key) is None and value is not None:
            normalized_facts[key] = value
            grok_price_used = True
    normalized_facts = _sanitize_normalized_facts(normalized_facts)
    for url in yfinance_sources:
        if url and url not in source_urls:
            source_urls.append(url)

    available_fields = _available_field_count(normalized_facts)

    # Fallback path for ASX/MarketIndex oriented coverage when Yahoo is unavailable or sparse.
    fallback_used = False
    fallback_notes: List[str] = []
    if available_fields < 3:
        fallback = await _gather_asx_marketindex_fallback(parsed, timeout=timeout)
        fallback_facts = fallback.get("normalized_facts", {}) or {}
        fallback_sources = fallback.get("source_urls", []) or []
        fallback_notes = fallback.get("notes", []) or []
        fallback_has_core = (
            fallback_facts.get("market_cap") is not None
            and fallback_facts.get("shares_outstanding") is not None
        )
        if fallback_has_core:
            for key, value in fallback_facts.items():
                if normalized_facts.get(key) is None and value is not None:
                    normalized_facts[key] = value
                    fallback_used = True
        elif any(
            fallback_facts.get(key) is not None
            for key in ("current_price", "market_cap", "shares_outstanding", "enterprise_value")
        ):
            fallback_notes.append(
                "Fallback numeric facts rejected: missing core fields "
                "(market_cap and shares_outstanding)."
            )

        normalized_facts = _sanitize_normalized_facts(normalized_facts)

        for url in fallback_sources:
            if url and url not in source_urls:
                source_urls.append(url)

        available_fields = _available_field_count(normalized_facts)

    commodity_notes: List[str] = []
    commodity_key_pairs = _commodity_key_pairs_for_profile(commodity_profile)
    commodity_usd_keys = [usd_key for usd_key, _aud_key in commodity_key_pairs if usd_key]
    if commodity_usd_keys and any(normalized_facts.get(key) is None for key in commodity_usd_keys):
        commodity_fallback = await _gather_commodity_price_fallback(commodity_profile, timeout=timeout)
        commodity_values = commodity_fallback.get("commodity_values", {}) or {}
        for key, value in commodity_values.items():
            if key in COMMODITY_FIELDS and normalized_facts.get(key) is None and value is not None:
                normalized_facts[key] = value
        normalized_facts = _sanitize_normalized_facts(normalized_facts)
        commodity_notes = commodity_fallback.get("notes", []) or []
        for url in commodity_fallback.get("source_urls", []) or []:
            if url and url not in source_urls:
                source_urls.append(url)

    if available_fields >= 3:
        status = "ok" if not fallback_used else "fallback_ok"
    elif available_fields > 0:
        status = "partial" if not fallback_used else "fallback_partial"
    else:
        status = "error" if (yfinance_error or fallback_notes) else "empty"

    reason_parts: List[str] = []

    def _append_unique(items: List[str]) -> None:
        for item in items:
            clean = str(item or "").strip()
            if not clean:
                continue
            if clean not in reason_parts:
                reason_parts.append(clean)

    if yfinance_error:
        _append_unique([f"yfinance prepass failed: {yfinance_error}"])
    if core_asset_classification.get("success"):
        confidence = core_asset_classification.get("confidence")
        profile = core_asset_classification.get("resolved_profile")
        if profile:
            confidence_text = f" confidence={confidence:.2f}" if isinstance(confidence, (float, int)) else ""
            _append_unique([f"Grok commodity-exposure resolver selected {profile}.{confidence_text}"])
    elif core_asset_classification.get("attempted"):
        err = str(core_asset_classification.get("error") or "unknown").strip()
        fallback_profile = str(core_asset_classification.get("fallback_profile") or "").strip()
        suffix = f"; fallback_profile={fallback_profile}" if fallback_profile else ""
        _append_unique([f"Grok commodity-exposure resolver unavailable: {err}{suffix}"])
    if yfinance_notes:
        _append_unique(yfinance_notes[:2])
    if fallback_used:
        _append_unique(["Applied ASX/MarketIndex Tavily fallback."])
    if fallback_notes:
        _append_unique(fallback_notes[:2])
    if grok_price_used:
        _append_unique(["Applied Grok commodity benchmark prices."])
    if commodity_notes:
        _append_unique(commodity_notes[:2])
    reason = " | ".join(reason_parts).strip()

    return {
        "status": status,
        "reason": reason,
        "ticker": parsed["normalized_ticker"] or resolved_ticker,
        "exchange": parsed["exchange"],
        "symbol": parsed["symbol"],
        "yahoo_symbol": yahoo_symbol,
        "company_name": company_name or "",
        "as_of_utc": as_of,
        "source_urls": source_urls,
        "normalized_facts": normalized_facts,
        "price_action": price_action,
        "core_asset_classification": core_asset_classification,
        "providers_attempted": (
            ["xai_resource_exposure_resolver", "yfinance", "tavily_fallback"]
            if core_asset_classification
            else ["yfinance", "tavily_fallback"]
        ),
    }


def minimal_market_facts_payload(
    market_facts: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Return the minimal market-facts payload expected by Stage 1 prompts.

    Shape:
    {
      "normalized_facts": {
        current_price,
        market_cap,
        market_cap_m,
        shares_outstanding,
        shares_outstanding_m,
        enterprise_value,
        enterprise_value_m,
        currency,
        commodity_profile,
        commodity price fields (template-conditional)
      },
      "price_action": {
        52-week weekly adjusted closes plus compact momentum/drawdown features
      }
    }
    """
    normalized = (market_facts or {}).get("normalized_facts", {}) or {}
    price_action = (market_facts or {}).get("price_action", {}) or {}
    minimal: Dict[str, Any] = {
        "current_price": normalized.get("current_price"),
        "market_cap": normalized.get("market_cap"),
        "market_cap_m": normalized.get("market_cap_m"),
        "shares_outstanding": normalized.get("shares_outstanding"),
        "shares_outstanding_m": normalized.get("shares_outstanding_m"),
        "enterprise_value": normalized.get("enterprise_value"),
        "enterprise_value_m": normalized.get("enterprise_value_m"),
        "currency": normalized.get("currency"),
        "commodity_profile": normalized.get("commodity_profile"),
        "core_commodity_focus": normalized.get("core_commodity_focus"),
    }
    for key in COMMODITY_FIELDS:
        value = normalized.get(key)
        if value is not None:
            minimal[key] = value
    payload: Dict[str, Any] = {"normalized_facts": minimal}
    if isinstance(price_action, dict) and price_action.get("weekly_closes"):
        payload["price_action"] = price_action
    return payload


def format_market_facts_query_prefix(
    market_facts: Optional[Dict[str, Any]],
) -> str:
    """Render minimal market facts block for prepending directly to the query."""
    payload = minimal_market_facts_payload(market_facts)
    normalized = payload.get("normalized_facts", {}) or {}
    has_core_market_facts = (
        normalized.get("market_cap") is not None
        and normalized.get("shares_outstanding") is not None
    )
    has_commodity_prices = any(normalized.get(key) is not None for key in COMMODITY_FIELDS)
    has_price_action = bool((payload.get("price_action") or {}).get("weekly_closes"))
    if not has_core_market_facts and not has_commodity_prices and not has_price_action:
        return ""
    return json.dumps(payload, indent=2)


def prepend_market_facts_to_query(
    query: str,
    market_facts: Optional[Dict[str, Any]],
) -> str:
    """
    Prefix minimal market facts block before the main query/template text.
    """
    core_query = (query or "").strip()
    prefix = format_market_facts_query_prefix(market_facts)
    if not prefix:
        return core_query
    if not core_query:
        return prefix
    return f"{prefix}\n\n{core_query}"
