# Portfolio memo comparison: 20 September 2026

## Verdict

**Better reading order and more reliable execution, but not a better-researched investment decision.** The latest memo is substantially easier to navigate than the previous completed remediation memo. It completes the two financial reviews and distinguishes concentration from investment merit more clearly. However, its recovery fails to carry forward 203 previously retrieved observations, several sells are justified by missing research, and the funding reconciliation remains unresolved.

My overall rating is **6/10**, versus **6.5/10** for the preceding completed remediation memo and **7/10** for the August document. These are subjective analyst-document scores, not expected returns. More bullish oil weights do not, by themselves, establish a better oil analysis.

## Scope

- Latest artifact: `portfolio_positioning_job_portfolio_recovery_20260919_140543.json`.
- Job: `23c85e9d-21cf-4248-b2f3-bf639154a01f`; succeeded, with the artifact labelled complete with limitations.
- Started 20 September at 00:05:43 Melbourne; finished 01:43:16, after 97m33s.
- Recovery source: `portfolio_positioning_job_portfolio_recovery_20260919_090032.json`, which stopped before final reviews and reconciliation.
- Same portfolio context and original plays. The independent and current-aware proposals were regenerated, not frozen unchanged. Their output hashes differ from the source run.
- DeepSeek Flash performed the principal analysis and exposure review; Opus performed the defensive and consistency reviews; Parallel Ultra2x was the retrieval assignment.
- Read-only audit of saved artifacts, receipts, recovery code and rendered documents. No new paid analysis, model change, trade or deployment.

The relevant local recovery/research code hashes match the manifest in the completed artifact. Older comparisons use the saved artifacts audited previously. Legacy portfolios, models and evidence differ; this is not a controlled model A/B test or an investment-performance backtest. Selected primary-source checks do not reverify every observation.

## Scores

Overall quality weights material evidence and implementation defects more heavily than presentation. It is not a simple average.

| Run | Readability | Formatting | Financial analysis | Overall quality |
| --- | ---: | ---: | ---: | ---: |
| Legacy August | 8 | 8 | 6.5 | 7 |
| Completed remediation, 19 September | 4 | 5 | 7 | 6.5 |
| Latest DeepSeek recovery | 7 | 6.5 | 6 | 6 |
| Ling/Opus replay | 6 | 5 | 7 | 6 |
| Earlier production, 18 September | 4 | 5 | 6 | 5.5 |
| Legacy April | 8 | 8 | 5 | 5.5 |

The immediately preceding research-led artifact is incomplete and cannot receive a finished-memo rating. Its research packet was broader than this recovery's. August remains the strongest finished reading experience, not the strongest verification architecture. April's attractive presentation does not cure its previously identified funding inconsistency.

## Measured Improvements

| Measure | Completed remediation | Latest recovery |
| --- | ---: | ---: |
| Positive independent / current-aware / final exposures | 12 / 17 / 20 | 12 / 13 / 15 |
| Raw final target sum | 100% | 100% |
| Returned new model requests, including retries | 67 | 43 |
| Retry requests | 19 | 2 |
| Full memo words, including appendix and sources | 14,957 | 17,235 |
| Default rendered memo words | 13,971 | 5,117 |
| Longest rendered paragraph, words | 1,570 | 100 |
| Desktop default memo height | 24,671px | 12,051px |
| Mobile default memo height | 62,651px | 23,344px |
| Recommended-portfolio heading offset, desktop | 10,983px | 430px |

Browser comparison used the unchanged saved memo text through the deployed frontend, with read-only fixture API responses at 1440px and 390px. This compares the current reader's treatment of each artifact, not historical frontend bundles. No JavaScript exceptions or horizontal memo-panel overflow occurred in the eight combinations. The latest expanded research appendix increases the desktop memo to 37,880px and mobile to 78,281px; the evidence is not concise simply because it starts collapsed.

Operationally, 21 initial research/extraction tasks were reused, 43 new model requests returned, and one new Parallel task ran. Reported incremental OpenRouter charges are US$3.93, excluding prior attempts and retrieval charges. This is not a full fresh-run price comparison.

Both retries were output truncations at 32,000 tokens. Both succeeded with a 64,000-token allowance, returning approximately 41,337 and 40,710 output tokens. The recovery mechanism worked; these were not context-window failures.

DeepSeek's exposure review completed with 87,790 input tokens and Opus's defensive review with 127,349. This does not prove that all the input reduction came from better packaging: the missing focused evidence also made these requests smaller.

## What Improved Analytically

1. **Independent thinking remains real.** The independent proposal has 12 positive exposures, the current-aware proposal 13, and reconciliation selects 15. The ideal introduces exposures outside the current book, including natural gas, agriculture and emerging-market local government bonds. Several are not adopted. The final does not simply mirror the current category count.
2. **Oil concentration is no longer confused as directly with a bearish oil thesis.** Energy moves from 33.7% to 24%, compared with 14% in the previous completed remediation and 6% in the stopped research-led proposals. The argument now says a supply thesis can be credible while the existing position is too large. That is better reasoning, but the 24% is not a verified optimal weight.
3. **Bullion and miners are separated.** The final proposes 6% bullion funded alongside a reduction in gold miners to 13%. Their economic overlap is acknowledged without claiming identical operating risks.
4. **Some financial corrections persist.** Term premium is distinguished from a curve slope, the core-PCE versus CPI-breakeven comparison is qualified, and falling yields are correctly described as raising existing fixed-rate bond prices.
5. **Play decomposition is cleaner.** Five scarcity exposures are recorded once each. The bond component preserves `relative_preference`; it is not rewritten as a short trade.

## Material Findings

### 1. Recovery retains the research expenditure but loses the research handoff

The source artifact contains **477 observations and 98 source entries**. The completed recovery contains **280 observations and 53 source entries**. Exactly 274 old observation IDs survive; six observations are new. **203 old observations are absent from the final evidence packet.** This is not simply renaming: the corresponding primary source URLs also disappear.

The old targeted lane records include 33 oil-balance observations and 75 unique fertiliser observations. None of those lane observation IDs appears in the new packet. Saved sources that disappear include the IEA September report, OPEC's report, and Nutrien's quarterly results. The original artifacts still contain this work; it has not been deleted from disk.

The cause is concrete:

- [Checkpoint writing](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_runtime.py:205) saves the partial artifact, caches, provider task identities and research reservations.
- [Recovery initialization](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_runtime.py:156) restores caches and reservations, but does not restore the saved partial research state.
- [The runner](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:3027) rebuilds the initial evidence ensemble and replans subsequent research.
- [The reuse logic](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:2844) looks for prior targeted lane results in `runtime.partial`, where recovery has not reinstated them. Exact provider-request caching does not solve newly worded questions with different identities and context.

The inherited allowance already has US$8.40 reserved against a US$9.00 run-level discovery budget. This is an internal cost envelope, not the provider account balance. The independent phase receives US$0.21 and current-aware US$0.15, neither enough for a US$0.60 task. The plays phase records zero allowance. Only the later challenge phase runs one new task, on term premium.

All 12 play-phase questions are deferred. Across the final registry, 80 questions are classified as 66 unanswered, 12 partial and two conflicting. None meets the fully answered criterion. That does not mean there are zero useful facts; it means the decision-specific research contract was not completed. Eight exact question texts repeat under different identities, in addition to paraphrases.

This is the opposite of the intended recovery behavior: **the spent allowance survives more reliably than the evidence bought with it.** My previous assurance that completed research would be reused was too broad: the 21 initial tasks were reused, but the downstream handoff was not preserved.

### 2. The oil and fertiliser conclusions remain materially under-researched

The oil prose is more balanced, but it still lacks the focused physical-market evidence. The [IEA September report](https://www.iea.org/reports/oil-market-report-september-2026) describes more than 10 mb/d of Gulf output shut in, a 95-million-barrel August inventory draw, severe refined-product disruption, and supply recovery deferred into 2027. It also forecasts demand contraction, an important offset. Those are material inputs to an oil-scarcity argument, not a guarantee that producer equities are cheap or should be increased.

The prior retrieval had this report. The current oil case cites sector performance, earnings breadth and short-term price headlines instead, while its Q4 Brent forecast assumes improved export capacity and Hormuz traffic. That forecast is conditional, but it has not reconciled the already retrieved scale of the disruption.

The fertiliser section says no producer margin information is supplied. Previously saved [Nutrien results](https://www.nutrien.com/news/press-releases/nutrien-reports-second-quarter-2026-results-1753) discuss nitrogen earnings, benchmark prices, gas costs and potash operating costs. They do not settle all nutrient balances or valuations, but they refute the notion that relevant company economics could not be obtained. The problem here is the application's evidence handoff, not an inherently unsearchable question.

### 3. Formatting differences still turn available numbers into apparent evidence gaps

The one successful new search retrieved a Kim-Wright term-premium observation of 0.9610% and a fitted Treasury yield of 4.8380%. Source excerpts encode the decimal point as Markdown `0\\.9610` and `4\\.8380`. Extracted evidence is flagged because literal excerpt and numeric matching do not normalize that presentation consistently.

Consequently, the final memo repeatedly describes term premium as unmeasured. An available term-premium level is not the same as a complete fiscal/inflation/geopolitical decomposition; that latter attribution remains genuinely unestablished. The system needs to retain that distinction instead of letting an escaped decimal undermine the available level.

The earlier signed-inventory fix does not pass its intended live test here: those inventory observations never reach the new packet.

### 4. Missing research becomes a sell instruction

Healthcare services, insurance, uranium, gambling, telecom and lithium are assigned exits substantially because they are unresearched or small. The uranium section explicitly says the position is not automatically a sell, then closes it because it is unassessed.

That is not an adequate investment case. A trade needs economic, risk-budget, mandate or liquidity justification. Missing research should identify the unresolved decision and next work; it must not manufacture negative conviction. Conversely, retaining an existing holding is not automatically safe either. The same standard must apply symmetrically to holding, adding and selling.

This asymmetry is especially visible when staples and defence receive small increases despite their own unassessed fundamentals, while similarly unassessed smaller positions are exited.

### 5. Funding and financial consistency remain incomplete

The raw final target weights total 100%, but this is not the same as a reconciled transition from the current book:

- The new 17% cash/T-bill sleeve is not linked correctly to the existing 0.426% cash balance. The reader shows proposed cash as `Unresolved` and a separate Cash row with no target. Final funding status is unresolved and one-way turnover is unavailable.
- The smaller-change policy now carries unchanged holdings explicitly, which is progress. Its total is **100.4244%**, apparently retaining old cash alongside the new liquidity sleeve. The model's lower-turnover assertion is not backed by a valid funded comparison. There are no quantified scenario outcomes.
- The memo repeatedly says neither saved baseline has nominal duration. The independent proposal actually has **10% in 2-5-year Treasury notes**, and the reconciliation elsewhere acknowledges that 10%. The final's 4% notes are not a newly discovered exposure absent from both baselines.
- The TIPS-versus-cash paragraph says TIPS only outperform if inflation exceeds roughly 2.33-2.35% breakevens. That threshold compares TIPS with a **same-maturity nominal Treasury**, not rolling cash. Cash comparison requires its expected reinvestment path and the relevant holding period. See the [Federal Reserve's definition](https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm).
- Gold miners are described as having zero carry. Miner equities can distribute cash; bullion's absence of contractual yield should not be copied into an unspecified equity sleeve.
- The crude discrepancy discussion sometimes presents WTI versus Brent differences as conflicting observations. Different benchmarks must be distinguished before testing same-instrument, same-contract and same-time contradictions.

Only two of ten recorded calculations are accepted: the 10y-2y and 30y-10y curve spreads. The other eight are unresolved. The final consistency reviewer says seven are unresolved, itself an incorrect count. The curve-spread implementation has improved, but the model still requests unsuitable calculation operations and carries unverified results into prose.

## Did It Debate The Plays?

**Yes, it debated them; no, it completed their research or the promised usable scoring.**

| Play component | Saved model judgment before qualification | Published outcome | Portfolio treatment |
| --- | --- | --- | --- |
| Fertiliser producers | Unassessed | Needs research | No allocation |
| Gold miners | 5/10, watch | Needs research | Trim to 13% |
| Silver miners | 4/10, watch | Needs research | Trim to 4% |
| Oil producers | 6/10, watch | Needs research | Trim to 24% |
| Uranium producers | Unassessed | Needs research | Exit current exposure |
| Physical gold | 6/10, watch | Needs research | Add 6%, funded from miners |
| Government-bond relative preference | Missing component assessment | Needs research | Prose declines exclusive gold-over-bonds preference |

These model scores are retained under `reported_judgment`, not the published final ratings. [Research qualification](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_research.py:220) replaces ratings with null when linked central premises remain unresolved. That is more honest than advertising unsupported precision, but it is no substitute for restoring and completing the research. It also leaves inconsistent prose such as a physical-gold heading saying not assessed while the paragraph says the score is held at six.

The critique appropriately distinguishes bullion, bills, intermediate nominal bonds and TIPS, and does not execute a short-bond idea. However, interpreting a preference for gold as an exclusive either/or overstates the submitted thesis. The aim should be to test relative hedge effectiveness and portfolio role, not refute a stronger claim the user did not make.

## Presentation

The executive view, comparison table, investment case and play discussion now precede supporting research. This is the clearest improvement. The text uses shorter paragraphs, individual exposure sections and direct source links. It is much closer to an analyst document than the previous long serialized research narrative.

Remaining presentation problems are visible, not hypothetical:

- The Strategic View panel renders `Growth: [object Object]` and equivalent inflation/liquidity strings. [The component](/Users/Toms_Macbook/Projects/llm-council/frontend/src/components/PortfolioPositioningLab.jsx:352) interpolates nested scorecard objects as text.
- The new memo is labelled `portfolio recovery`, rather than a meaningful report title.
- Duplicate unanswered questions recur under multiple exposures; the long appendix has become a research backlog.
- Unknown comparisons, raw question identifiers, unresolved cash and inconsistent play-score wording leak into the reading experience.
- August remains shorter and more selective: 4,607 total words, with an 8,343px desktop memo versus 12,051px for this run even before expanding its research.

## Priority Repairs

1. Restore phase-labelled research, sources, answers and completed task identities on recovery, before planning fresh calls. Preserve independence: holdings/play research must not leak into the blind phase. Test a real interrupted checkpoint across the code change, not just an in-memory merge helper.
2. Make paid research reusable across question paraphrases and dimension changes. Only charge the remaining envelope for genuinely new provider tasks. Report carried expenditure and reusable evidence together.
3. Normalize source presentation before comparing numbers and excerpts, preserving the raw original and transformation provenance. Missing decomposition must not erase an available level.
4. Keep investment merit, evidence confidence and portfolio action distinct. Resolve material uncertainty using restored research; do not convert a coverage gap into a sell rule or a whole-play null rating without component-level explanation.
5. Reconcile cash and unchanged holdings once. Compare genuinely funded alternatives. Test final statements against the actual saved baseline allocations and require the same financial comparisons throughout the document.
6. Fix the scorecard rendering, meaningful memo title and duplicate question display without redesigning the working legacy layout.

The next improvement should come from these data-flow and decision-consistency repairs, not another model or another generic review layer. Completing a run is a real operational improvement. It is not yet evidence that the research-led architecture has passed its financial-quality release check.

## Audit Artifacts

[Downloaded artifacts, derived metrics, extracted memos and browser screenshots](/Users/Toms_Macbook/Projects/llm-council/outputs/audits/portfolio-deepseek-recovery-review-20260920) include reproducible read-only inspectors. Previous reference audits: [research-led partial](/Users/Toms_Macbook/Projects/llm-council/docs/portfolio-research-led-comparison-20260919.md) and [completed remediation](/Users/Toms_Macbook/Projects/llm-council/docs/portfolio-remediation-comparison-20260919.md).
