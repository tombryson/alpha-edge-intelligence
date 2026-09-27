# Portfolio Decision Process: Proposed Remediation

Status: implemented on `codex/portfolio-decision-remediation`; not deployed.
See [build and verification record](portfolio-decision-remediation-build.md) for
the implementation, tests and remaining live evaluation. The historical memo
has not been regenerated or rewritten.
Based on the production run ending `20260918_111608.json` and its saved audit.
No new paid model calls are needed to produce this design.

## Core Decision

Retain independent research, the separately formed ideal and current-book
assessments, and the existing reviewer roles. Improve the evidence-to-decision
process between those views and the final memo. Do not add another full council
or require every model to generate another complete allocation.

The central distinction is between:

1. An attractive investment thesis or a useful hedge.
2. The best instrument/exposure for expressing it.
3. Its incremental value in this particular portfolio.
4. Whether a trade is justified now, after costs and constraints.

A strong commodity thesis can coexist with a recommendation to trim an
overweight producer position. A hedge can be valuable despite lower expected
standalone returns. A lack of research establishes neither a buy nor a sell.

## 1. Establish The Actual Investment Brief

The current run implicitly evaluates a highly concentrated resources portfolio
as though it should become a diversified whole-wealth allocation. That might
be appropriate, but the input does not establish it.

Store the investor's brief once in Trading Terminal and pass it through every
run: portfolio scope (whole portfolio or a dedicated sleeve), objective,
base currency, horizon, liquidity needs, risk limits and relevant tax/FX policy.
Prefill only from trusted, explicit settings; do not infer risk tolerance from
existing holdings. Explain unknowns without requiring a large questionnaire.

The independent allocator receives this brief, but never current weights,
the current category catalogue or submitted plays. Independence means freedom
from current-position anchoring, not freedom from the investor's objectives.
Preserve supplied tax and hedge policies currently omitted by
`CONSTRAINT_FIELDS` in `backend/portfolio_independent.py`.

When the brief is incomplete, continue with an illustrative investment view
and explain which sizing judgments are conditional. Do not silently replace a
resources mandate with a balanced-fund mandate or suppress the entire memo.

This follows the separation of objectives, constraints and implementation in
[CFA Institute's portfolio-planning framework](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/basics-of-portfolio-planning-and-construction).

## 2. Make Existing Reviews Decision-Specific

Keep DeepSeek on the two initial views and routine synthesis. Restore Ling for
financial mechanism, pricing and exposure analysis. Keep Opus for adverse
scenarios and critical review. These are proposed responsibilities, not proof
that any brand is intrinsically best; use the repaired run to evaluate them.

Both reviewers must represent the strongest supporting and opposing cases.
Ling should not be obliged to advocate and Opus should not be obliged to reject.
Separate factual corrections, investment disagreements and unanswered questions.
A schema-valid response alone does not count as a substantive review.

For each material recommendation or play, retain a small decision record:

- Thesis and purpose: return opportunity, hedge, liquidity, or another stated role.
- Mechanism and horizon: what must happen, who benefits, and through which cash
  flows or hedge payoff.
- Expression and pricing: actual instrument characteristics, implied expectations,
  valuation/cost assumptions, and alternatives.
- Supporting evidence, opposing evidence, unresolved questions and sources.
- Portfolio effect, action, sizing rationale and what would change the view.

Extend the existing play/review/allocation schemas rather than copying the full
record into every stage. Store it once under a stable identifier. Optional or
unknown fields remain explicit unknowns, not reasons to discard useful work.

Maintain one explained investment-case score out of 10 where it is assessable.
Keep confidence and portfolio action separate; do not average reviewer scores,
turn a score into a probability, or mechanically reduce it for missing metadata.
Unresearched is not equivalent to a neutral 5/10 or a negative conclusion.

## 3. Investigate Plays After The Independent Views Are Saved

Preserve each submitted play as the parent idea. Decompose bundled plays into
economically distinct legs inside the existing review batch, not one new agent
per commodity. The scarcity play needs separate fertiliser, gold-miner,
silver-miner, oil-producer and uranium-producer assessments.

For this run, research should address questions such as:

| Decision | Evidence capable of changing the answer |
| --- | --- |
| Fertiliser scarcity | Product-specific supply/export disruption, inventories, feedstock costs, producer margins and valuation. Higher output prices alone do not establish better margins. |
| Gold/silver miners versus bullion | Production, costs, capex, reserve quality, financial leverage and valuation; distinguish miners from metal and producers from developers. |
| Oil producers | Realised prices, hedging, costs, balance sheets, reinvestment and cash-flow sensitivity under scarcity and normalisation. |
| Uranium producers | Contract coverage/prices, production ramp reliability, supply response and financing; spot uranium alone is insufficient. |
| Gold versus sovereign bonds | The proposed adverse event, fiscal/term-premium evidence, real-rate and FX sensitivity, short/long duration, and the actual protection offered by each instrument. |

These are research directions, not factual conclusions about current markets
and not a permanent list limiting which investments the app may consider.

Gold as insurance against fiscal credibility loss should be judged against that
event, including its failure cases, not rejected merely because it yields less
than Treasury bills. A view that government debt is high still needs evidence
connecting debt dynamics, funding costs, investor behaviour and asset pricing.
Analyse growth, inflation, liquidity and sovereign-confidence shocks separately;
they need not favour the same hedge.

## 4. Allocate Research By Decision Impact

The present workflow takes only the provisional allocator's questions and
then truncates the list to three. A material reviewer or play question can
disappear before retrieval.

Build one deduplicated question queue from both views, both reviews and the
plays. Each candidate must state which decision changes under different
answers and why saved evidence does not answer it. Investor preferences and
missing JSON fields never become market searches.

Prioritise material unresolved choices, not source volume: large proposed
changes, distinguishing between rival expressions, and claims central to
accepting or rejecting a submitted idea. Do not invent numerical probabilities
or an apparent expected-value calculation merely to rank questions.

Use the existing machinery: Parallel ultra4x, short individual queries, five
initial results, deduplication, concurrent independent calls and per-question
checkpoints. Prefer direct primary data for identifiable official series and
filings; retain search for discovery and qualitative context. Count independent
underlying sources, not repeated copies through several providers.

Replace the universal three-question truncation with an explicit research
time/spend envelope and decision-based stop rule. Reuse evidence first. Expand
only for a surviving material question where another query is plausibly useful.
Reserve no automatic minimum number of calls per asset or play.

Successful retrieval does not mean a question is answered: record what was
resolved, what remains open, and whether it changes the recommendation. When
the budget is exhausted or retrieval fails, retain the memo and qualify only
the affected decision. An unresearched existing holding does not receive an
automatic HOLD either; material risks remain visible for review.

## 5. Separate Financial Arithmetic From Judgment

Compute weights, turnover, funding, copied baseline percentages and elementary
arithmetic in code. Do not ask models to reproduce them from memory in prose.

Extend existing evidence metadata with the economic measurement needed for
comparison: reference period, annualisation, forecast horizon, inflation index,
nominal/real basis, currency, series/instrument and source vintage. Apply
comparability checks to material comparisons and derived claims, not as a
mandatory checklist for every sentence.

Examples:

- A 3.75%-4.00% range has a computed 3.875% midpoint.
- A one-year PCE forecast and five-year CPI breakeven are different quantities;
  any investment inference must explain the bridge between them.
- Annualized quarterly GDP growth and full-year Q4/Q4 growth are not competing
  estimates of the same quantity.
- Nominal yield is not real return. Any conversion needs an explicitly identified,
  horizon-matched inflation assumption; holding-period price and FX effects are
  separate from yield.
- A trend strategy's behaviour requires its actual strategy assumptions, not an
  automatic label of convex or path-independent protection.

The [Federal Reserve's TIPS methodology](https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm)
and [risk-premium discussion](https://www.federalreserve.gov/econres/notes/feds-notes/tips-from-tips-update-and-discussions-20190521.html)
explain why breakevens are not a pure inflation forecast.

An incompatible comparison should produce a specific correction or uncertainty
attached to that claim. It must not delete the memo, zero the allocation, impose
arbitrary price bounds or forbid a novel investment idea.

## 6. Repair Identity And Reconciliation

Use stable observation IDs separate from versioned source content and review
fingerprints. New source extraction can invalidate a source check without
silently renaming the fact or breaking prior proposal citations. Preserve
aliases and lineage when importing historical artifacts.

Introduce explicit proposal-to-exposure relationships using stable IDs and
instrument attributes. Relations can express equivalent exposures, partial
overlap, substitutes or a new exposure. An alias is only appropriate for true
equivalence. Partial overlaps cannot each inherit the entire original weight.

This is an extensible mapping, not an approved-asset list. Unknown or novel
exposures remain intact. A model may propose a mapping with evidence; code
calculates the resulting comparison, and ambiguous relationships remain visible.
Cash labels should not erase a valid comparison. Shared gold sensitivity must
not collapse bullion and miners into the same instrument.

Add a disposition for each material reviewer finding: accepted, rebutted with
reasons, or unresolved. Correct factual mistakes downstream; do not require
agreement on investment opinions. If synthesis ignores a material correction,
request a targeted patch to the affected claim, not another complete portfolio.

The current code copies earlier investment details onto final rows by asset
key, even after final synthesis changes the recommendation. Version those
details by decision assumptions, not only label. Preserve reusable work but
reassess details made stale by changed expression, horizon, evidence or sizing.
Likewise, check newly introduced final citations/targets after synthesis;
reviewing only the pre-final selection misses additions such as bullion.

## 7. Distinguish Destination From Trade Plan

Keep the ideal allocation, the current-aware assessment and the chosen
destination visible. Separately explain which changes are justified now.
A target difference is not itself a trading signal.

Compare holding, a minimal-change alternative and the proposed allocation
under the same relevant scenarios and investor brief. Account for overlapping
factors, currencies, liquidity and trading/tax costs where known. Use the
existing `scenario_comparison` implementation before building another engine.

Scenario inputs must have sources or explicit assumptions and uncertainty
ranges. Do not fabricate covariance matrices, probabilities or sensitivity
coefficients to produce an impressive-looking optimization. Historical proxy
estimates are labelled proxies, not facts about unspecified holdings; terminal
scenario returns do not establish maximum drawdown.

If holding-level data is absent, remain at illustrative allocation level and
explain what cannot be established. Keep tax/cost assumptions explicit. Use
position ranges and policy-driven no-trade bands where supported, not arbitrary
universal turnover caps. A 62% turnover proposal should explain why smaller
changes do not achieve the objective; it is neither automatically prohibited
nor automatically justified by an ideal-weight gap.

This is consistent with [CFA Institute's treatment of allocation and rebalancing](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/principles-asset-allocation).

## 8. Make Delivery Reliable Without Another Council

- Negotiate JSON mode using actual model/provider support. Keep JSON mode and
  strict-schema support distinct. Normalise provider errors, handle the observed
  hyphenated message, retry the same model without an unsupported format option,
  and preserve raw text if structured extraction fails. Do not silently change
  models or treat a failed reviewer as an abstention supporting consensus.
- Record configured versus actually contributing models, provider, resolved
  model where available, attempts and substantive completion. Endpoint support
  differs: see [OpenRouter's documentation](https://openrouter.ai/docs/guides/features/structured-outputs).
- Give analysis stages concise, relevant evidence plus shared macro context and
  contrary evidence. Keep complete source packets archived and addressable. Do
  not replay the full evidence dump into every role or truncate away opponents.
- Use adequate supported output budgets, smaller independent work units and
  targeted repair to reduce repeated whole-response truncations. Budget choice
  should reflect output shape and observed usage, not a blanket 10k for reviews.
- Repair monitoring fields and preserve dated decisions for later evaluation.
  Missing monitoring metadata should disable only that automated condition.
- Render the settled decisions and prose through the established memo layout.
  Put provenance and diagnostics in the appendix. Show "Partly adopted: 4%
  physical gold; short-duration bonds retained" rather than an unexplained Watch.

## Implementation Order

| Pass | Existing ownership | Deliverable |
| --- | --- | --- |
| A: Correctness and preservation | `portfolio_runtime.py`, `portfolio_evidence.py`, `portfolio_independent.py`, `portfolio_decisions.py` | Ling compatibility, stable facts, explicit comparison mappings, no destructive validation or double counting. |
| B: Investment reasoning | Existing review/reconciliation prompts and `_run_targeted_research` | Separate play legs, material question queue, correction dispositions and decision-specific final checks. |
| C: Suitability and sizing | Trading Terminal context, independent context, scenario/funding helpers | Persistent brief, destination versus justified changes, comparable scenarios and cost assumptions. |
| D: Reader and evaluation | Existing memo renderer and audit fixtures | Clear play outcome, concise analysis, appendix details, monitoring and controlled comparison report. |

Keep changes additive and backward compatible with saved memos. No general
frontend redesign, new agent framework, full-pipeline rewrite or new mandatory
research service is required.

## Verification And Repair Of This Run

Use the existing artifact as a regression fixture before spending on a replay.
Test the observed failures, including hyphenated provider errors, cash aliases,
gold/miner non-equivalence, immutable fact references and a final target changed
after its detail assessment. Assert that unrelated completed work survives.

Add financial comparison fixtures for GDP periods, nominal/real carry, CPI/PCE
horizons, hedge-versus-return objectives and decisions based only on missing
research. Semantic tests inspect explanations as well as schema completion.
Use human/blinded review of difficult judgments; another LLM is not ground truth.

Verify input isolation with hashes and leakage tests. The ideal must not change
because plays were added later. Preserve baseline outputs and factual errata;
do not overwrite them and claim the revised view remained holdings-blind.

Then run a separately authorised, bounded repair: recover Ling, research the
decision-relevant gaps, refresh affected reviews/details, and reconcile/write
the result. Reuse frozen initial research and both starting views. Preserve the
original run and compare with a linked new artifact. Newly retrieved evidence
must have an appropriate historical vintage for the original cutoff; otherwise
label the exercise an updated analysis, not a controlled replay.

Measure improvement by faithful use of both baselines, explicit treatment of
each play leg, correction survival, justified changes, funding correctness,
evidence resolution, reader usefulness, cost and runtime. Do not reward agreeing
with the user's plays, selecting a preferred number of assets, or changing all
weights. Later, track dated forecasts and shadow portfolio outcomes against
holding and an appropriate benchmark; one persuasive memo is not proof of alpha.

## Success Criterion

The reader can understand what the system believes, what would prove it wrong,
how the evidence changed its mind, and why a proposed portfolio change is
worthwhile. Where it cannot reach a sound conclusion, it preserves the work
and states the precise unresolved decision instead of manufacturing confidence.
