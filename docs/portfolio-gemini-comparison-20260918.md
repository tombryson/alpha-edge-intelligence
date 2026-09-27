# Gemini 3.8 Flash Portfolio Comparison

Completed locally on 18 September 2026, approximately 17:26 AEST.
No deployment or persistent model-routing changes.

[Gemini memo](http://127.0.0.1:5194/portfolio-analysis?run_id=gemini-opus.json) |
[Ling/Opus memo](http://127.0.0.1:5194/portfolio-analysis?run_id=mixed-ling-opus.json) |
[Original DeepSeek-led memo](http://127.0.0.1:5194/portfolio-analysis?run_id=independent-live.json)

## Verdict

**Gemini was economical, structurally reliable and substantially shorter. It
did not improve financial reliability in this test.** I would retain the
Ling/Opus memo as the more useful document to read, while keeping its previously
documented financial errors visible. Neither should be accepted as validated
investment advice merely because the pipeline completed.

The clearest failure is unusually informative: Opus explicitly identified a
wrong healthcare earnings figure in Gemini's initial proposal. Gemini retained
it in provisional reconciliation, final reconciliation and the finished
commentary. Adding a capable reviewer is not sufficient when the synthesis can
ignore a concrete factual correction.

## Controls And Execution

Gemini handled the holdings-blind ideal, separately formed current-aware view,
exposure review, provisional and final reconciliation, three investment-case
batches and memo commentary. Opus handled the defensive review.

The original portfolio, initial analytical prompts, research cutoff and final
553-fact evidence bundle match both earlier same-day runs by hash. The ideal
was saved before current holdings were introduced; the current-aware request
did not see the ideal. No new Grok, Perplexity, Parallel, extraction or
source-check calls were made. New questions outside the saved bundle remain
unanswered. This compares analytical configurations, not fresh research quality.

There were 11 paid requests: nine Gemini requests and two Opus attempts for
one review. Opus's first response exhausted its separate 10,000-token reviewer
budget. Its saved partial output was retained; the normal retry at 20,000 tokens
completed. Initial allocations used the configured 32,000-token budget.
No manual format recovery or prompt rewrite was needed for Gemini.

Elapsed analysis time was about 11 minutes 22 seconds. All eleven requests
returned reported cost:

| Charge | USD |
| --- | ---: |
| Nine Gemini requests | $2.039287 |
| Completed Opus review | $1.732275 |
| Truncated first Opus attempt | $1.797675 |
| **Total analysis replay** | **$5.569237** |

The mixed replay's reported subtotal was $25.347115, with one additional
interrupted request unpriced. This is not a like-for-like model price benchmark:
that configuration gave Opus several major roles and incurred more repairs.
The original DeepSeek-led run's earlier audit recorded a $3.059837 OpenRouter
subtotal across retained recoveries, with different roles and work. None of
these figures includes a fresh common research run's full cost.

## Results

| Measure | DeepSeek-led | Ling/Opus | Gemini/Opus reviewer |
| --- | ---: | ---: | ---: |
| Independent / current-aware / final exposures | 11 / 8 / 12 | 12 / 13 / 14 | 7 / 10 / 9 |
| Model proposal total | 100% | 100% | 100% |
| App-assembled specified total | 121% | 100% | 100% |
| App funding check | Unresolved | Balanced | Unresolved cash mapping |
| Memo words | 15,355 | 18,677 | 9,712 |
| Retained investment cases | 12/12 | 9/14 | 9/9 |
| Final structured fact references | 69 | 63 | 64 |
| References missing from final evidence ledger | 16 | 19 | 11 |
| Resolving references without saved source checks | 7 | 11 | 19 |
| Valid machine-evaluable monitoring conditions | 0 | 0 | 0 |

All eleven missing Gemini fact IDs existed in the initial evidence packet.
They reflect the existing evidence-identity merge problem, not invented IDs.
The nineteen unchecked references also reflect this experiment's deliberate
reuse of the original checks rather than commissioning checks for new selections.
The monitoring contract and missing investor mandate remain common limitations.

Gemini's nine final targets are:

| Exposure | Target |
| --- | ---: |
| Cash and Treasury bills | 20% |
| TIPS | 15% |
| Short-dated sovereign and high-grade credit | 10% |
| Energy producers | 12% |
| Quality/value equities | 15% |
| AI and power infrastructure equities | 10% |
| Pharma/biotech | 8% |
| Gold producers | 5% |
| Diversified financials | 5% |

This is approximately 55% equities, 25% bonds and 20% cash/bills, versus the
mixed memo's 65% equities, 26% bonds and 9% cash. Energy is smaller than the
mixed memo's 16%; healthcare is 8% rather than 15%; it retains gold miners,
not bullion, and favours power infrastructure over a semiconductor allocation.
These are model proposals from frozen evidence, not trades executed by the app.
Final weights are identical to Gemini's provisional weights.

## Financial Assessment

### Improvements

- Genuine category independence: seven initial exposures, ten current-aware
  exposures and nine final exposures, rather than reproducing the current list.
- Clearer, shorter portfolio shape; all nine detailed investment cases survived
  normalization, unlike the mixed replay's loss of five usable cases.
- The concentration-versus-thesis distinction remains useful: a favourable
  energy view does not establish that half the portfolio should be in energy.
- Power infrastructure and semiconductors are treated as different economic
  exposures. The final proposal explains its preference rather than treating
  them as interchangeable labels.

### Material Weaknesses

1. **An explicitly corrected factual error survives.** The evidence identifies
   Health Care as the only sector with declining earnings; 52% is the blended
   index growth figure. Gemini's ideal attaches "-52%" to healthcare. Opus's
   accepted review flags the mismatch. The final writer nevertheless states
   "negative sector earnings momentum (-52% in Q2)". This is a synthesis failure,
   not missing retrieval or a parsing defect.
2. **Missing research becomes a sell argument.** Lithium, copper and other
   positions are labelled speculative or undesirable because they are small or
   lack coverage. Opus explicitly says missing evidence should prompt research,
   not rejection. Gemini still calls for liquidation. No minimum holding-size
   rule, position-level evidence or investor implementation policy supports it.
3. **Defensive characteristics are assumed.** The writer turns an unspecified
   Pharma/Biotech sleeve into large-cap, cash-generative defensive healthcare
   and calls unspecified mining holdings speculative or junior. Those holding
   characteristics are not established by the input's category labels.
4. **Nominal and real protection are overstated.** The prose repeatedly calls
   bills zero-duration and treats their current yield as a secure real return;
   its own detail table gives bills 0.25 years of duration. It also calls the
   sovereign/high-grade-credit combination risk-free in the summary. Nominal
   carry, inflation protection and credit risk are different properties.
5. **TIPS value is not demonstrated by mismatched horizons.** Comparing a
   ten-year breakeven with one recent CPI print or a single-year PCE forecast
   does not, by itself, establish mispricing. TIPS principal adjusts with CPI,
   but a 12-24 month investment still has mark-to-market exposure. The detail
   section admits real-duration risk; the finished prose overstates guarantees.
   [TreasuryDirect](https://www.treasurydirect.gov/marketable-securities/tips/),
   [Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds).
6. **Growth is substituted for expected investor return.** Utility rate-base
   expansion and banking revenue growth are presented as reasons to beat cash
   without a valuation, financing, dilution or sustainable return bridge.
7. **The concentration arithmetic mixes exposure categories.** The memo says
   precious-metal miners total 26.5%. The actual gold and silver sleeves total
   23.90%; adding uranium produces 26.48%. The broad mining concentration is
   real, but uranium should not be classified as precious-metal exposure.
8. **The prose is more categorical than the analysis.** Terms such as
   catastrophic, fatal and existential recur, while exact sizing lacks a
   quantified risk budget. Shorter is not the same as more disciplined.

Opus added useful challenge, particularly the earnings correction and criticism
of exits based on missing data. It is not an oracle: its accepted review also
endorses zero-duration real carry and uses overly categorical claims about
which assets protect in adverse regimes.

## Application Issues, Not Model Scores

The app retained Gemini's 20% `cash_and_tbills` target but left the separate
legacy `cash` row unspecified. It therefore reports "No final weight specified
for Cash" and leaves the allocation review unresolved even though the proposed
targets sum to 100%. This is the known exposure-mapping defect, not a model
omission. It was not silently repaired inside a controlled comparison.

The pipeline correctly preserved the memo and labelled it complete with
limitations. However, this label concerns execution and available fields, not
financial accuracy. No production settings, prompts or layout were changed.

## Decision

Gemini is a viable lower-cost analytical worker, but this sample does not
justify promoting it above the preferred Ling/Opus document on financial
quality. The priority is to make final synthesis resolve specific factual
corrections, repair exposure and evidence identity, and distinguish unanswered
research from a negative investment case. These changes should preserve useful
outputs and surface unresolved claims, not discard the memo.

The [Grok/Parallel audit](portfolio-grok-parallel-audit-20260918.md) remains the
retrieval recommendation. This replay changed analytical models, not retrieval.

## Verification

`gemini/comparison.json` records the control hashes, stage receipts, costs and
metrics. `gemini/requests/` retains every transport response, including the
truncated Opus attempt. Browser verification passed at 1440px and 390px in
light and dark themes, with no JavaScript errors or workspace overflow.
Saved artifact: `outputs/audits/portfolio-independent-uplift/live/gemini-opus.json`.
