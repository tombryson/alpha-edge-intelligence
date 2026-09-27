# Portfolio model benchmark: protocol

Status: protocol frozen before paid requests, 23 September 2026.

## Scope

Six exact OpenRouter models, two cases each, one sample per case. No production
configuration changes, fresh retrieval, automatic retries, or full memo rerun.

- openai/gpt-6-luna-pro
- openai/gpt-6-luna
- openai/gpt-6-sol-pro
- openai/gpt-6-sol
- xiaomi/mimo-v2.6-pro
- deepseek/deepseek-v4.1-flash

Cases use the saved September 21 r360 partial memo's source excerpts and historical
portfolio, with high risk tolerance and a 5+ year horizon. Old recommendations,
overlays, model opinions and asset-class targets are excluded. This is a closed
evidence test, not validation that retrieved excerpts accurately reproduce the
publishers' original documents or current market conditions.

Oil: physical scarcity, recovery scenarios, producer economics, valuation and
portfolio concentration. Gold/bonds: fiscal risk, nominal versus real yields,
inflation breakevens, duration, currency and hedge implementation.

All models receive identical messages per case, recorded and hashed. Source text
is preserved in full for the selected sources. There is no output token ceiling
in our request. The requested 700-1100 word decision note is a presentation target,
not truncation. OpenAI and DeepSeek use medium reasoning; MiMo uses enabled
reasoning with its provider default. These are not equal-compute settings.

Each request has a durable intent and independent streamed result. Concurrency
is two. No client-side retry, fallback to another model, repair call or paid judge.
Ambiguous failures remain unresolved until inspected; rerunning the command does
not resubmit an existing intent. Provider routing, actual resolved model, finish
reason, usage, billed cost, first-content latency and total latency are retained.

## Scoring, Fixed Before Outputs

Each dimension is scored 0-10; weighted total is reported out of 10.

| Dimension | Weight | What earns credit |
| --- | ---: | --- |
| Evidence fidelity | 25% | Correct attribution, dates, units, source independence; no invented facts |
| Financial reasoning | 25% | Correct causal and valuation mechanisms; distinguishes thesis from return |
| Decision usefulness | 20% | Clear conditional action, relevant to mandate; practical change triggers |
| Counterarguments and uncertainty | 15% | Strong opposing case, honest unknowns, no false precision |
| Quantitative consistency | 10% | Correct arithmetic, comparable definitions, no unsupported sizing maths |
| Readability | 5% | Clear recommendation and structure without repetitive generic caveats |

Anchors: 9-10 exceptional and no material errors; 7-8 useful with small omissions;
5-6 mixed, requiring substantial analyst review; 3-4 materially flawed; 0-2 unusable.
Missing optional facts do not automatically lose points; decision-relevant omissions
do. Critical unsupported claims, invented citations and material arithmetic mistakes
are listed separately and preclude an unqualified production recommendation.

Responses are randomly labelled per case. Scores and reasons are saved before
opening the identity map. This reduces identity bias; a single assistant evaluator
is not an independent expert panel. Cost/speed are reported separately, not folded
into financial quality. Two cases and one draw cannot establish a universal ranking.

## Factual and Reasoning Checklist

### Oil

- IEA supply 100.7 mb/d and demand 102.4 imply a conditional annual-average
  balance, not an observed daily September deficit. Do not subtract year-on-year
  changes to fabricate a level balance.
- August inventory draw 95 million barrels / 31 days is about 3.06 mb/d. Component
  changes -65 -52 +23 = -94 million, consistent with rounded -95, not every region
  drawing. OECD commercial inventory rose while government inventory fell.
- IEA, IEF reproducing IEA, and a secondary source citing IEA are not three
  independent confirmations. IEA/EIA/OPEC demand forecasts disagree materially.
- The IEF narrative itself has quarterly spread numbers inconsistent with its
  table (e.g. Q3 106.3 - 102.5 = 3.8, not 4.2); do not blindly echo them.
- Distinguish observations, estimates and forecasts, including the 2027 supply
  rebound and conditional recovery. Shut-in capacity is not usable spare capacity.
- Scarcity may benefit unaffected producers but not automatically disrupted
  operators, all energy equities, or buyers at any price. Consider volumes,
  realized prices, hedging, operating costs, capex, taxes and balance sheets.
- No company valuation, costs, forward curve or five-year return distribution is
  supplied. Do not invent fair value, target returns or a precise optimal weight.
- The 33.6635% energy-producer weight is a concentration question separate from
  whether the physical thesis is correct. High risk does not dictate either sale
  or purchase; distinguish a short disruption from a 5+ year investment case.
- Any stress loss or funding example needs its assumptions and correct percentage
  point basis, and must not claim statistical optimization.

### Gold, Nominal Bonds and TIPS

- Recorded 10-year nominal 5.01 minus real 2.68 = 2.33 percentage points. This is
  approximate breakeven compensation, not a guaranteed return or pure forecast.
- Current CPI, projected PCE, 10-year breakeven and 5y5y forward inflation measure
  different horizons/baskets. Current inflation above breakeven does not establish
  decade-long TIPS outperformance.
- Nominal duration suffers when yields rise but can hedge disinflation/recession.
  TIPS retain real-duration risk and are not equivalent to inflation-proof cash.
- A held-to-maturity USD real yield is not a guaranteed home-currency return;
  currency, tax and liquidity requirements are missing from the saved mandate.
- Gross OECD issuance includes refinancing; about 18 trillion gross versus about
  4 trillion net are different concepts. Stable auction demand is material
  counterevidence to a blanket confidence-collapse assertion.
- IMF excerpt has headerless debt ratio sequences. Do not invent year labels or
  precise dated debt ratios from them.
- Gold has no contractual yield, has real-rate/USD opportunity cost and can be
  volatile. Mining equities are not physical gold and should not be counted as an
  equivalent defensive hedge.
- July gold commentary is older than September rates. Current valuation and a
  decisive forward return comparison are not established by the packet.
- A defensible recommendation may add physical gold while retaining a role for
  nominal bonds/TIPS. Do not force this conclusion; justify any alternative.

## Artifacts

`outputs/audits/portfolio-six-model-benchmark-20260923/` contains immutable inputs,
catalog and funding snapshots, per-request receipts/results, blinded notes, grades,
and the eventual comparison. Credentials are never written there.
