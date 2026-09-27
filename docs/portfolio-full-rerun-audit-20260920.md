# Fresh paid portfolio rerun: interim audit

## Status

**Not a completed comparison yet.** The fresh run generated research, independent and current-aware proposals, play reviews, a reconciled draft and commentary. It stopped at the credit check before the final consistency review and any resulting scoped correction.

- Run: `portfolio_positioning_job_portfolio_full_rerun_20260920_20260920_033409.json`.
- Job: `7c10f1fc-92c1-419f-87c7-1f1cf457b22a`.
- Production release 355; no model substitutions or code changes during the run.
- Same 17 current asset classes, original portfolio snapshot and two plays as the previous completed recovery. No resume checkpoint, frozen research or old task cache was supplied.
- Started 20 September 2026 at 13:34:09 Melbourne; stopped at 18:30:30 after **4h56m21s**.
- OpenRouter preflight passed with $11.16 available against a $5.93-$7.08 estimate. At the stop, $3.51 remained and the next request required $8.38 of credit headroom. That is a conservative request allowance, not its eventual bill. Another $10 was requested as a buffer; no credits were purchased.
- Saved artifact is `awaiting_credit`. Final review and repair must be resumed from its checkpoint, not by repeating the paid research.

[Open the saved draft](https://llm-council-analysis.fly.dev/portfolio-analysis?run_id=portfolio_positioning_job_portfolio_full_rerun_20260920_20260920_033409.json).

The findings below concern this unfinished draft. The remaining review may correct some of them. They must not be presented as defects that survived a completed final-review pass.

## Interim Verdict

**Research coverage improved materially; decision integrity has not yet caught up.** There is substantially better physical-oil and producer-level evidence. All observations collected during this run reach the saved evidence packet. However, the draft still has an invalid funded transition, drops several correctly identified play assessments from display, and makes a significant fertiliser inference contradicted by its own retrieved numbers.

The previous completed memo received 6/10 overall. I am withholding a finished-memo rating for this run until its final review and repair complete. For the current draft only, readability is approximately 6.5/10 and formatting 6/10: still readable, but more repetitive and longer than its predecessor. These are subjective document-quality judgments, not investment-return forecasts.

## Measured Comparison

| Measure | Previous completed recovery | Fresh draft |
| --- | ---: | ---: |
| Saved observations | 280 | 578 |
| Source entries | 53 | 100 |
| Positive independent / current-aware / final target rows | 12 / 13 / 15 | 9 / 19 / 20 |
| Fully answered research questions | 0 | 2 |
| Partially answered questions | 12 | 47 |
| Unanswered / conflicting questions | 66 / 2 | 26 / 0 |
| New OpenRouter calls, including retries | 43 | 112 |
| Retry requests | 2 | 6 |
| New retrieval requests | 1 | 18 |
| Reported incremental OpenRouter cost | $3.93 | $7.75 |
| Full saved memo words | 17,235 | 24,664 |
| Default reader words | 5,117 | 5,758 |
| Desktop default memo height | 12,051px | 13,475px |
| Mobile default memo height | 23,344px | 26,380px |

The earlier run reused paid research, whereas this one is fresh. Their costs are not like-for-like fresh-run prices. The fresh draft's 18 retrieval requests comprise **15 Parallel Ultra2x tasks and three Perplexity requests**. Parallel's configured task estimate is $9.00; the combined reported OpenRouter cost and Parallel estimate is already $16.75, excluding Perplexity and remaining work. This is not a reconciled provider invoice.

The 124 completed tasks are 106 successful model calls plus 18 successful retrieval calls, not 124 macro-level pipeline stages. Six additional attempts failed and were retried: two truncations, two invalid-JSON responses, one scalar-value repair and one upstream transport failure. None of the earlier run's tasks was reused.

## What Improved

1. **Evidence retention works within this fresh execution.** All 223 initial observations and all 355 focused observations are present downstream: zero missing observation IDs across the 15 saved research lane records. This does not, by itself, test an interrupted recovery; resuming this checkpoint will provide that separate live test.
2. **Oil is finally grounded in physical conditions.** The draft explicitly incorporates more than 10 mb/d of Gulf output shut in, constrained exports and extremely limited effective spare capacity. The IEA also reports significant demand destruction, which must remain in the opposing case. The EIA's $67/bbl forecast is specifically Brent in the second half of 2027, conditional on restoration; it is not a current price or an unconditional target. [IEA September report](https://www.iea.org/reports/oil-market-report-september-2026), [EIA global oil outlook](https://www.eia.gov/outlooks/steo/report/global_oil.php).
3. **Producer economics reach the play discussion.** Gold and silver discussion now uses reported realised prices, AISC, production guidance and cost pressures. Fertiliser research separates nutrients instead of equating a higher commodity price with a higher producer margin.
4. **Independent allocation remains distinct.** Nine independent exposures differ substantially from the 19 current-aware targets. The final proposal is not merely a copy of the current book, although it still ends with a long tail of small positions.
5. **Presentation fixes hold technically.** Ten read-only browser combinations across current/legacy artifacts, desktop/mobile and light/dark completed without JavaScript exceptions, `[object Object]` strings or horizontal memo-panel overflow. Supporting research remains collapsed. This preserves readability mechanics, not editorial concision.

Observation count is not verified-fact count: 379 observations pass source-text matching, 199 need verification, and strict claim review labels 80 supported, 472 unresolved and 26 unsupported. Some unresolved flags concern publication metadata or missing table headers; others are genuine evidence gaps.

## Outstanding Draft Findings

### 1. The funded transition is 107%, despite a 100% target list

The 20 raw targets sum to 100%, but their relationships to the current holdings do not reconcile. A 4% pharma target and 3% combined industrial-metals target are supplemented by separately retained 4% pharma, 1.5% base-metals and 1.5% copper rows. The displayed table therefore totals 107%.

The old cash problem is improved: the existing 0.426% cash is linked once to the new 12% cash target. The remaining failures concern non-cash identity and capital-transfer relationships. The smaller-change alternative totals 99.8054% and cannot support a valid turnover comparison either. The pending scoped review must resolve these relationships explicitly; silently normalizing the weights would conceal the problem.

### 2. Correct component IDs are rejected when display names change

Fertiliser has an explained 4/10 judgment and physical gold has an explained 6/10 judgment in `unmatched_legs`. The government-bond leg also contains a substantive assessment. All three have the correct frozen component IDs, but the UI says they have not been assessed.

The cause is [complete_play_assessments](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_independent.py:476): after matching the ID, it also requires the normalized display name to match exactly. `Physical gold bullion` is rejected against `Physical gold`; a more descriptive fertiliser name is rejected in the same way. This is application-induced loss of usable analysis, not a research failure. Preserve identity by the stable ID and canonicalize the display label, while still rejecting genuinely unknown IDs or conflicting economic roles.

### 3. The nitrogen conclusion contradicts available producer data

The draft says potash is the only nutrient with an evidenced positive producer spread and describes nitrogen margins as negative or falling. Its own packet contains Nutrien nitrogen realised price of $452/t and COGS of $216/t. Nutrien reports **$236/t gross margin, versus $168/t a year earlier**. Phosphate weakness is real, but cannot be generalized to North American nitrogen economics. [Nutrien Q2 results](https://www.nutrien.com/news/press-releases/nutrien-reports-second-quarter-2026-results-1753).

The relevant saved facts are `fact_aef5dd96113f25dcbe92` and `fact_d9058718e509b2a019aa`. This is not a call for another broad fertiliser search: the contradictory evidence is already present. It needs a nutrient-and-region comparison and explicit treatment of production volumes versus per-tonne margins. Positive margins still do not establish attractive equity valuation.

### 4. Repeated inventory research crowds out essential play questions

Five of the 12 focused Parallel calls concern overlapping oil inventory, physical tightness and days-of-cover questions. Copper also receives two closely overlapping searches. The calls obtain more observations but do not settle the repeatedly requested observed OECD inventory measure.

Meanwhile oil-producer economics, both uranium questions, the sovereign-fiscal mechanism and the gold-versus-bonds comparative hedge question are deferred. The gold-over-bonds play therefore remains untested on its central causal claim despite the large packet. Research reuse by explicit IDs has not prevented the planner from expressing the same unresolved question under new IDs. The next design correction should protect coverage of distinct material decisions, record unavailable measurements, and stop repeated equivalent searches unless the source strategy or missing dimension changes.

### 5. Arithmetic and language still disagree

The draft describes the 10-year real yield rising from 2.43% to 2.68%, but `computed_claims` records **-25bp**, because [the calculator](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_judgment.py:314) subtracts the second fact from the first without validating chronological orientation for `time_change`. The arithmetic is mechanically consistent with the operand order but wrong for the stated change. A `calculated` status is not semantic verification.

Other contradictions remain: uranium moves from 0.817% to 1% while the prose says no addition; rare earths moves from 3.281% to 1% while described as held; the play summary says the potash expression is not funded although the target table includes 1%. These should be checked against the actual transition, not merely repeated in another review narrative.

### 6. More research is not yet translated into an investable ranking

The draft has better cost and operating evidence but still lacks a disciplined valuation-to-return comparison. A wide realised-price/AISC spread does not establish that miner shares are cheap. Conversely, a high energy allocation may warrant concentration review without proving 15% is the right destination. Account role, base currency, hedge policy, horizon and transaction costs remain unknown.

The improved distinction between investment merit and portfolio weight is valuable. It is weakened when concentration is asserted as sufficient to choose exact weights without showing the adverse-case impact or comparing funded alternatives.

### 7. Execution remains too slow and its funding estimate is inadequate

Four Opus review sections cost $5.50 on approximately 749k aggregate input tokens. DeepSeek consumed approximately 5.32m input and 1.22m output tokens for $2.26. Final allocation alone received about 439.7k input tokens and took 34 minutes on its successful attempt; the independent allocation took 26 minutes and evidence reconciliation 17 minutes.

The preflight's $7.08 upper estimate was exceeded before completion, while the next request needed $8.38 of conservative headroom. Expected total cost and maximum simultaneous request allowance must be estimated separately using the actual phased plan. A passing total-cost estimate must not imply the later request guard will pass.

A read-only recovery preflight during this audit reproduced the inconsistency: it reported `ready` with $3.41 available and $0.98-$1.22 estimated remaining cost, despite the saved next-request guard requiring $8.38. No recovery was submitted on that misleading result. The immediate blocker is the application's conservative request guard, not proof that the provider has exhausted the account balance.

Provider latency and large, repeatedly serialized contexts both contribute. Six retries are not the main explanation for nearly five hours. Monitoring also encountered Fly tunnel outages, delaying retrieval of some status updates; that is separate from the server's recorded execution duration.

## Completion Checklist

- Obtain the requested OpenRouter top-up and verify the balance.
- Resume this checkpoint without changing models, inputs or research cutoff.
- Confirm all 578 observations and saved phase boundaries survive recovery.
- Let the existing consistency review and scoped correction finish; preserve both the initial draft and completed artifact for comparison.
- Recheck funded totals, visible play assessments, nitrogen economics, calculation direction and action/weight consistency.
- Refresh browser measurements and then assign the final comparative ratings.

Read-only audit artifacts, scripts and screenshots: [portfolio-full-rerun-20260920](/Users/Toms_Macbook/Projects/llm-council/outputs/audits/portfolio-full-rerun-20260920). No production code or saved financial conclusion was changed during this interim audit.
