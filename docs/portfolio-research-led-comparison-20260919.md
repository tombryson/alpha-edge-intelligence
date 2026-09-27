# Research-led portfolio run: comparison and audit

## Verdict

**Better retrieval, but not yet a better finished memo.** The latest run stopped before reviewer completion and reconciliation. It has substantial saved research and two funded proposals, not a final portfolio recommendation or completed play debate. Calling it a successful end-to-end improvement would be misleading.

The 11 August artifact remains the strongest reading experience. The preceding completed remediation run remains the strongest of these production artifacts for explicit review and traceability, despite its documented financial errors. The latest research-led build is promising but has not passed its live comparison gate.

## Scope and status

- Latest job: `aad10f66-3ad0-413f-a977-2da7d9429506`.
- Artifact: `portfolio_positioning_job_portfolio_recovery_20260919_090032.json`, workflow 4.
- Started 19 September 2026, 19:00:32 Melbourne; stopped 21:04:37 after 2h04m05s.
- Production job remains `failed`; saved artifact is `awaiting_credit`. OpenRouter requested additional credit. This does not establish the current account balance or mean the balance was literally zero.
- Independent ideal and current-aware assessment are saved. No final `macro_positioning`, completed analytical reviews or final play assessments are present.
- This recovery reused three Perplexity results from the earlier attempt. Its successful Parallel research used `ultra2x`.

Read-only audit of the production status, saved artifact, provider receipts, deployed reader and implementation. No paid analysis, recovery, deployment or application-code changes were made. Relevant local source hashes match the artifact's recorded code manifest. Source spot checks are not a re-verification of all 477 observations.

Latest and preceding production runs use the same portfolio snapshot and submitted plays, but fresh research, different market cutoffs and different successful provider participation. The legacy and model-replay comparisons are document-quality comparisons, not controlled forecasts or investment-performance tests.

## Scores

Subjective scores out of 10. Overall quality is not a simple average: unsupported conclusions, incomplete funding and internal contradictions matter disproportionately. Completed-run scores retain the previous audit's findings; incomplete analysis is not compared as though it had received its planned reviews.

| Artifact | Readability | Formatting | Financial analysis | Overall quality |
| --- | ---: | ---: | ---: | ---: |
| Legacy August | 8 | 8 | 6.5 | 7 |
| Completed remediation, 19 September | 4 | 5 | 7 | 6.5 |
| Ling/Opus replay | 6 | 5 | 7 | 6 |
| Previous production, 18 September | 4 | 5 | 6 | 5.5 |
| Legacy April | 8 | 8 | 5 | 5.5 |
| Latest research-led run | Not yet rateable | Not yet rateable | 6, provisional | Incomplete |

The latest provisional 6 applies to the saved allocator proposals, not a final reviewed memo. I would rate its research relevance and breadth around **7.5/10**: a clear improvement on the immediately preceding run's failed supplementary research, but not a measure of verified accuracy. Missing producer economics, noisy verification and uneven question coverage prevent a higher score.

August wins as an analyst document, not as a verified portfolio engine. April's readability does not excuse its 98% target table and inconsistent separate cash discussion. The Ling/Opus replay has connected financial reasoning but broken evidence references and other issues recorded in its earlier audit.

## What improved

| Measure | Completed remediation | Latest partial run |
| --- | ---: | ---: |
| Evidence observations | 304 | 477 |
| Source-packet entries | 46 | 98 |
| Independent positive allocations | 12 | 12 |
| Current-aware positive allocations | 17 | 21 |
| Final positive allocations | 20 | None yet |
| Independent/current weight totals | 100% / 100% | 100% / 100% |
| Unresolvable references in either saved baseline | 0 | 0 |
| Completed financial reviewers | 2 | 0 |

The new question-led research genuinely obtains decision-relevant material. Oil research includes supply disruption, inventories, usable spare capacity, export routing and divergent demand forecasts. Fertiliser research distinguishes nitrogen, phosphate and potash, including gas exposure, producer results and margins. Equity research distinguishes earnings-revision events from distinct-company breadth. Inflation research separates realized CPI, PCE and different forecast horizons.

These are substantive improvements, not just a longer source list. The independent view also remains separate from the current portfolio: 12 versus 21 exposures, each funded to 100%. It is not mechanically forced to mirror the 17 existing categories. However, 21 current-aware allocations still suggest fragmentation rather than decisive prioritisation.

## Where the process still fails

### 1. Better oil evidence does not reach the allocation argument adequately

The saved current-aware proposal cuts energy producers from 33.7% to 6%. Its cited rationale emphasizes a three-session WTI decline, easing supply anxiety and possible normalization. The independent proposal also allocates 6% and describes an unwinding risk premium.

**Neither energy target's explicit fact-reference list includes any of the 33 observations extracted by the focused oil-research task**, after accounting for fact aliases. This does not prove the model never read them; it does establish that the recommendation does not trace its reasoning to the new research.

The retrieved [IEA September report](https://www.iea.org/reports/oil-market-report-september-2026) reports over 10 mb/d of Gulf output shut in, a 95-million-barrel August inventory draw and continuing severe product-market disruption. Its normalization outlook is deferred into 2027. Those findings require explicit reconciliation with any near-term supply-normalization argument.

Concentration reduction can still be sensible. A bullish physical oil outlook also does not automatically make every producer cheap or justify a 33.7% portfolio position. The missing work is the bridge from disrupted supply to producer cash flows, costs, hedges, valuation and an appropriately sized exposure. Neither a falling spot price nor a high spot price settles that question.

The implementation appends focused facts but preserves the earlier brief's narrative fields. That is a plausible contributor to stale framing, not proof of the model's internal reasoning: [research merge](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:2922).

### 2. A literal numeric check weakens legitimate evidence

The source excerpt says inventories plunged by 95 million barrels; the extracted change is correctly signed as `-95`. The verifier compares the numeric value with literal numbers in the excerpt and flags the negative value because the excerpt contains positive `95` attached to a decline verb. The same issue affects `-507`, `-65` and `-52` inventory changes.

The facts remain saved. However, the coverage checker treats this verification issue as disqualifying and marks associated answer dimensions unresolved. This is not evidence that the primary source lacks those observations. See [numeric matching](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_evidence.py:161) and [coverage classification](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_research.py:73).

The remedy is explicit direction/unit/derivation handling, not accepting every absolute-value match. A sign must remain supported by context.

### 3. Partial answers are not preserved and reused reliably

There were 14 successful Parallel tasks: three initial and eleven focused tasks. Three focused tasks revisit previously searched equity-valuation, credit-spread and equity-breadth-expansion subjects in the current-aware phase. These are new searches, not transport retries or necessarily byte-identical prompts. Some may add useful evidence, but the planner does not consistently restrict them to genuinely missing dimensions.

The reuse check promotes a previous question only when every required dimension is answered. A later planned/deferred version then overwrites the earlier question state. For example, oil is saved as partially answered after successful research, then appears as deferred in the final question registry while still carrying substantive answers. The aggregate says zero fully answered out of 27; it must not be read as zero useful research.

See [reuse policy](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:2839) and [question-state replacement](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:2924). Same-label later research also replaces the earlier lane entry in the partial artifact, although immutable receipts remain saved.

### 4. The research packet overwhelms the reviewers

Ling's first attempt rejected structured-output support. Its fallback attempt was then rejected because **296,409 input tokens exceeded its 262,144-token context window**. These are provider-recorded numbers, not estimates.

Opus received **377,463 input tokens**, generated 32,000 output tokens and stopped with `finish_reason=length`; no complete JSON review was received. The subsequent recovery/retry path encountered the credit block. The raw response remains in the receipt store, but there is no completed review in the saved memo.

Both review prompts are roughly 900,000 JSON characters. The compacted evidence alone still includes roughly 539,000 characters of facts and 87,000 characters of question records, plus source metadata, duplicated narrative structures and both full proposals. The review prompt sends the whole analysis brief rather than a decision-focused packet: [review input](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_independent.py:199).

This is not solved solely by topping up credit or changing models. Preserve the full research ledger, but supply material decision evidence, contrary observations, concise question states and referenced source excerpts to each review. Split review responsibilities into bounded decision groups where needed and retain successful groups independently. Do not indiscriminately truncate research or remove all output budgeting.

### 5. The intended play debate has not happened

Both submitted plays remain saved. The play planner omitted `play_components`; each play has an unresolved inventory with zero components. The supplementary play research covered fertiliser, including an expansion. The gold-miner, silver-miner, oil-producer-economics, uranium and gold-versus-bonds questions remain deferred in this phase.

There are no completed play scores, Include/Watch/Reject decisions or final funding changes. The presence of oil or gold in the earlier independent proposal is not acceptance of a user play, because those proposals precede the play debate by design. Missing research is not a researched rejection.

### 6. Financial reasoning still needs an effective challenge

The independent TIPS section says realized core CPI of 2.4% and a forward breakeven of 2.21% are both below target. Neither is below 2%; moreover, the [Fed's target is defined in PCE terms](https://www.federalreserve.gov/faqs/economy_14400.htm), so different indices and horizons require qualification.

The proposal also uses broad-market valuation to support a selected AI/quality-growth sleeve without establishing that sleeve's valuation, and expands insurance partly through a generic positive-curve argument rather than insurer-specific economics. No individual holdings were supplied, which limits defensible operating-stage, hedging and producer-cost conclusions. These are exactly the kinds of gaps the missing reviewers needed to challenge.

## Readability and presentation

I rendered the original saved memo text, unchanged, through the deployed frontend at 1440px and 390px. API responses were intercepted with read-only artifact fixtures; no analysis was started. This compares the current reader's presentation, not historical JavaScript bundles. Live-job panels were excluded from the layout measurement.

There were no JavaScript errors or horizontal memo-panel overflow. The new supporting-research accordion and shorter paragraphs are genuinely better. The longest rendered research paragraph is 100 words, versus 1,570 in the preceding completed remediation memo. August's longest paragraph is 192 words.

But the latest default memo body contains only **22 visible words**, mostly headings and a stale "analysis is in progress" statement. Reconciliation and implementation are empty. Expanding research exposes about 6,779 rendered words, over 15,000 desktop pixels or 31,000 mobile pixels. It contains the proposals, but not a final argument or allocation table.

The shorter default page is therefore not evidence of a concise successful memo. A useful partial view should show the saved proposals and an accurate incomplete state without presenting empty final sections. The legacy August document remains more coherent: conclusion, current shape, strategic differences, readable allocation tables and implementation form an actual investment argument.

## Priority order

1. Preserve and reuse answered dimensions; do not overwrite partial research with deferred states. Fix signed-change verification and research-state reporting.
2. Require each material allocation to reconcile decisive supportive and contrary research, while refreshing stale market-summary assumptions. Demand producer economics before a producer-specific valuation verdict.
3. Build decision-focused reviewer packets, retain partial review work and recover the saved run without repeating successful retrieval. Additional funds alone do not fix the Ling context rejection.
4. Repair and freeze the submitted play components, research only the missing material premises and keep thesis merit distinct from portfolio fit and sizing.
5. Complete reconciliation, then assess the actual final memo. Preserve the improved paragraph structure and research accordion; use the legacy document's selective reading order.

These are repairs to the current architecture, not a case for another general-purpose agent or another layer of generic debate.

## Audit files

Artifacts, extracted memos, reproducible inspectors, screenshots and browser measurements are under [the local audit directory](/Users/Toms_Macbook/Projects/llm-council/outputs/audits/portfolio-research-led-review-20260919). Prior completed-run analysis is in [the preceding comparison](/Users/Toms_Macbook/Projects/llm-council/docs/portfolio-remediation-comparison-20260919.md).
