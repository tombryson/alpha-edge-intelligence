# Portfolio Memo: Second-Pass Input, Reasoning and Handoff Audit

Status: completed read-only investigation, 21 September 2026. Remediation is proposed, not implemented.

Historical findings below remain the baseline. Subsequent implementation,
the failed live run and its stopped recovery are reassessed in the
[September 22 full audit](./portfolio-r360-run-audit-20260922.md#september-22-stop-decision-and-full-reassessment).
That document is the current status and priority source; it retains D01-D12
through the complete U01-U17 mapping rather than replacing this financial audit
with a performance-only checklist.

## Executive Finding

The principal weakness is not a shortage of model intelligence or a simple shortage of sources. The system does not consistently preserve the meaning of evidence as it moves from source passages to observations, research answers, decisions and reader prose.

This deeper pass adds confirmed defects to the [first completed-run audit](./portfolio-final-comparison-and-concurrency-20260921.md): wrong table-column extraction, inadequate citation excerpts, loss of opposing forecasts from downstream requests, over-broad evidence statuses, inactive monitoring, and rejected factual patches. It also finds financial overreach where US sector evidence is applied to unspecified holdings, short-horizon observations are used for a long-term allocation, and precise weights survive material changes to their premises without an adequate explanation.

The memo remains useful as a discussion document, but its apparent diligence exceeds its verified decision quality. Do not equate more facts, more warnings, or more completed reviews with better analysis. Do not resolve this by throwing away the memo, suppressing uncertainty, or requiring every optional field before publication.

## Scope and Evidence

Run: `portfolio_positioning_job_portfolio_recovery_20260921_085131.json`, recovering the original high-risk/long-term run beginning at 02:24:41 UTC. The saved research cutoff is `2026-09-21T02:24:42.516553Z`.

- Inspected the original submitted context, compacted snapshot, preserved proposals, two reviewers and their component batches, research phases, final settlement, corrections, commentary and final review.
- Traced actual dispatch fact inventories, not merely what the current source code would send.
- All 26 local files listed in the completed artifact's code manifest match their recorded hashes. This supports code-to-artifact attribution; the recovery manifest does not independently prove the original request text of every earlier stage.
- Recomputed the smaller-change funding comparison without altering the artifact.
- Independently checked selected primary reports and visually inspected the World Bank PDF table. This is not independent verification of all 665 observations or a full investment backtest.
- No paid analysis, model substitution, deployment or production-data modification. New files are audit exhibits and documents only.

Supporting exhibits live in [the audit directory](/Users/Toms_Macbook/Projects/llm-council/outputs/audits/portfolio-final-review-20260921). The [uplift draft](./portfolio-evidence-decision-uplift-draft-20260921.md) is the implementation proposal.

## Input Boundary

| Input | Actually supplied | Consequence |
| --- | --- | --- |
| Current allocation | 17 non-cash asset classes, cash, total value 58,939.32; weights reconcile to 100% | Valid input for an asset-class allocation discussion |
| Snapshot date | 18 September, 11:16:06 UTC | Deliberately retained for this comparison; not a fresh holdings valuation on 21 September |
| Security positions | Empty; `holdings_count=0` | Zero records does not mean an empty portfolio |
| Company evidence | Empty | Producer type, geography, hedging, operating stage and company valuations are not known |
| Investor preferences | High risk tolerance; 5+ years | Correctly present in the independent context and later pipeline |
| Portfolio scope, objective, base currency, benchmark | Not supplied | Whole-wealth suitability, FX impact and implementation comparisons remain conditional |
| Scenario assumptions and sensitivities | Empty | The quantitative scenario module has no inputs |
| Plays | Five scarcity components and one gold-versus-bonds preference | Frozen component inventory is correct; research allocation is not |

This is not a recommendation to make security-level inputs mandatory. Asset-class-only analysis is legitimate. The defect is making claims beyond its input resolution. The three-day-old comparison snapshot is also not inherently a bug; live execution must distinguish an intentionally frozen comparison from refreshed holdings.

## Findings

### D01. A source table was converted into the wrong time series

The World Bank source excerpt contains all row values plus displaced headers. Extraction selected the first Brent and WTI values and labelled them August 2026. Visual inspection of the [September Pink Sheet](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Pink-Sheet-September-2026.pdf) confirms:

| Series | Value used as August 2026 | Actual period of that value | August 2026 column |
| --- | ---: | --- | ---: |
| Brent, USD/bbl | 82.6 | 2023 annual average | 90.9 |
| WTI, USD/bbl | 77.7 | 2023 annual average | 82.7 |

Facts `fact_0c0bcace6400973e13e2` and `fact_e7c7a17c088a180ce8cc` are explicitly marked unsupported by the saved source reviewer for this column error. Nevertheless, the shared market narrative continues to call them August prices, and both remain cited by the final Energy target and final finding checks. A checker detecting an error is not a correction reaching the investment decision.

The error manufactures an apparent price discrepancy and consumes later analysis on reconciling it. Required repair: retain row/column/period provenance, correct or supersede the observation, and invalidate dependent current claims while preserving the historical draft.

### D02. A citation excerpt is treated as sufficient document access

The saved September 18 FactSet source contains only 705 characters. It gives aggregate Energy growth and the oil-price move but omits the subsector explanation. The full report distinguishes estimated growth of 420% for refining/marketing, 104% integrated oil and gas, 51% exploration/production, 8% storage/transportation, and -9% equipment/services. Aggregate Energy growth is not upstream producer growth. The report also contains newer P/E observations than the August numbers used in the final memo. [FactSet report](https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/EarningsInsight_091826.pdf)

The issue is not proof that the current oil holdings are refiners or upstream producers: their identities were absent. It is the missing applicability bridge.

`hydrate_citations` skips source extraction whenever `content` is nonempty. A short excerpt thus satisfies source hydration even if a material question needs its table headers, neighbouring paragraphs or latest valuation section. This is visible in [source hydration](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_sources.py:40) and [Parallel result normalization](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_retrieval.py:140).

The remedy is selective within-document retrieval, not fetching every full document or requesting another broad search. Five initial results should be a discovery starting point, not evidence that each document has been adequately inspected.

### D03. Opposing evidence disappears from the final decision inputs

Two saved forecasts are important counterweights to the early deficit narrative:

- `fact_f19a2b907dfe4f43f438`: ICSG April forecast of a 96,000-tonne refined-copper surplus in 2026.
- `fact_7f17d81f2903315bfdc6`: Cochilco Q2 forecast of a 225,000-tonne refined-copper surplus in 2026.

Both were present in the independent allocator and provisional comparison inputs. Neither was included as an observation in the final settlement, either writer input, or either final consistency review. Deficit observations remained included. The final case describes a range of deficit estimates rather than reconciling surplus versus deficit and global versus ex-US forecasts.

These forecasts are not independently endorsed here; their relevance is that the system retained them, then omitted them from the requests responsible for the final conclusion. Earlier reviewers had an observation catalogue available, but did not retrieve both contrary observations through their follow-up lookups.

[Dispatch trace](/Users/Toms_Macbook/Projects/llm-council/outputs/audits/portfolio-final-review-20260921/deep-contrary-evidence-trace.json) proves this is a request-selection problem in addition to an interpretation problem. The series fallback in [scoped evidence selection](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_tasks.py:130) matches exact metric, benchmark and unit text. A surplus forecast and a deficit forecast use different metric names; opposing assumptions need explicit semantic relationships.

### D04. Evidence status conflates wrong data with repairable metadata

Of 665 observations, 234 have field-check results. The final statuses are 48 supported, 60 unsupported and 557 unresolved. These are application labels, not an independent estimate of how many statements are true.

The final targets directly cite 49 distinct IDs: 10 supported, 27 unresolved, 11 unsupported and one missing. Many unsupported labels concern metadata, not a wrong financial value:

- The 109.6% Energy growth estimate is marked unsupported because its currency is `USD` instead of not applicable.
- The 19.6x equity P/E is similarly marked unsupported on currency.
- Q1 AISC is marked unsupported because the model represented a quarter with a precise quarter-end observation date.
- A FOMC forecast is marked unsupported because a release date was used as its observation date.
- Six observations have all nine reviewer checks supported yet remain unresolved under static validation.

In contrast, the World Bank column error genuinely contradicts the value-period pairing. These cases require different handling.

[Normalization](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_evidence.py:176) requires the same fields for market quotes, period statistics and forecasts. [Coverage](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_research.py:279) can mark an entire answer unresolved because one referenced observation has a timing issue. [Investment projection](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_tasks.py:15) retains the global status and adverse checks but drops the explanatory review reason and positive review dimensions. That saves tokens by discarding distinctions the next model needs.

Result: the copper-miner question has 17 cost citations and 18 production citations yet every dimension is unresolved. Gold-miner operating research suffers the same treatment. This helps explain, but does not excuse, the final assertion that no research was supplied.

### D05. The date model can create false cutoff violations

Six China copper-import facts are flagged as published after the cutoff. The source metadata says `2026-09-21 09:03 (site time)`; the fact becomes `2026-09-21T09:03:00` without an offset. The timestamp helper treats naive dates as UTC. If the website timestamp were UTC+8, it would precede the cutoff. The source timezone was not established in this audit, so neither future leakage nor eligibility is proven.

Preserve raw timestamp, precision, timezone and verification status. A monthly observation is a period, not an invented instant. A forecast's publication date is its availability date, not the future outcome's observation date. Unknown timezone should remain unknown, not silently UTC.

### D06. The shared macro narrative is an unmaintained derived artifact

The initial market view calls Q2 actual GDP versus Q3 nowcast a conflict and treats global and regional forecasts as competing estimates. Different periods can describe acceleration or deceleration; they are not automatically contradictory measurements.

It also calls inflation elevated to justify an inflation-rising quadrant without a consistently aligned trend comparison. A high level, a monthly change, an annual rate and forecast risk skew answer different questions. Q2 may still be a defensible analyst view, but the justification is incomplete.

Later source reconciliation returns updated facts while preserving the earlier narrative. There is no reliable dependency from an observation correction to every derived market claim. The executive context even continues to say no broad-market valuation was supplied despite a P/E observation being used elsewhere.

Require claim-level source dependencies and a current market view with explicit period and geography, not another unconditional global synthesis on every new fact.

### D07. The horizon and opportunity search are not fully aligned

The high/5+ year mandate is delivered correctly, but the macro lane still explicitly asks for a dominant 12-24 month regime. Most supplied sizing arguments concern current yields, last quarter's beats, short-term curves and annual earnings. The three final `forecasts` merely restate the Fed's projections and a nowcast; they are not accountable forecasts from this portfolio thesis.

The independent and current-aware models also exclude broad emerging markets partly on MENA growth. Developed equities are justified predominantly with S&P 500 evidence. Neither regional proxy establishes the investable universe's economics.

A five-year memo needs structural supply response, capital investment, cash-flow durability, starting valuation and adverse paths over that horizon, while retaining shorter catalysts as timing information. It does not need arbitrary five-year point forecasts or forced country quotas.

### D08. Commodity and asset-class arguments stop before shareholder returns

The improved oil view now uses supply and inventories, but the value chain still matters. The [IEA September report](https://www.iea.org/reports/oil-market-report-september-2026) describes unusually severe refined-product disruption, regional refining-margin differences, freight effects and an assumed supply recovery in 2027. Those are different exposures and horizons, not a single oil bullish/bearish score.

The [World Gold Council cost analysis](https://www.gold.org/goldhub/gold-focus/2026/08/record-gold-prices-outpace-rising-mining-costs-q126) explains that royalties contributed materially to AISC increases, with jurisdiction-specific effects and fuel/freight risks. Spot minus historical aggregate AISC is not distributable cash flow or proof that every miner benefits equally. Scarcity can increase producers' revenues and their energy/input costs simultaneously.

The clean-energy allocation is another unsupported bridge: declining project LCOE can benefit buyers, developers or storage owners while compressing equipment suppliers' margins. The final memo admits no listed-equity return case and says cash is preferred until that bridge exists, yet assigns 1.45%. That is an unresolved opportunity-cost contradiction, not a reason to automatically delete the idea.

Copper futures require a specified funded exposure, collateral treatment and rolling strategy; a price thesis is not a fully defined total-return instrument. TIPS require distinction between individual held-to-maturity securities and a fund with continuing duration, plus investor currency. [TreasuryDirect's instrument description](https://www.treasurydirect.gov/marketable-securities/tips/) establishes inflation adjustment and maturity terms, not a guaranteed investor-specific real return from an unspecified vehicle.

### D09. Decisions anchor before late evidence, without proving the retained sizing

Provisional weights and final weights are identical except cash moving from 3% to 3.001633575%. The final settlement explicitly says the added research confirms the provisional destination. That can be legitimate; this audit does not require weight changes as proof of intelligence.

But the unchanged silver, copper and gold reasoning still misstates available research, and the revised oil thesis does not establish why 16% rather than 20% or 24% best fits the mandate. Several new weights are near a reduced version of the independent ideal; the record does not prove mechanical averaging, but it also does not establish a strong comparative sizing objective.

Important distinctions must survive: thesis attractiveness, confidence in evidence, portfolio fit, and justified trading now. Broadening the number of asset classes does not prove reduction of common commodity, equity, liquidity or currency risk.

### D10. Risk comparison exists in code but has no producing stage here

The scenario calculator consumes `snapshot.scenarios` and `risk_exposures`. Both are empty. This workflow does not create a sourced or explicitly assumed scenario packet before comparing allocations. The saved `scenario_comparison` is empty.

Therefore statements about downside being bounded, or one mix being superior in stress, are not backed by that module. A qualitative stress discussion is still useful. Quantification should use named assumptions and ranges, not invented correlations, probabilities or a forced optimiser.

### D11. Review resolutions are not reliably tied to repaired claims

The two reviewers produced 55 findings. Final dispositions mark 37 accepted and 18 unresolved, using only three distinct explanations. Grouping saves repetition, but a generic declaration that corrections were incorporated is not evidence they appear in the document.

Some disposition references are malformed: two use a `fact_` prefix with finding identifiers; the final semiconductor target cites a non-existent fact ID. The correct-looking near-match must not be silently guessed.

Nine prose patches were applied and seven remain unapplied. [Patch application](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_judgment.py:566) does not permit the `excluded_opportunities` or `smaller_change_alternative` roots or the `observed_expectation` leaf, even though the final reviewer proposes corrections there. Thus the saved archive can contain a correct proposed correction while the reader still sees the stale claim. Rejection reasons are not recorded per patch.

Exact-original matching is useful protection against editing a changed paragraph; it should be retained alongside stable semantic IDs and explicit rejected/superseded/applied states. A final reviewer also repeats the wrong World Bank figures while declaring the benchmark issue resolved. Review success is not a truth certificate.

### D12. Monitoring is prose-shaped, not operational

All seven monitoring conditions return `unassessed`, with null observation and null ID. The model emits free-text metric/benchmark/unit descriptions; [evaluation](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_decisions.py:469) requires exact string equality to stored observations.

Several conditions require sustained or consecutive observations, but the schema/evaluator checks only the latest single value. The copper spread threshold also needs an explicit sign convention: the saved positive 36 represents a contango magnitude, while the trigger treats a positive spread as backwardation. Binding those labels loosely could produce the wrong signal.

These are not demonstrated live monitors. Distinguish a suggested review condition from a configured, sourced, evaluable condition. Do not silently create recurring paid searches.

## Clarifications and Existing Findings

- The independent model genuinely does not receive holdings or plays. Different proposal shapes support this; the current-aware branch sees shared research, so the two views are not independent sources of truth.
- The frozen play inventory is correct. Planner omissions, an invented copper component, budget allocation and broad play-to-component dependency mapping remain the problems. Review batching did supply the plays in a later batch; one batch's sentence saying no plays were supplied must not be misread as proof the entire review missed them.
- The smaller-change portfolio is now **balanced**, with **8.6635% one-way turnover**. An earlier invalid-range diagnostic was repaired. Full-destination turnover remains unresolved because of the bullion/holdings mapping. Do not carry forward the claim that neither alternative has a computable turnover.
- The final 0.0054 percentage-point weight residual is immaterial. It is not comparable in importance to wrong source periods or funding claims.
- Approximately 72% of the original request span has only one active request, despite working concurrency elsewhere. Search-wave barriers, isolated branches run serially, serving-provider latency and repeated task output explain the runtime; this run had no application retries. The detailed timing remains in the first audit.
- The corrective writer leaves instruction-like language in the final memo and expands the primary-theme field. Preserve the established UI; repair the writer's document responsibilities.

## Conclusion

The next uplift should repair the evidence-to-decision contract before adding more research agents. Its success criterion is that the right observations, uncertainty and opposing interpretations reach the right decisions, with arithmetic and execution status handled by code. Concurrency should then remove false dependencies while preserving independent reasoning.

The [draft uplift](./portfolio-evidence-decision-uplift-draft-20260921.md) maps every finding above and every outstanding item from the first audit to a scoped change and an acceptance test.

## Reproduction

Run from the repository root:

```sh
.venv/bin/python outputs/audits/portfolio-final-review-20260921/deep_audit.py
```

Key generated exhibits: `deep-inputs.json`, `deep-evidence-metrics.json`, `deep-proposals.json`, `deep-reviews.json`, `deep-market-view.json`, `deep-questions.json`, `deep-contrary-evidence-trace.json`, `deep-integrity-probes.json`, `deep-code-provenance.json` and topic-specific fact lists. These are derived audit artifacts, not edits to the saved run.
