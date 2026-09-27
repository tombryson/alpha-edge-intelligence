# High-Risk, Long-Horizon Portfolio Run: Interim Audit

## Status and Scope

**The latest run is still running. This is not a completed-memo assessment.**

- Job: `2e7fd841-6792-4494-ba40-84ea43b957a7`.
- Artifact: `portfolio_positioning_job_portfolio_high_risk_long_term_20260921_20260921_022441.json`.
- Started September 21 at 02:24:41 UTC (12:24 Melbourne).
- At 06:06:52 UTC: comparing proposals; 58 tasks completed, 45 completed model requests and 13 retrieval requests, with zero retries. Four review/lookup requests were active.
- The independent ideal and current-book assessment are saved. Final reconciliation, final commentary and financial-consistency checks have not finished.
- Both saved inputs contain `risk_tolerance=high` and `time_horizon=5+ years`. The original 17 current asset classes and both plays are unchanged; research has a new September 21 cutoff. No prior checkpoint was supplied.
- Read-only inspection of the live job, a downloaded partial artifact, the exact play-planning receipt, local architecture, and previous audited artifacts. No extra paid analysis, restart, model substitution, deployment or alteration of the running job.

[Open the run](https://llm-council-analysis.fly.dev/portfolio-analysis?run_id=portfolio_positioning_job_portfolio_high_risk_long_term_20260921_20260921_022441.json).

The content measurements below use the snapshot saved at approximately 06:00:52 UTC. Execution progressed to review during the audit. The findings may be corrected by the outstanding reviews; they are not defects proven to survive final settlement.

## Verdict

**Some requested behaviours work, but a better finished investment memo is not yet demonstrated.** The independent view is genuinely different from the existing book. The profile is used explicitly, and unknown research no longer becomes an automatic sell. However, the play planner misses three submitted commodity components, falsely associates copper with the submitted scarcity play, and the independent draft repeats a material inflation-comparison error.

The strongest interim financial finding is not that a bond or commodity weight is too high or too low. It is that the argument supporting the weight does not consistently follow from comparable observations and the research already available.

## Comparative Ratings

Subjective document-quality scores out of ten, not return forecasts. Earlier scores are carried forward from the saved comparative audits, not re-estimated using a common new dataset. Overall quality places more weight on material analytical defects than appearance. Portfolios, dates, models, research and now mandate inputs differ: this is not a controlled model A/B test.

| Artifact | Readability | Formatting | Financial analysis | Overall |
| --- | ---: | ---: | ---: | ---: |
| Legacy August | 8 | 8 | 6.5 | 7 |
| Completed September 19 remediation | 4 | 5 | 7 | 6.5 |
| Completed September 20 DeepSeek recovery | 7 | 6.5 | 6 | 6 |
| September 20 fresh run, stopped before final review | 6.5 draft | 6 draft | Not final | Not ranked |
| September 21 High / 5+ years | Not final | Not final | **5.5 for the two saved drafts only** | **Not ranked** |

August remains the strongest completed reading experience in this comparison, not the strongest verification architecture. Its own synthesis failed and it fell back to an earlier lane, so its presentation should not be mistaken for evidence of a flawless pipeline. The previous completed recovery had evidence-handoff and funding-reconciliation defects. The September 20 fresh run stopped awaiting credit and never passed its final-review comparison.

The new draft is readable, with about 2,474 words before supporting research, 9,766 words including the research appendix, two simple allocation tables and a longest main prose paragraph of 99 words. This is a partial document, not a fair length comparison with a finished memo. The final writer has not run. No new browser visual regression was performed in this audit; typography and responsive-layout scores are therefore withheld.

## What Improved

### 1. Independence is visible

The independent proposal has nine positive exposures; the current-book proposal has 18 including cash. Both target lists total 100% within floating-point precision. This does not prove final transition accounting, which has not run.

The independent proposal contains 22% TIPS, 24% developed equities, 14% energy equities, 8% bullion, 7% direct copper exposure, 6% grid/storage equities, 5% gold miners, 9% bills and 5% cash. The current-book proposal instead largely preserves the existing holdings, reducing energy to 25% and increasing cash/bills to about 9.09%.

These are distinct views, not the independent allocator copying every existing category. The model differentiates bullion, miner equities, commodity-price exposure, real duration and liquidity instruments.

### 2. The new profile reaches the reasoning

The independent draft explicitly connects copper and grid investment to the 5+ year horizon. It describes high risk tolerance as willingness to accept loss rather than an instruction to maximize risk. The current-book assessment also uses both preferences.

This verifies delivery and use of the parameters, not that their effect on exact weights is optimal. A long horizon is not a commitment to hold every ten-year instrument to maturity. A high risk tolerance does not establish capacity to absorb losses, spending needs, base currency or tax treatment.

### 3. Missing research no longer automatically creates exits

The current-book draft records 13 REVIEW decisions, three HOLDs, one TRIM and one ADD. It preserves about 41.43% in unassessed positions pending research instead of inventing negative conviction to sell them.

That is a meaningful correction to the previous behaviour. It is not completion of the analysis: retaining a position under review is not the same as positively underwriting it. The large unassessed pharma and silver allocations still need actual research.

### 4. Useful work survives while the job runs

The snapshot contains 432 observations and 68 source entries. Draft portfolios are readable before final settlement, checkpoints are saving, and no returned model call has a non-stop finish reason. No application output cap stopped the independent response at 32k: it returned 46,432 completion tokens.

Observation counts are not verified-fact counts. This fresh run also does not test interrupted recovery or prove every later stage retains the same observations.

## Material Draft Findings

### 1. The TIPS case compares different inflation periods and indices

The independent draft calls the gap between 2.33% ten-year inflation compensation, 3.4% current CPI and a 3.7% 2026 PCE forecast its clearest mispricing, supporting a 22% TIPS allocation. A contrary-evidence note acknowledges premia, but the executive summary and action rationale still use the invalid comparison.

Ten-year breakeven compensation concerns inflation over the matching bond horizon; it is not expected inflation for this year. PCE and CPI are different indices. Inflation can be high now and decline thereafter without the ten-year market being mispriced. The memo itself cites much lower later-year Fed projections, but does not reconcile those into a horizon-matched case.

The real-yield level can support an investment argument. This comparison does not establish relative undervaluation or the claimed strength of conviction. The Fed explicitly defines breakeven using nominal and inflation-linked securities of identical maturities and notes the role of premia: [Federal Reserve explanation](https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm).

Other overstatements include saying 0-1 year bills have no price risk and that position bands bound downside. Short maturity reduces rate sensitivity, and liquidity may reduce forced-sale pressure; neither is a guaranteed loss limit. Instrument prices depend on yield and time to maturity: [TreasuryDirect pricing](https://www.treasurydirect.gov/marketable-securities/understanding-pricing/).

### 2. The saved copper conclusion does not reconcile contrary forecasts already retrieved

The research answer explicitly says that the saved forecasts do not establish a consensus global deficit: it records later ICSG and Cochilco refined-surplus forecasts of 96,000 and 225,000 tonnes alongside Goldman ex-US deficits.

The independent action rationale nevertheless says the named forecasters all point toward a deficit. Its detailed discussion acknowledges contango, weak Chinese imports and different geographical scopes, but does not reconcile those saved surplus forecasts. This is an internal evidence-to-conclusion mismatch, not a claim that the audit independently verified each forecast or that copper must be bearish.

A long horizon can change the importance of near-term evidence. It cannot turn an omitted contrary forecast into a consensus.

### 3. Play research did not cover the submitted play components

The exact returned `research_plan_plays` response contains four questions: rates, copper, gold and oil. It contains no new fertiliser, silver or uranium question and omits the requested `play_components` section. The separate component-identification fallback ran, but it did not repair the question plan before dispatch.

Worse, the planner attaches copper to the scarcity play and invents a copper/industrial-metals component name. Copper may be independently investable; it was not in the submitted five-commodity play. The actual subsequent paid search asks for China's refined-copper imports separately from concentrate imports.

The earlier current-book research registry already identified silver and uranium as unresearched. Fertiliser is absent from this returned play plan. A valid play ID on a question is therefore not proof that the question represents a real submitted component.

The rates question for gold-over-bonds focuses on the curve and policy probabilities. It does not establish the central sovereign-debt/fiscal-confidence premise. Gold demand research helps, but it is not a complete comparative test of that hypothesis.

Implementation location: `research_phase` in `scripts/portfolio_positioning_memo.py` establishes missing components and maps component names, then passes the original question list to targeted research. There is no equivalent coverage reconciliation that ensures missing material components have a researched answer, a scheduled question or a specific reason no search is needed.

This does **not** prove the eventual memo will omit all three commodities: downstream reviewers may request further research. It does prove the dedicated play-research step did not fulfill its intended coverage at this boundary.

### 4. Measurement-level reuse has not passed this live test

The snapshot's 18 research questions contain zero `dimension_measurements` bindings. The play planner also returns empty binding arrays. The new measurement registry therefore cannot provide the intended measurement-level reuse on these questions, although ordinary fact and question reuse does work.

The run reports 156 reused facts and does not repeat the whole copper question. However, the initial question already requested separate refined/concentrate imports; the play plan changes the dimension wording and buys that unresolved measurement again. Empty bindings/aliases prevent the finer identity mechanism from helping.

Some alleged conflicts are not conflicts: September 18 and September 21 gold prices are described as same-day observations, and Q2 ETF outflows versus August inflows are treated as needing reconciliation. Different periods can represent a change rather than contradictory evidence. The planner needs stronger period/instrument comparison before paying to resolve a supposed discrepancy.

## Why It Is Slow

This is not a retry loop. All 43 completed model calls in the 06:00 snapshot returned once. There were also 13 retrieval requests: ten Parallel tasks and three Perplexity requests. The live count subsequently reached 45 completed model calls as reviews started.

| Completed phase | Approximate elapsed time |
| --- | ---: |
| Initial discovery, extraction, lane briefs and reconciliation | 31 minutes |
| Independent research planning and focused research | 55 minutes |
| Independent allocator | 53 minutes |
| Current-book planning and focused research | 36 minutes |
| Current-book allocator | 17 minutes |

The first six provider retrieval calls took only 2.6-4.6 minutes each and ran concurrently. Extraction and generation account for much of the later delay.

| Call | Input tokens | Output tokens | Time | Actual serving provider |
| --- | ---: | ---: | ---: | --- |
| Independent allocator | 107,695 | 46,432 | 52.7 min | Sail Research |
| Current-aware allocator | 126,106 | 25,518 | 16.9 min | DigitalOcean |
| Consumer-credit source extraction | 2,383 | 11,791 | 22.0 min | Morph |
| Sector-valuation source extraction | 3,018 | 6,373 | 15.2 min | Morph |

OpenRouter served 23 of the 43 completed model calls through Morph. Their median completion tokens divided by request wall time is approximately 8.9 tokens/sec, versus 114.1 for seven Wafer calls. These are observed end-to-end ratios including request delay, not controlled provider throughput benchmarks; workloads and reasoning differ. The evidence is sufficient to show that even small requests can be slow and that removing duplicated context alone cannot fix runtime.

Against the previous fresh run's matching stages, independent input grew from 98,217 to 107,695 tokens and output from 15,236 to 46,432; duration doubled from 26.1 to 52.7 minutes. The new independent response includes 18,728 reasoning tokens and about 27,704 other completion tokens. Both reasoning and the requested business output matter this time.

Current-aware output fell from 27,258 to 25,518 while elapsed time rose from 7.3 to 16.9 minutes. This is further evidence against attributing every delay solely to output size.

The redesign's largest expected reductions concern final settlement, corrections and commentary. Those stages have not completed, so this run cannot yet verify their latency/quality gains. The current review packets still include approximately 400k and 194k input characters per section.

Reported OpenRouter charges were about US$0.40 at the later status check, excluding outstanding calls and external retrieval. That low interim amount is not a full-run price or proof of good cost-to-value: expensive Opus reviews and downstream work remain, and hours of latency matter too.

## Most Useful Next Corrections

1. Reconcile the submitted component inventory against the research plan before paying for searches. Preserve useful output and fill only missing material coverage; never fail the whole memo for an omitted planning field. Do not silently replace a submitted play with a related commodity.
2. Treat differing dates, indices, regions and instrument conventions as explicit comparison dimensions. Separate genuine contradictions from changes or incomparable observations before requesting more research.
3. Compare each strong investment conclusion with its linked research answer and contrary observations. A disclaimer in an appendix does not repair a contradictory executive claim. Correct the specific claim; do not regenerate the entire portfolio.
4. Use observed serving-provider latency in future OpenRouter routing decisions. Establish a speed/cost policy with the user rather than silently switching models or imposing an output ceiling. Do not kill or duplicate the current paid calls.
5. Make measurement bindings usable on real planner output, with scoped enrichment when absent. Keep ordinary question/fact reuse as a fallback, and require an explicit changed source strategy before repeating an already unavailable measurement at the same cutoff.
6. Finish the current reviews before judging final play scores, funded transitions, commentary quality or overall memo superiority. Do not market a passing parser or an increased fact count as a passed financial-quality release gate.

## Evidence Files

- `outputs/audits/portfolio-high-risk-review-20260921/current-partial.json`: live partial artifact downloaded during this audit.
- `outputs/audits/portfolio-high-risk-review-20260921/plays-planner-receipt.json`: exact saved request/response proving the question-planning findings, including the supplied original plays.
- `docs/portfolio-full-rerun-audit-20260920.md`: prior fresh-run interim findings.
- `docs/portfolio-deepseek-recovery-comparison-20260920.md`: previous completed-memo ratings and rendered measurements.
- `docs/portfolio-redesign-remediation-20260921.md`: implemented changes and the explicit requirement for a paid live quality check.

No claim is made here that every market observation has been independently verified. The principal financial findings use the saved document's own research, plus the primary-source definitions linked above. No application code or running-job state was changed.
