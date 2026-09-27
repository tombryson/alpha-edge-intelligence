from backend.portfolio_tasks import decision_source_check_plan
from backend.portfolio_runtime import workload_summary


def test_decision_checks_retain_opposition_and_corrections_not_whole_debate():
    facts = [
        {"id": "chosen", "kind": "forecast", "metric": "Supply balance", "benchmark": "Copper", "unit": "tonnes", "target_period": "2027", "comparison_groups": ["copper-balance"]},
        {"id": "opposing", "kind": "forecast", "metric": "Supply balance", "benchmark": "Copper", "unit": "tonnes", "target_period": "2027", "comparison_groups": ["copper-balance"]},
        {"id": "correction", "supersedes": "opposing"},
        {"id": "challenged"}, {"id": "peripheral"}, {"id": "unresolved"},
    ]
    proposal = {"asset_class_targets": [{"asset_class": "Copper", "fact_ids": ["chosen"]}],
                "review_dispositions": [{"finding_id": "open", "status": "unresolved"}]}
    reviews = [{"findings": [
        {"id": "bad-period", "asset_class": "Copper", "kind": "factual_correction", "fact_ids": ["chosen", "challenged"]},
        {"id": "general", "asset_class": "Copper", "kind": "research_gap", "fact_ids": ["peripheral"]},
        {"id": "open", "asset_class": "Other", "kind": "investment_disagreement", "fact_ids": ["unresolved"]},
    ]}]
    plan = decision_source_check_plan({"facts": facts}, proposal, reviews)
    assert set(plan["fact_ids"]) == {"chosen", "opposing", "correction", "challenged", "unresolved"}
    assert len(facts) == 6
    assert plan["selection_reasons"]["opposing"] == ["same_measurement_or_opposing_case"]


def test_topic_and_measurement_series_do_not_expand_to_every_period():
    facts = [{"id": str(i), "kind": "observed_macro", "metric": "yield", "benchmark": "ten year",
              "unit": "percent", "reference_period": f"2026-09-{i:02}", "comparison_groups": ["sovereign debt"]}
             for i in range(1, 20)]
    facts.append({**facts[0], "id": "opposing-print", "value": 9})
    plan = decision_source_check_plan({"facts": facts}, {"fact_ids": ["1"]})
    assert set(plan["fact_ids"]) == {"1", "opposing-print"}


def test_check_plan_preserves_missing_references_and_resolves_aliases():
    plan = decision_source_check_plan({"facts": [{"id": "new"}], "fact_aliases": {"old": "new"}},
                                      {"fact_ids": ["old", "missing"]})
    assert plan["fact_ids"] == ["new"]
    assert plan["missing_fact_ids"] == ["missing"]


def test_shared_forecast_topic_cannot_pull_unrelated_measurements_into_checks():
    from copy import deepcopy
    selected = {"id": "selected", "kind": "forecast", "metric": "Net margin", "benchmark": "Energy producers",
        "unit": "percent", "currency": "USD", "target_period": "2027", "comparison_groups": ["market-outlook"],
        "applicability": {"subject": "Oil producers", "geography": "US", "instrument": "Equity"},
        "measurement": {"price_basis": "nominal", "annualization": "annual"}}
    facts = [selected, {**selected, "id": "opposing", "value": -5, "source_ids": ["independent"]}]
    for field, value in [("metric", "IT earnings growth"), ("benchmark", "SP500"), ("currency", "AUD"),
                         ("target_period", "2028"), ("kind", "observed_macro"), ("unit", "basis points")]:
        facts.append({**selected, "id": field, field: value})
    for parent, field, value in [("applicability", "geography", "Europe"), ("applicability", "instrument", "Bonds"),
            ("applicability", "subject", "Oil refiners"), ("measurement", "price_basis", "real"),
            ("measurement", "annualization", "quarterly")]:
        changed = deepcopy(selected)
        changed.update(id=field)
        changed[parent][field] = value
        facts.append(changed)
    facts += [{**selected, "id": "unknown-scope", "applicability": {}},
              {"id": "topic-only", "kind": "forecast", "target_period": "2027", "comparison_groups": ["market-outlook"]}]
    before = deepcopy(facts)
    plan = decision_source_check_plan({"facts": facts}, {"fact_ids": ["selected"]})
    assert set(plan["fact_ids"]) == {"selected", "opposing"}
    assert facts == before
    # A different measurement still belongs when the analyst explicitly cites it.
    plan = decision_source_check_plan({"facts": facts}, {"fact_ids": ["selected", "metric"]})
    assert set(plan["fact_ids"]) == {"selected", "opposing", "metric"}


def test_budget_deferral_is_not_a_provider_request():
    rows = [{"stage": str(i), "status": "failed", "failure_type": "budget_deferred"} for i in range(6)]
    result = workload_summary(rows)
    assert result["new_research_requests"] == 0
    assert result["deferred_research_tasks"] == 6
