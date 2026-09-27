from copy import deepcopy

from backend.portfolio_tasks import fact_review_batches


def test_review_batches_group_sources_without_losing_claims_or_source_context():
    sources = [{"id": name, "excerpt": name * 5000} for name in ("a", "b")]
    facts = [{"id": str(i), "source_ids": ["a" if i % 2 == 0 else "b"], "source_excerpt": "full claim"}
             for i in range(32)]
    packet = {"sources": sources, "as_of": "2026-09-23"}
    before = deepcopy((facts, packet))
    batches = fact_review_batches(facts, packet)
    assert len(batches) == 2
    assert [len(batch["source_packet"]["sources"]) for batch in batches] == [1, 1]
    assert sorted(row["id"] for batch in batches for row in batch["facts"]) == sorted(row["id"] for row in facts)
    for batch in batches:
        assert batch["source_packet"]["sources"][0] in sources
    assert (facts, packet) == before


def test_large_common_source_is_not_repeated_in_a_call_per_fact():
    source = {"id": "s", "excerpt": "complete table with full column headers " * 3000}
    facts = [{"id": str(i), "source_ids": ["s"]} for i in range(12)]
    batches = fact_review_batches(facts, {"sources": [source]})
    assert len(batches) == 1
    assert batches[0]["source_packet"]["sources"] == [source]
    assert batches[0]["facts"] == facts


def test_large_unrelated_sources_and_large_claims_are_split_not_clipped():
    packet = {"sources": [{"id": str(i), "excerpt": "text " * 14000} for i in range(4)]}
    facts = [{"id": str(i), "source_ids": [str(i)], "source_excerpt": "quote " * 7000} for i in range(4)]
    batches = fact_review_batches(facts, packet)
    assert len(batches) == 4
    assert [row for batch in batches for row in batch["facts"]] == facts
    assert [row for batch in batches for row in batch["source_packet"]["sources"]] == packet["sources"]


def test_multisource_claim_keeps_all_sources_in_one_check():
    packet = {"sources": [{"id": str(i), "excerpt": "source text"} for i in range(3)]}
    facts = [{"id": "a", "source_ids": ["0", "2"]}, {"id": "b", "source_ids": ["2", "0"]}]
    batches = fact_review_batches(facts, packet)
    assert len(batches) == 1
    assert batches[0]["facts"] == facts
    assert {source["id"] for source in batches[0]["source_packet"]["sources"]} == {"0", "2"}


def test_uncited_different_forecast_remains_discoverable_to_reviewers():
    from backend.portfolio_tasks import evidence_for_review
    facts = [{"id": name, "kind": "forecast", "metric": metric, "benchmark": "Energy producers", "unit": "percent",
        "target_period": "2027", "comparison_groups": ["energy"], "source_ids": ["s"]}
        for name, metric in [("direct", "Net margin"), ("different", "Capex growth")]]
    brief = {"facts": facts, "source_packet": {"sources": [{"id": "s", "excerpt": "source text"}]}}
    reviewed = evidence_for_review(brief, {"fact_ids": ["direct"]})
    assert [row["id"] for row in reviewed["facts"]] == ["direct"]
    catalog = reviewed["other_observations"]
    assert "different" in [row[catalog["columns"].index("id")] for row in catalog["rows"]]
    reviewed = evidence_for_review(brief, {"fact_ids": ["direct", "different"]})
    assert {row["id"] for row in reviewed["facts"]} == {"direct", "different"}
