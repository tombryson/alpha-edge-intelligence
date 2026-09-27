# Portfolio Memo Comparison: September 23, 2026

## Verdict

The latest memo completed and contains real final allocation and commentary responses. It is a better financial discussion than the September 20 and 21 memos, but not an unqualified improvement in the finished product. Evidence coverage, careful distinctions and allocation arithmetic have improved. Research handoff, play completion, comparative scenario analysis and reading quality remain materially deficient.

**Best financial reasoning of these four outputs: September 23. Best finished reading experience: August 11. Overall usefulness: September 23 is approximately tied with September 21, below August as a complete memo product.** This does not mean August's financial claims were more thoroughly substantiated.

[Completed memo](https://llm-council-analysis.fly.dev/portfolio-analysis?run_id=portfolio_positioning_job_portfolio_finish_only_20260923_100700.json)

## Scores

Scores are qualitative editorial judgments out of ten, not backtested investment performance or a mechanical average. Financial analysis includes evidence use, economic reasoning, contrary cases, horizon and sizing. Overall quality emphasizes decision usefulness and completeness, with readability a substantive part of usefulness. Previous scores are retained for comparability.

| Memo | Readability | Formatting | Financial analysis | Overall quality |
| --- | ---: | ---: | ---: | ---: |
| August 11 legacy | 8 | 8 | 6.5 | 7 |
| September 20 recovery | 7 | 6.5 | 6 | 6 |
| September 21 recovery | 6 | 5.5 | 6.5 | 6.5 |
| September 23 completion | 5.5 | 5 | 7 | 6.5 |

The latest earns the higher analytical score for actual sector economics and more careful treatment of facts, forecasts and instruments. It does not earn a higher overall score because two plays remain unscored, some retrieved evidence never reaches the decision, comparisons are incompletely mapped, and repetition materially increases the reading burden.

## Scope And Comparability

- Latest artifact: `portfolio_positioning_job_portfolio_finish_only_20260923_100700.json`, completed at 10:25:22 UTC / 20:25:22 Melbourne on September 23.
- Compared against the saved September 21 recovery, September 20 recovery and August 11 memo, using their actual text and structured outputs.
- The successful finish-only continuation took approximately 15 minutes 30 seconds. That is **not** the duration of the complete research-and-recovery chain. Retained receipts begin at 02:28:49 UTC, almost eight hours before final completion.
- This deliberately finishes the saved release-362 research. It is not a fresh validation of every subsequent local architecture change. No discovery or source-check requests were added during completion.
- Inputs are not controlled: the latest portfolio starts with 50.39% energy, versus 33.66% in the older comparison portfolio. Research dates, models and play specifications also differ. Allocation changes cannot be attributed solely to architecture or model quality.
- Final allocation and commentary used `anthropic/claude-opus-5.5`; retained upstream work includes GPT-6 Sol, GPT-6 Luna Pro, DeepSeek Flash and Parallel ultra2x. This is not an isolated Opus-versus-DeepSeek benchmark.
- All six plays, high risk tolerance, 5+ year horizon, original evidence and the sealed independent/current baseline portfolios were retained. The prior recovery verification has 19 passing output checks.
- Source checks were closed at the user's explicit request. The 478 saved verdicts were retained; 119 selected facts remain explicitly unverified. This limits confidence but does not invalidate the whole memo. It is distinct from omitting available research or claiming it does not exist.

## What Improved

### Independent Judgment Is Present

The independent ideal has five positive exposures: 65% diversified equities, 25% Treasuries and 10% cash, split into specific equity and bond categories. The current-aware proposal has ten positive exposures; the final portfolio has sixteen. These are genuinely different portfolios, not a requirement to copy the investor's list of asset classes.

The final recommendation retains substantial scarcity exposure while introducing broader equities, nominal duration, bullion and liquidity. It does not automatically endorse every play. That independence is desirable; inadequate research is not.

### Sector Reasoning Is More Specific

- Oil: physical supply disruption, inventory depletion, forecast recovery and the difference between upstream and refining earnings now enter the discussion. This is much better than drawing an oil conclusion chiefly from a short price range and one bank forecast.
- Silver: the memo now discusses a physical deficit, industrial demand, photovoltaic thrifting and supply response. The earlier recovery described the physical balance as unresearched.
- Gold miners: realized prices, sustaining costs, cash generation and operating/jurisdiction risks replace some generic miner-versus-bullion discussion. The upstream evidence is richer, even though current valuations and the actual held-company mix remain incomplete.
- Fertiliser: it recognizes that disrupted shipments do not automatically translate into producer profits; feedstock, product mix, freight, affordability and valuation matter. It differentiates commodity prices from producer equities.
- Rates: it no longer equates the nominal yield-curve spread with term premium or Fed projections with market-implied expectations. It acknowledges missing matched-maturity evidence instead of manufacturing a precise breakeven calculation.

### Arithmetic And Treatment Of Unknowns Improved

Sixteen final targets total 100%. The deterministic funding ledger reports consistent funding and 33.4108% one-way turnover. The smaller-change alternative is also balanced to displayed precision, with 17.3914% one-way turnover. No final fact references are missing from the saved ledger or alias map, versus three unresolved IDs in September 21.

Small positions without adequate coverage are generally retained for review, rather than treated as automatic sales merely because they are absent from the ideal. The memo acknowledges unknown tax lots, base currency and constituents. It correctly labels weights as judgments rather than optimized estimates.

## Material Findings

### P1: Retrieved Uranium Research Does Not Reach The Final Allocation

The final memo says no uranium supply, contracting, cost or valuation evidence was supplied. That is false as a description of the saved research.

There are 24 uranium-related observations, including production, reactor requirements, utility inventories, contracting, Kazatomprom guidance and a Cameco valuation observation. Not all are source-verified or sufficient to establish a five-year return case. Their existence nevertheless makes "no evidence" an incorrect conclusion.

The actual dispatch receipts identify the handoff failure:

| Stage | All included facts | Uranium facts included | Uranium question state |
| --- | ---: | ---: | --- |
| Final allocation | 1,696 | **0** | Two older unanswered questions |
| Commentary | 1,697 | **24** | Old questions plus newer partial answer |

The newer answer, `question_0466cbfed3f81bca9221`, explicitly points to `question_ea1ad7f919b766a6e8d7` through `reuse_question_id`. It contains a useful discussion of primary production, inventories, contracts and the limits of the available balance. The final allocator receives the old unanswered question, but not this newer answer. The writer later receives the research but preserves the stale conclusion rather than correcting the allocation's account of available evidence.

The settlement path scopes evidence to changed cases and pending findings. This artifact demonstrates that the selected relationships do not reliably bring forward a later answer to an existing investment question. Sending 95.5% of the entire fact ledger still failed to include the relevant uranium evidence. More tokens or another generic review would not address this selection defect.

Receipt references: final `a1c23a972cde99f8af0eb64b41dc91263e012b475778621d844e0fcb4ca7187e`; commentary `269dfc9ac95b01a914ab623c7a2b9bc49f75ba318535365f5ab84befe9ecb397`.

### P1: Important Play Research Was Deferred

Three mining-services questions and the sovereign-fiscal/gold-versus-bonds question have `retrieval_status=deferred`, with the recorded reason: "Outside the remaining discovery allowance; saved analysis remains available."

These include funded mining capex, backlog, utilization, equipment/labour constraints, pricing and margins, plus sovereign debt, debt service, official Treasury demand and comparative hedge behaviour. A targeted search of the fact ledger found no mining-services operating observations for the requested play. Oil-and-gas services earnings are not a substitute for mining-services research.

This is a prioritization failure: material user plays were left outside the research allocation while the run accumulated 1,776 facts. It is not evidence that those plays are unattractive. The appropriate remedy is to prioritize these decision questions within the existing workload, not restore unlimited follow-up loops.

### P1: Scenario Comparison Does Not Compare The Independent Portfolio Adequately

All three common scenarios leave **90% of the independent ideal in the unknown category**. Only its 10% cash is mapped. The independent ideal's equity and Treasury names do not map to the exposure labels used in the final scenario definitions.

The recommendation table likewise labels diversified global equities "Different / not selected" in the independent ideal, although that ideal contains 65% equities divided between US and developed ex-US. The stored issue is `DIVERSIFIED_GLOBAL_EQUITIES: unresolved ideal exposure relationship`.

There is a legitimate difference between the precise instruments, but the display should distinguish a partially equivalent combination from no selected exposure. The current exact-name scenario comparison cannot support a claim that the final portfolio has been comprehensively tested against the independent ideal.

There are three qualitative regimes and no numeric portfolio return estimates. Qualitative analysis is legitimate. The failure is incomplete exposure mapping and insufficient comparison, not the absence of invented probabilities or precise forecasts.

### P2: The Long-Term Mandate Still Has A Short-Term Analytical Centre

High risk tolerance and 5+ years are present, and the memo does distinguish strategic intent from current concentration. Much of the decisive evidence nevertheless concerns 2026 earnings, a 2027 oil forecast and current yields. It lacks a sufficiently developed multi-year path from supply constraints through investment, capacity, margins, valuation and shareholder returns.

A high-risk mandate does not require keeping every concentrated position. But deciding to turn over about one-third of the portfolio requires a stronger explanation of the long-term trade-off than "30% is a risk cap" while 25% is also described as defensible. Gold and silver sizing similarly remains judgmental without enough quantified marginal-risk or opportunity-cost support.

The memo should compare a few explicit, assumption-labelled paths, including persistent disruption and a supply response, and show how the proposed changes behave. It should not pretend that a larger checklist or more source-verification calls supplies that reasoning.

### P2: Forecasts And Uncertainty Are Not Always Expressed Carefully

The oil case calls the premise "time-limited tightness" and treats the 2027 recovery forecast as changing the premise from open-ended scarcity. EIA does forecast recovery, but explicitly conditions it on increasing Hormuz flows and alternative routes. The source also warns its inputs stop on September 3. This is a scenario with assumptions, not proof that the disruption ends. The September 23 memo needs a clearer treatment of what happens if those assumptions fail. [EIA September STEO](https://www.eia.gov/outlooks/steo/)

Other wording deserves correction:

- Bullion does not provide the "same gold sensitivity" as gold miners; it shares a price driver without identical operating leverage or equity risk.
- "Cash gives no drawdown" is too absolute when currency and implementation are unspecified. Nominal balance stability is not the absence of real or FX risk.
- Giving a weak numerical play score because key research was not performed risks confusing investment merit with confidence. The latest schema separates some of these concepts, but the reader still sees 4/10 before discovering that a decisive part of the question was deferred.

### P2: Formatting And Reading Burden Regressed

The deployed frontend was tested against all four saved outputs at 1440px and 390px widths. API reads were fulfilled from the exact saved memo payloads; no writes or paid calls were permitted. Screenshots confirm that the legacy visual shell remains, but newer content fits it poorly.

| Memo | Default memo-panel words | Desktop panel height | Mobile panel height | Full Markdown words |
| --- | ---: | ---: | ---: | ---: |
| August | 4,231 | 8,343px | 17,579px | 4,607 |
| September 20 | 5,117 | 12,051px | 23,344px | 17,235 |
| September 21 | 4,770 | 13,122px | 24,216px | 21,334 |
| September 23 | 7,244 | 18,246px | 34,251px | 25,896 |

The latest default memo panel has 71% more words than August and is over twice as tall on desktop. These counts exclude the separate introductory summary panel. Supporting research is collapsed by default, which is good; expanding it makes the latest panel approximately 51,287px high on desktop.

Concrete reader defects:

- The large opening summary flattens line breaks into one paragraph and displays raw `**Oil:**` syntax and inline bullet separators.
- Multiple body lists collapse into a single bullet containing several `-` items.
- The opening summary and reconciliation section repeat the same allocation argument.
- Repeated unresolved-question lists interrupt the investment cases and plays instead of being consolidated in the supporting material.
- An internal `finding_d5efa41d60227de5` identifier reaches the visible investment case.
- "Provisional recommendation" and discussion of accepted findings survive in the finished presentation.

The measured memo panels have no horizontal overflow, no `[object Object]` artifacts and no browser page errors. The problems are content hierarchy, rendering and repetition, not a blank or crashing reader. The existing layout should be preserved and fed properly structured prose; another page redesign is unnecessary.

## Did It Debate The Plays?

Yes, but not completely. All six are addressed; only four have numerical parent scores, all provisional. All six parent verdicts are `needs_research`, including those partially reflected in the allocation. Those verdicts also appear in the model's recorded judgments, so this is not solely a UI relabelling issue.

| Play | Recorded score | Allocation treatment | Audit judgment |
| --- | ---: | --- | --- |
| Fertiliser | 4/10 | No new allocation | Better economic decomposition; current pricing and investable producer case unfinished. The producer leg itself is unscored. |
| Precious-metals miners | 5/10 | Gold miners 8%, silver miners 4%, both reduced | Genuine operating-cost and bullion comparison; current valuation and held-company mapping still incomplete. |
| Oil producers | 5/10 | Retained at 30%, reduced from 50.39% | Substantially better debate; concentration and thesis merit are more clearly separated, but forecast recovery receives too much certainty. |
| Uranium producers | Unscored | Existing 2.91% retained | Incomplete assessment, worsened by the proven evidence-handoff failure. |
| Mining services | Unscored | No new allocation | Not meaningfully researched; generic economic mechanism is not a completed evaluation. |
| Physical gold over bonds | 4/10 | Adds 4% bullion and 8% nominal Treasuries | Partly accepts bullion, rejects an exclusive gold hedge. Fiscal premise remains unresearched; the relative-preference leg is 3/10. |

It is reasonable to disagree with a play. It is not reasonable to present a missing investigation as a researched rejection. Neither more bullish conclusions nor greater agreement with the investor would, by itself, improve this audit score.

## Source Spot-Checks

This was not a fresh verification of every fact. A targeted primary-source check supports two important distinctions:

1. EIA's September STEO contains the approximately 400-million-barrel inventory depletion estimate and $74/bbl 2027 Brent forecast used by the memo. Its recovery assumptions must travel with that forecast; the source does not establish an unconditional endpoint to scarcity. [EIA](https://www.eia.gov/outlooks/steo/)
2. EIA's 2025 uranium report contains the 174 million pounds of maximum contracted deliveries, 186 million pounds of unfilled requirements, and 170 million pounds of year-end US commercial inventory present in the saved research. These are US-specific categories and periods, not a global future deficit. They confirm that relevant research existed and deserved qualified treatment rather than a claim of absence. [EIA uranium marketing report](https://www.eia.gov/uranium/marketing/)

The Silver Institute PDF could not be independently retrieved with the web tool in this pass. Silver's improved coverage is judged from the saved sources and observations, not represented as a newly source-certified conclusion.

## Operational Assessment

Completion was real: four successful new model calls, comprising final allocation, two changed investment-case batches and commentary. Their reported cost was US$13.713784, excluding earlier work. Three additional attempts received explicit temporary provider credit-reservation rejections before successful retry. The earlier three completed case batches were reused.

Efficiency remains poor. Those four successful calls consumed **3,203,891 input tokens**. Final allocation alone used 967,197 input tokens. The lossless encoding repair allowed this saved run to finish; it did not make the architecture efficient. A near-million-token input that omits the uranium evidence needed for the decision is a particularly clear demonstration that volume is not coverage.

No new paid analysis, application changes, model swaps or deployment were performed for this comparison.

## Priorities For The Next Improvement

**Superseded as an implementation queue:** the user's subsequent scope decision
makes plays supplementary, not a dedicated research mandate. Keep the empirical
findings below, but use the [current lean audit](portfolio-research-architecture-review-20260923.md#current-audit-a-smaller-evidence-to-memo-pipeline)
and [six-item active ledger](portfolio-architecture-remediation-ledger-20260920.md#active-queue-evidence-to-memo-simplification).
Prioritize material core investment questions within the existing budget;
introduce plays only at final synthesis. Missing play research must not block
the memo or generate its own follow-up programme.

| Priority | Change | Evidence of success | Avoid |
| --- | --- | --- | --- |
| 1 | Reconcile later answers to the original question and carry current play evidence into settlement. | The saved uranium case reaches final allocation with its observations, contradictions and remaining gaps; no stale "no evidence" conclusion. | Adding another generic reviewer or sending the entire archive. |
| 2 | Spend discovery allowance on unanswered material play questions before additional general coverage. | Every requested play has an actual researched answer or a clear, specific unresolved limit; mining services and fiscal risk are not silently displaced. | Unlimited follow-up or a full checklist per asset. |
| 3 | Map economically equivalent exposures across baseline and final portfolios. | US plus ex-US equity and Treasury components participate correctly in the same scenarios; unmapped weight is disclosed. | Inferring equivalence solely from fuzzy names or fabricating risk estimates. |
| 4 | Connect the 5+ year thesis to a small number of explicit investment paths and sizing trade-offs. | A reader can see why the proposed change is preferred to holding or making the smaller change under stated assumptions. | Another mandatory research/review layer. |
| 5 | Repair memo composition within the existing legacy layout. | Brief formatted executive view, one comparison, six concise play assessments, supporting research at the end; no raw Markdown or internal IDs. | Another wholesale UI redesign or truncating away substantive analysis. |

The highest-value next work is **using research already paid for, prioritizing the missing decisions, and improving composition**, not purchasing a larger generic investigation.

## Reproduction

Audit inputs and scripts: `outputs/audits/portfolio-finish-comparison-20260923/`.

- `reader-full.json`: production reader projection with structured evidence, decisions and receipts.
- `reader.json`: exact production `view=memo` payload.
- `audit.py`, `metrics.json`, `critical-findings.json`: deterministic content, references, funding and handoff checks.
- `browser.mjs`, `browser/metrics.json`, `browser/*-top.png`, `browser/latest-*-plays.png`, `browser/latest-*-commentary.png`: deployed-reader fixture comparison, including mobile screenshots.
- `latest.md`, `september21.md`, `september20.md`, `august.md`: extracted memo text.

Run `.venv/bin/python outputs/audits/portfolio-finish-comparison-20260923/audit.py` for the saved-artifact checks and `node outputs/audits/portfolio-finish-comparison-20260923/browser.mjs` for browser comparison. Assertions verify final weights, six plays and the 0-versus-24 uranium handoff. Browser snapshots are based on the deployed frontend at audit time; later deployments can change the rendering.

Related records: [finish-only recovery](portfolio-finish-only-recovery-20260923.md), [September 21 comparison](portfolio-final-comparison-and-concurrency-20260921.md), [architecture ledger](portfolio-architecture-remediation-ledger-20260920.md).
