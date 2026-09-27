# Portfolio Analysis: Three-Generation Comparison

Audit date: 18 September 2026. Read-only review of saved outputs, request records and source code. No new model calls, deployments or application changes were made for this comparison.

## Judgment

**The new architecture is the best foundation, but it has not yet produced the best complete product.** It restores a genuinely independent investment view and a separately formed assessment of the current portfolio. Its final accounting, evidence references, reconciliation and reading quality are not yet reliable enough.

There are three different winners:

1. **Architecture worth developing:** new independent workflow, previous September workflow, legacy workflow.
2. **Memo usefulness as a document to read:** legacy, new independent, previous September.
3. **Funding arithmetic in the inspected outputs:** previous September wins. Both the primary legacy example and new application ledger have material inconsistencies.

I would retain the new analytical sequence, recover the legacy editorial discipline, and preserve the previous workflow's working accounting and evaluation contracts. I would not roll everything back, nor describe the new run as a passed release gate.

## Scope And Fairness

| Generation | Primary artifact | Cross-check |
| --- | --- | --- |
| Legacy | 25 April, `portfolio_positioning_job_portfolio_positioning_20260425_133901.json` | Adjacent April run ending `135740.json`, plus 11 August saved run |
| Previous | 17 September, `portfolio_positioning_job_portfolio_recovery_20260917_121841.json`, workflow 2 | Original proposals, research, task receipts and generation audit |
| New | 18 September, `independent-live.json`, workflow 3 | Both initial views, reviews, provisional/final proposals, recovery records and current code |

The two September runs have identical saved `portfolio_context` hashes: 12 held asset classes, a 48-category available universe, no individual positions and no submitted plays. They do not contain a completed investor mandate. The new ideal does not receive that holdings catalogue.

The September runs use the same requested role models, but different research cutoffs, fresh evidence, different prompts and floating model aliases. April and August also have different portfolios and model assignments. This is an audit of actual outputs and architectural mechanisms, **not a controlled causal A/B experiment or an investment-performance backtest**.

The April artifacts do not have an exact generation-code manifest. Saved content establishes what they produced; nearby historical code does not prove the exact deployed revision. August's saved prompts provide stronger evidence about its input leakage.

The completed new run used the original 16,000-token starting budgets. The subsequent change to 32,000 has not been tested in another live run. It cannot be credited with improving the runtime reported here.

The assessment covers objectives and constraints, investment arguments, portfolio construction, implementation and monitoring, consistent with the scope described in [CFA Institute's portfolio-planning framework](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/basics-of-portfolio-planning-and-construction). The scores below are my judgments of these artifacts, not CFA ratings.

## What Actually Changed

### Legacy: Market View, Then Positioning Memo

```text
Grok / Tavily / Perplexity research
  -> evidence brief and macro themes
  -> three allocator proposals
  -> judge / comparison
  -> current-versus-ideal commentary
  -> sectioned memo with ranges, conviction and monitoring
```

The April memo reads like an analyst's positioning note: market regime, commodity context, broker themes, preferred exposures, treatment of current holdings and conditions that could change the view.

However, an instruction to think independently is not input isolation. By August, the supposedly blind allocator received current weights and exposure baskets. The August architecture also expanded into three complete memo councils with nine allocator outputs, followed by cross-memo synthesis. Shared research and repeated councils did not create nine independent information sources.

### Previous September: Evidence Review And A Funded Proposal

```text
Frozen inputs and credit checks
  -> three research subjects across providers
  -> fact extraction, full fact review and reconciliation
  -> macro-first proposal
  -> three other allocator/reviewer proposals, seeing the macro prior
  -> provisional comparison and supplementary research
  -> final allocation
  -> investment details AFTER weights are chosen
  -> funding / mandate / evidence checks
  -> shortened memo dominated by checks and sources
```

This substantially improves provenance and recovery. It also changes the product: investment detail is added after the weights are set, implementation completeness suppresses thesis ratings, and the renderer omits analysis that was actually generated.

The macro-first model does not see current weights directly, but its research and opportunity context are still influenced by the existing portfolio. The other roles then see its proposal. This is deliberation, not two separately formed starting views.

### New: Two Separate Views, Then Challenge And Reconciliation

```text
Holdings-independent research
  -> independent ideal, saved before holdings are revealed
  -> separate current-portfolio assessment, blind to that ideal
  -> exposure and defensive critiques
  -> provisional reconciliation
  -> focused supplementary research and selected source checks
  -> investment-case work BEFORE final reconciliation
  -> final recommendation and analytical commentary
  -> existing funding / reader infrastructure
```

The central design is better. The integration with existing funding, evidence and evaluation code is not finished. Several defects arise precisely where the new, freely named exposures enter old identifier-based machinery.

## Rankings

Scores are ordinal judgments out of 10: 1-2 materially broken or absent; 3-4 weak; 5-6 useful with important limitations; 7-8 strong but incomplete; 9-10 unusually strong and demonstrated. A one-point difference is not statistical precision. Legacy scores use April as the primary document and August to test architectural claims.

| Dimension | Legacy | Previous | New | Main reason |
| --- | ---: | ---: | ---: | --- |
| Independence from existing holdings | 2 | 5 | **9** | New ideal input excludes holdings, catalogue, company packets and plays; current assessment separately excludes the ideal. |
| Freedom to choose economic exposures | 3 | 6 | **8** | New proposals select their own structures instead of filling existing categories. |
| Assessment of the current book | 5 | 6 | **7** | All 12 current exposures receive an assessment; assessment no longer implies retention. |
| Macro reasoning and causal argument | 5 | **6** | **6** | More evidence and qualifications, but regime labels still substitute for parts of the causal argument. |
| Pricing, expectations and investable edge | 3 | 4 | **5** | New detail comes before final synthesis, but attractive themes are still insufficiently separated from attractive prices. |
| Instrument and exposure distinctions | 3 | 7 | **8** | Better separation of bullion/miners, nominal/real duration and AI power/semiconductors. |
| Challenge and contrary evidence | 4 | 5 | **7** | Dedicated critiques are more useful than requiring every reviewer to emit another portfolio. |
| Faithful comparison and reconciliation | 4 | **5** | 4 | New comparison loses all current-aware numeric references and contains attribution errors. |
| Portfolio risk and sizing justification | 3 | **4** | **4** | None demonstrates adequate quantified hold-versus-change scenario and marginal-risk analysis. |
| Respect for supplied investor constraints | 2 | **5** | 3 | New neutral projection drops supplied tax and hedge policies; actual test mandate is empty. |
| Source traceability and verification | 3 | **6** | 5 | Previous has two unresolved final IDs; new has 16, plus seven resolving but unchecked citations. |
| Data vintage and benchmark comparability | 3 | **5** | **5** | New records more context but still misinterprets some different-period observations as conflicts. |
| Funding arithmetic and accounting | 2 | **8** | 2 | Previous ledger is 100%; new model proposal is 100% but application ledger becomes 121%. |
| Range-based positioning versus required trade | **7** | 3 | 6 | Legacy can HOLD inside a range; new restores the conceptual distinction but mapping remains defective. |
| Preservation of model conviction | 6 | 1 | **7** | Previous turns every displayed rating into UNASSESSED; new retains its 12 proposal ratings. |
| Readability and analytical structure | **8** | 2 | 4 | Legacy has a coherent reader-facing sequence; new restores sections but serializes too much raw material. |
| Signal relative to document volume | **8** | 3 | 2 | New is 15,355 words with repeated packets and internal IDs. |
| Machine-usable monitoring | 2 | **6** | 2 | Previous has six typed conditions; new triggers omit a required age field and skip evaluation. |
| Checkpoint recovery and inspectability | 2 | **7** | 6 | New preserves most work, but accepted writer output was lost when a progress write hit disk-full. |
| Diversity of model judgment | **7** | 5 | 5 | Three families remain, but DeepSeek owns most September synthesis and processing roles. Shared evidence limits independence. |
| Future performance evaluation readiness | 1 | **5** | 2 | Previous retains a decision timestamp and five forecasts; new has neither. |

There is deliberately no averaged grand score. A readable memo cannot compensate mathematically for an invalid capital ledger. Equally, passing a schema check does not establish a good investment thesis.

## Measured Output Differences

| Measure | Legacy April | Previous September | New September |
| --- | ---: | ---: | ---: |
| Memo words, whitespace count | 2,652 | 3,619 | 15,355 |
| Second-level sections | 17 | 4 | 15 |
| Model-selected target exposures | 7 | 25 | 12 |
| Structured allocation rows | 7 | 25 | 25 |
| Specified structured target total | 98%, plus separate 15% cash statement | 100% | 121% |
| Retained fact-ledger records | No comparable schema | 570 | 553 |
| Distinct URLs in memo | 12 | 84 | 149 |
| Final proposal fact references | No comparable schema | 49 | 69 |
| Final references absent from evidence ledger | Not measurable | 2 | 16 |
| Displayed ratings on model target rows | 3 strong, 3 medium, 1 weak | All 25 unassessed | 1 strong, 7 medium, 4 weak |
| Typed monitoring conditions meeting basic evaluator fields | 0 | 6 | 0 |
| Dated forecasts | None in comparable contract | 5 | 0 |
| Saved decision timestamp | Absent | Present | Absent |

Zero legacy fact-ledger records does not mean zero research. April retained 12 Tavily and 12 Perplexity results; native Grok failed with an invalid-model HTTP 400. August retained 62 distinct research URLs and 20 Grok tool calls. Source count is coverage volume, not evidence quality or independent confirmation.

The adjacent April memo had 90% in targets plus 10% cash, so its basic total can reconcile. It used a different portfolio input and is not a same-input replication. The primary April funding fault is not proof every legacy memo had the same arithmetic fault.

## Findings That Matter Most

### 1. The Independence Improvement Is Real

The new ideal has 11 exposures totalling 100%. The current-aware proposal has eight totalling 100%, despite assessing all 12 held classes. Saved request order and input contents establish that the ideal came first and did not receive the current book, and that the current-aware request did not receive the ideal.

This directly addresses the concern that 20 existing categories automatically produce 20 recommended categories. Fewer categories alone would not prove independence; the saved input separation does.

However, both views share research, and the same DeepSeek assignment performs the ideal, defensive review and final synthesis. The final proposal is therefore not independent confirmation of the ideal.

### 2. The Final Answer Largely Adopts The Ideal

The final recommendation keeps all 11 ideal exposures, adds 2% healthcare, and funds it by reducing broad equity from 12% to 11% and IG credit from 6% to 5%. Its weights are identical to the provisional reconciliation.

That is not inherently wrong: synthesis need not average two portfolios. But it must show why it rejects the other view's material arguments. Current-aware energy was 15%, versus final 8%; TIPS was 15%, versus final 12%; healthcare was 10%, versus final 2%.

All 13 reconciliation rows have null `current_reference_pct`. The validator matches exact normalized identifiers rather than explicit economic relationships. Differently named comparable exposures therefore lose their comparison values. The writer also calls 6% a middle position between 6% and 8%, and the defensive review attributes the current-aware healthcare allocation to the ideal.

This is a material comparison defect, not cosmetic wording. The new architecture has separate minds at the start, but cannot yet consistently account for their disagreement at the end.

### 3. The Application Corrupts A Valid 100% Proposal

The new model-selected targets total 100%. Existing energy, healthcare and broad-equity action rows are added again under different identifiers, contributing another 8%, 2% and 11%. The structured ledger becomes 121%, with an old cash row also missing a final value.

This is an application mapping fault, not a model deliberately recommending 121% gross exposure. It must be repaired with explicit current-to-proposed exposure relationships, distinguishing replacements, partial overlaps and genuinely different instruments. Arbitrarily rescaling the answer or collapsing all similar labels would conceal the error.

Legacy has its own funding problem: the primary April table totals 98% while the strategy separately proposes 15% cash. August's targets total 100%, but separately retained current-only decisions create another 7.23% ambiguity. The previous September ledger is the strongest inspected funded representation.

### 4. More Research Has Not Yet Produced Proportionately Better Analysis

New evidence contains 553 facts. Eighty-one original observation IDs change after supplementary merging because identity incorporates a mutable source digest. Existing proposal references are not all rewritten. The final proposal contains 16 references that no longer resolve and seven additional references that resolve but were not source-reviewed.

The underlying observations remain retained; this is not evidence that they were fabricated or deleted. Nevertheless, the promised claim-to-source chain is broken.

The 72 selectively reviewed records contain only nine fully supported aggregate records, but 59 supported observation checks. Those are different measures: missing publication metadata, inappropriate currency fields and actual observation mismatches must not all become a claim that the financial evidence is false.

The previous workflow also has two unresolved final references. Its broader verification is therefore better in this comparison, not perfect.

### 5. The Financial Reasoning Still Stops Too Often At A Plausible Story

Legacy's clear prose contains overconfidence. It treats capital-expenditure growth as sufficient evidence for an equity allocation, makes sweeping statements about duration, and calls Treasury-bill carry a 4.3%+ real return while elsewhere describing only a small positive policy-rate-minus-inflation spread. The better writing does not make those judgments rigorous.

The new run improves instrument distinctions and contrary arguments, but has not resolved the main analytical gap: **what does today's price already imply, and what differentiated view justifies this weight instead of holding or cash?**

Examples requiring better underwriting, rather than more generic searches:

- AI/power at 11%: investment demand is documented, but the memo does not sufficiently connect valuations, expected cash flows, financing costs and risks to that precise weight.
- Bullion versus miners: the distinction is correct; the required return advantage and consequences for the actual current exposure remain insufficiently quantified.
- Small current positions: being small or weakly researched is not itself an investment reason to exit. No minimum-position policy was supplied.
- Quality/value, broad equity, financials and AI/power: names imply distinct sleeves, but the run does not demonstrate constituent or factor-level overlap control.
- Growth: realized Q2 GDP and a Q3 nowcast are different-period quantities, not necessarily contradictory measurements. More reconciliation text does not fix that analytical category error.

Neither September artifact demonstrates a usable quantified scenario comparison with supplied risk sensitivities. There is no defensible basis here to say the new target weights would outperform the old ones.

### 6. Monitoring And Evaluation Regressed

This comparison found defects additional to the initial live-run audit:

- All 15 new monitoring notes omit `max_age_days`, which the existing condition evaluator requires. Several also have no numeric threshold/operator. No evaluated `review_conditions` are saved by the new pipeline.
- The previous run has six typed conditions, although their actual statuses remain unassessed without matching observations. That is a working data contract, not proof that continuous monitoring is operating.
- New `PROPOSAL_SCHEMA` omits dated forecasts. The previous artifact has five; the new one has none.
- The new decision has no `decision_at`. The older pipeline stamps it in a shared tail that workflow 3 bypasses. The existing return-attribution validator rejects records without that decision origin.
- One new future-rate trigger uses an upper-bound threshold greater than 3.75% to represent another hike, while its own memo quotes the current upper bound as 4.00%. A later unchanged 4.00% decision would satisfy that condition. This is a rule-definition fault, not an observed live trigger firing.

These are not reasons to discard the memo. Preserve the research and judgment; repair the specific contracts and mark unavailable monitoring honestly.

### 7. Independence Must Not Mean Ignoring Investor Instructions

`CONSTRAINT_FIELDS` omits `tax_cost_policy` and `currency_hedge_policy`. A synthetic projection probe supplied those policies alongside AUD base currency; only base currency survived into the independent context.

The current-aware branch still receives the full mandate. The defect is specifically in the independent projection, not proof that every role ignores policies. The live snapshot's mandate is empty, so this is a latent architectural regression rather than an explanation of a supplied policy being breached in this run.

A holdings-blind ideal should remain aware of explicitly supplied constraints. Restore those fields without inventing constraints or requiring a large new questionnaire.

### 8. The Memo Became A Data Dump Again, In A Different Form

The previous memo lost the narrative: checks and sources occupy about 76% of its characters, while forecasts, monitoring and substantial commentary remain in the artifact but not the memo.

The new version restores the section structure but outputs 15,355 words. Nested evidence packets flatten into long semicolon-delimited text, repeated observations and internal `fact_...` IDs. The reader receives research-system serialization, not consistently edited investment prose.

The April note's useful editorial sequence should be retained: conclusion, macro mechanism, preferred portfolio, current-versus-ideal assessment, implementation and what changes the view. Source lineage, alternative outputs and diagnostics belong in the existing appendix. This does not require redesigning the interface again.

## Operations And Model Effects

| Item | What the evidence supports |
| --- | --- |
| Legacy reliability | August finished in 12m28s, but all three brief stages fell back, two judges fell back and cross-memo synthesis fell back. A completed memo was not proof every intended stage worked. |
| Previous workload | 149 retained completed tasks; 112 were fact extraction/review, not analysts. Its last recovery reused all 149. This does not measure a fresh-run bill or latency. |
| New workload | 90 distinct retained model-request receipts and 20 retrieval/research receipts across attempts. These are not directly comparable with task counts. |
| New duration | 3h2m including two local disk-full interruptions. Large prompts, provider latency and whole-response retries were additional material causes. |
| New known cost | $3.059837 of reported OpenRouter charges across retained receipts. Excludes other providers and the lost original writer response; not the total bill. |
| Recoverability | Earlier accepted analysis survived. One accepted writer response was lost because progress logging occurred before durable response persistence. |
| Budget change | Starting response budgets are now 32,000, after this run. That may avoid some truncation retries; it does not shrink 200k-300k input prompts or prove lower latency. |

April's allocator models were Claude Sonnet 4, Gemini 3.1 Pro Preview and Grok 4.1 Fast. August used GPT-5.5, Gemini 3.1 Pro Preview and Grok 4.3 for the three roles that actually ran.

Both September artifacts request DeepSeek Flash Latest for macro-first/defensive work, Gemini 3.8 Flash for current-aware allocation, and Grok 4.6 for exposure review. DeepSeek also performs much of the evidence processing, reconciliation and commentary. New retained receipts show the alias resolving to DeepSeek V4.1 Flash. Thus, differences between the two September outputs cannot be explained simply as replacing the allocator roster with stronger models.

There is insufficient comparable billing, fresh-run timing and failure-frequency evidence to rank total cost or operational uptime across generations. There are no comparable realized-return series, forecast outcomes or risk-adjusted performance results. Submitted-play scoring is implemented in the new contract but was not exercised: this run supplied zero plays.

## What To Preserve And What To Repair

Preserve from legacy: analytical section order, readable conviction, acceptable positioning ranges and distinction between the ideal and current holdings.

Preserve from previous: durable checkpoints, inspectable requests, funding checks, decision timestamps and typed evaluation contracts. Do not preserve rating erasure or diagnostic-first prose.

Preserve from new: neutral initial research, two separately formed views, open exposure selection, specialist critiques, investment cases before final reconciliation and explicit treatment of user ideas as hypotheses.

Priority repairs, without another general redesign:

1. Link current holdings, each proposal's exposures and final exposures explicitly. Use the same links for funding, comparisons and implementation. Retain distinctions where instruments differ.
2. Keep observation identity stable across source updates, validate every final material citation and review newly introduced material claims without repeating all research.
3. Restore decision timestamp, dated forecasts, monitoring schema/evaluation and supplied tax/hedge constraints in workflow 3.
4. Make the final reasoning answer the other view's strongest material objections. Check quoted weights and role attribution; do not force compromise weights.
5. Pass compact evidence projections, update only changed evidence, and repair affected fields rather than regenerating entire proposals.
6. Persist accepted responses before progress reporting. Give active phases accurate headlines and bounded request deadlines without deleting successful research.
7. Render editorial narrative instead of raw packets, preserving the existing visual layout and readable source links.

The most valuable next analytical improvement is not another generic agent. It is a **clear, testable investment disagreement**: what is priced in, what we believe instead, the instrument that expresses it, why changing the current book is worth the costs and risks, and the observation that would overturn that decision. The new sequence can support this. The present run only partially delivers it.

## Evidence And Reproduction

Comparison data and readable memo extracts: `outputs/audits/portfolio-independent-uplift/three-generation-comparison/`.

- `metrics.json`: counts, sections, targets, ratings, references and monitoring fields.
- `architecture-checks.json`: matching September inputs, unchanged provisional/final weights, null comparison references and constraint-projection probe.
- `compare_generations.py`, one directory above: read-only comparison utility. It reuses cached April artifacts, or fetches the named saved artifacts from Fly if missing. It does not run models.
- [Completed live-run audit](portfolio-independent-live-comparison-20260918.md): request counts, source-reference defects, recovery hashes and browser checks.
- [Historical architecture audit](portfolio-architecture-divergence-audit-20260918.md): earlier code, artifact and deployment comparison.
- `outputs/audits/portfolio-20260811/AUDIT.md`: August prompt leakage, fallback and financial-analysis findings.

Relevant current code: `backend/portfolio_independent.py` (input projection, proposal schema and reference matching), `backend/portfolio_decisions.py` (funding, condition evaluation and return attribution), `backend/portfolio_evidence.py` (fact identity), `backend/portfolio_memo.py` (packet-to-text rendering), and the workflow-3 versus workflow-2 tails in `portfolio_positioning_memo.py`. The mirrored runner under `scripts/` has the same implementation.

This audit records defects; it does not silently repair or deploy them. Preserve all three generations' outputs for comparison.
