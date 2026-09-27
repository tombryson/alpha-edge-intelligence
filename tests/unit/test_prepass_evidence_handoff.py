import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.jobs.prepass import _build_stage1_prepass_source_rows_from_bundle
from backend.council import stage1
from backend.prepass_cache import load_cached_prepass_rows, save_cached_prepass_rows


def build(tmp_path, docs):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"docs": docs}))
    return _build_stage1_prepass_source_rows_from_bundle(path)


def test_preserves_late_facts_conditions_and_all_list_items(tmp_path):
    facts = [f"2026-06-{i:02}: Drill hole {i} needs further validation." for i in range(1, 31)]
    rows, meta = build(tmp_path, [{
        "title": "Quarterly report", "url": "https://example.com/q.pdf",
        "published_at": "2026-07-31", "key_points": facts,
        "capital_structure": ["Cash A$19.514m at 30 June; operating outflow A$6.289m."],
        "risks_headwinds": [f"Condition {i} remains outstanding." for i in range(12)],
        "timeline_milestones": [{"milestone": "Restart", "target_window": "September 2026",
                                  "condition": "Subject to acquisition completion and funding"}],
        "catalysts_next_12m": ["Study results anticipated H1 2027, not product approval."],
    }])
    text = rows[0]["excerpt"]
    assert len(text) > 1600
    assert all(fact in text for fact in facts)
    for fact in ("A$19.514m", "A$6.289m", "Condition 11", "September 2026",
                 "Subject to acquisition completion and funding", "H1 2027, not product approval."):
        assert fact in text
    assert not text.endswith("...")
    assert rows[0]["source_id"] == "S1"
    assert rows[0]["url"] == "https://example.com/q.pdf"
    assert meta["handoff_version"] == "complete_facts_v2"


def test_deduplicates_exact_statements_without_merging_changed_terms(tmp_path):
    fact = "Cash was A$19.514m at 30 June."
    rows, meta = build(tmp_path, [{
        "one_line": fact,
        "key_facts_paragraph": fact + " Funding is conditional on approval.",
        "key_points": [fact, "Cash was A$19.514m at 31 March.", "Cash was A$19.515m at 30 June."],
        "risks_headwinds": ["Funding is not committed."],
    }])
    text = rows[0]["excerpt"]
    assert text.count(fact) == 1
    assert meta["duplicate_statements_removed"] == 2
    assert "A$19.514m at 31 March" in text
    assert "A$19.515m at 30 June" in text
    assert "Funding is conditional on approval." in text
    assert "Funding is not committed." in text


def test_normalizes_strings_and_nested_objects_without_losing_values(tmp_path):
    rows, _ = build(tmp_path, [{
        "key_points": "A complete fact, not a list of characters.",
        "capital_structure": {"cash": ["A$8.712m at 30 June"], "debt": {"drawn": 0,
            "conditions": ["Second A$10m optional, requires FDA clearance"]}},
        "timeline_milestones": [{"milestone": "Trial", "target_window": "H1 2027",
                                  "status": "Research only", "source_snippet": "Approval not obtained"}],
    }])
    for value in ("A complete fact", "A$8.712m", "drawn: 0", "requires FDA clearance",
                  "H1 2027", "Research only", "Approval not obtained"):
        assert value in rows[0]["excerpt"]


def test_does_not_merge_different_sources(tmp_path):
    rows, _ = build(tmp_path, [
        {"url": "https://example.com/a", "published_at": "2026-07-01", "one_line": "Funding remains conditional."},
        {"url": "https://example.com/b", "published_at": "2026-08-01", "one_line": "Funding remains conditional."},
    ])
    assert len(rows) == 2
    assert rows[0]["url"] != rows[1]["url"]


def test_real_stage1_prompt_keeps_packet_once_despite_old_compression_budget(tmp_path):
    rows, _ = build(tmp_path, [{"url": "https://example.com/q.pdf", "published_at": "2026-07-31",
        "key_points": [f"Observation {i}: work remains subject to permit approval." for i in range(250)],
        "risks_headwinds": ["TAIL CONDITION: potential US$18m, not awarded or paid."]}])
    captured = []

    class PromptCaptured(Exception):
        pass

    def capture(prompt, ledger):
        captured.append(prompt)
        raise PromptCaptured

    with patch.object(stage1, "_classify_cashflow_schema_with_agent", new=AsyncMock(return_value={})), \
         patch.object(stage1, "_validate_stage1_prompt_mandatory_fact_coverage", side_effect=capture), \
         patch.object(stage1, "PERPLEXITY_STAGE1_SECOND_PASS_PROMPT_COMPRESSION_ENABLED", True), \
         patch.object(stage1, "PERPLEXITY_STAGE1_SECOND_PASS_PROMPT_TARGET_CHARS", 10000), \
         patch.object(stage1, "PERPLEXITY_STAGE1_SECOND_PASS_MAX_CHARS_PER_SOURCE", 300):
        try:
            asyncio.run(stage1._run_stage1_second_pass_analysis(
                model="test", user_query="Analyse", research_brief="", run={},
                prepass_source_rows=rows, supplementary_macro_news_override={},
            ))
        except PromptCaptured:
            pass
    assert len(captured) == 1
    prompt = captured[0]
    assert len(prompt) > 10000
    assert prompt.count("TAIL CONDITION: potential US$18m, not awarded or paid.") == 1
    assert "Observation 249" in prompt
    assert "AUTHORITATIVE_SOURCE_EVIDENCE_JSON" in prompt
    assert "SOURCE_KEY_POINTS_JSON" not in prompt
    assert "FACT_DIGEST_V2_JSON" not in prompt
    assert "EVIDENCE_APPENDIX" not in prompt
    assert "https://example.com/q.pdf" in prompt


def test_old_clipped_cache_is_not_treated_as_complete(tmp_path):
    saved = save_cached_prepass_rows(cache_root=tmp_path, ticker="ASX:EIQ",
        source_rows=[{"source_id": "S1", "excerpt": "Clipped..."}])
    path = Path(saved["cache_path"])
    payload = json.loads(path.read_text())
    payload["prepass_version"] = "stage1_prepass_rows_v1"
    path.write_text(json.dumps(payload))
    rows, meta = load_cached_prepass_rows(cache_root=tmp_path, ticker="ASX:EIQ")
    assert not rows
    assert meta["cache_reason"] == "prepass_version_changed"
