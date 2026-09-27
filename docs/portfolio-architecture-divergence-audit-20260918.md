# Portfolio Memo Architecture: Historical Versus Current

Audit completed: 18 September 2026 AEST (17 September UTC). Read-only investigation of production artifacts, deployed source, local source and Git history. No analysis was rerun and no application code or production data was changed.

## Conclusion

The September integrity work changed the analytical product, not just its reliability. A range-led macro positioning memo became a fully funded allocation proposal with a fact-review system, implementation requirements and a different narrative contract. Some changes repair genuine faults. Others suppress useful model judgments or omit substantial analysis from the memo.

The most consequential findings are:

1. The new deterministic memo renderer omits many analytical sections that still exist in the saved output. It foregrounds a long list of unresolved checks instead.
2. Model thesis conviction is overwritten according to implementation and mandate completeness. In the latest completed run, 23 model ratings became UNASSESSED; the other two were already UNASSESSED.
3. Range-based actions and point-target trades now share the same action label, although they mean different things.
4. The allocator's instructions and available instruments changed. The outputs are not generated under the old investment brief.
5. Historical runs are re-evaluated using today's schema, which changes their displayed status and can conceal their original ratings without modifying the original JSON.
6. Much of the expanded workload checks fields rather than generating independent investment arguments. It does not establish that the resulting allocation is financially superior.

## Evidence And Timing

| Baseline | What was inspected |
| --- | --- |
| 25 April | Production `/data/jobs/portfolio_positioning_job_portfolio_positioning_20260425_133901.json`, plus its current API response |
| 11 August | Retained original `outputs/audits/portfolio-20260811/run.json` |
| Latest completed run | Production `/data/jobs/portfolio_positioning/portfolio_positioning_job_portfolio_recovery_20260917_121841.json` |
| Earlier code | `e7c555e` (20 April), `114ffb7` (28 April), `2de86fe` (8 September) |
| Current implementation | Deployed generation source and current working tree |

The April and August artifacts have no generation code manifest, so they cannot be attributed to an exact source revision with certainty. Their saved prompts and sections provide direct evidence of actual behavior. The large integrity rewrite is in the uncommitted working tree after `2de86fe`; the remediation record documents its initial verification on 15 September and subsequent changes on 16-17 September. There is no single clean commit identifying each deployed change.

The latest completed artifact is explicitly **workflow version 2**, with `complementary_roles`. It is not a version-one memo ensemble. Its 16 recorded generation-file hashes all match both deployed generation code and local generation files at audit time.

The memo-loading optimization from the previous task is local and not deployed. It changes read performance, not generation. It cannot explain the analytical divergences documented here.

## Architecture Before

### April

```text
Portfolio snapshot
    |
Grok macro/news + Tavily + Perplexity research
    |
Evidence brief / macro and commodity summaries
    |
Three allocator proposals
    |
Allocator comparison / judge
    |
Portfolio comparison commentary, directions and conviction
    |
Sectioned macro positioning memo
```

This was already structured generation followed by a deterministic Markdown renderer. It was not a single unrestricted chairman writing the entire document. The important difference was what the models were asked to produce and which of those fields the renderer included.

### August / Pre-Integrity Baseline

```text
Three research subjects: macro regime, sector leadership, coverage audit
    |
Grok + Tavily + Perplexity for each subject
    |
Three evidence briefs -> shared evidence reconciliation
    |
Three complete memo lanes in parallel
    |-- each: three allocators -> judge -> commentary -> memo
    |
Cross-memo synthesis -> final commentary -> sectioned memo
```

The August artifact contains three memo lanes and nine allocator outputs. The three strategies were macro-first, portfolio-aware and exposure-equivalence. Although the code defined a fourth defensive strategy, the three-model pool did not run it.

The memo lanes shared an evidence brief. Repetition across them was not three independent collections of evidence.

## Architecture Now

```text
Freeze snapshot and research cutoff; check provider funding
    |
Three research subjects
    |-- native Grok web/X research
    |-- Perplexity research
    |-- Parallel Ultra2x discovery / citation extraction for new retrievals
    |
Extract source-linked facts in document batches
    |
Review nine fields of each fact in eight-fact batches
    |
Reconcile evidence, preserving unresolved and contrary observations
    |
One genuinely blinded macro-first allocation
    |
Three complementary roles, each receiving the frozen macro prior
    |-- portfolio-aware allocator
    |-- exposure-equivalence reviewer
    |-- defensive-regime reviewer
    |
One provisional comparison
    |
Optional material-question research, reusing existing evidence first
    |
One final allocation synthesis
    |
Investment details for the selected allocation, four sleeves per batch
    |   (these responses cannot change weights)
    |
Deterministic funding / evidence / mandate assessment
    |
Commentary explaining the recorded decision, without changing ratings
    |
Rebuild decision rows -> render shortened memo -> save artifact/checkpoints
```

Source: `portfolio_positioning_memo.py`, especially `_query_stage`, `_run_pipeline`, `_run_allocator_commentary` and `_render_markdown`; `backend/portfolio_tasks.py`; `backend/portfolio_decisions.py`.

Version-one checkpoint recovery still retains the older repeated memo-lane path. New version-two runs avoid that repetition. The latest repaired version-two run reused its original successful Tavily retrievals and used Parallel for supplementary research; it is not a clean all-Parallel run. This preservation avoided paying to retrieve the same initial evidence again.

## Changes That Alter The Answer

| Dimension | Earlier behavior | Current behavior | Consequence |
| --- | --- | --- | --- |
| Investment brief | Macro-led allocation ranges and directional commentary | One 100% funded point portfolio, with cash and explicit treatment of existing sleeves | Moves from positioning guidance toward an implementation-ready portfolio contract |
| Range semantics | HOLD could mean the existing weight is acceptable inside the range | ADD/TRIM is determined by distance from the point target, with a 0.05 percentage-point threshold | A reasonable existing allocation can become a trade even without leaving the recommended range |
| Energy framing | Explicit language allowed 25-45% Energy under high-oil/tight-supply conditions and discouraged generic balanced-fund positioning | `_query_stage` removes those clauses, plus several taxonomy and regime heuristics | The old concentration-friendly prompt bias is gone; this is a policy change, not merely parsing cleanup |
| Asset vocabulary | Required mapping into supported parent buckets | Allows distinct instruments and exposures rather than forcing collapse | TIPS, long nominal government bonds and IG/HY credit can become separate recommendations |
| Macro-first role | Told not to anchor, but its saved prompt still included current portfolio weights and exposure baskets | Receives no current portfolio context; runs before other allocators | A genuine improvement in experimental isolation, but the initial recommendation can differ materially |
| Council | Repeated three-role memo ensembles | One macro-first plus three complementary roles | Less repeated allocation work; the defensive role now actually participates |
| Independence | Shared research and repeated prompts | Shared fact ledger, with later roles also seeing the macro prior | Neither design is independent external validation; the new design is deliberately sequential deliberation |
| Investment case | Commentary could assess directions and conviction | Details are added after final weights are selected; commentary must not change them | Missing or adverse detail can flag a proposal, but this step does not revise the funded allocation |
| Conviction | Commentary/model rating, with arithmetic defaults if missing | Rating survives only if per-sleeve checks and portfolio mandate requirements pass | Thesis confidence becomes entangled with implementation readiness |
| Failure behavior | Fallback prose/proposals and first-valid-lane selection could produce an apparently finished memo | Core retrieval, reconciliation, allocator and funding dependencies can stop completion; supplementary gaps now remain warnings | More honest failure reporting, but still a larger dependency surface than the earlier workflow |
| Final document | Broad macro, strategy, implementation and monitoring sections | Allocation, decision basis, outstanding checks, sources | Readable analysis is omitted even when present in the artifact |

The removal of hard-coded Energy sizing and keyword-based regime overrides is defensible. It should not be described as preserving the old analytical behavior: it explicitly changes it. The base prompts still contain older wording; `_query_stage` edits the effective prompts centrally, making the real contract harder to understand from the role functions alone.

## Direct Output Divergences

### 1. Ratings Are Being Replaced By Code

Latest raw allocator/synthesis ratings in `macro_positioning.asset_class_targets`:

| Rating | Raw proposal | Final structured memo |
| --- | ---: | ---: |
| STRONG | 2 | 0 |
| MEDIUM | 14 | 0 |
| WEAK | 7 | 0 |
| UNASSESSED | 2 | 25 |

`backend/portfolio_decisions.py:173` requires both no open verification questions and no mandate constraints before retaining a thesis rating. The latest snapshot contains an empty mandate. All seven mandate fields are missing. That alone is sufficient to suppress every rating, independently of the model's investment view.

Other checks also fail locally: every sleeve is marked as missing a substantiated market-pricing comparison and an established investment horizon. Those are legitimate things to investigate, but they are not equivalent to the model having no view on the thesis.

The commentary receives this already-downgraded decision and is instructed not to change conviction or status. Its saved summary says: "Directions, targets, conviction, and analysis status are unchanged." This is instruction-following language entering the memo, not additional market analysis.

### 2. A Saved HOLD Can Become A Current TRIM

April Energy example:

| Field | Value |
| --- | ---: |
| Current weight | 37.58% |
| Recommended range | 30-42% |
| Point target | 35% |
| Saved action | HOLD |
| Current recomputed decision action | TRIM |

The saved main allocation row still contains HOLD. The newly generated decision/review object contains TRIM. This demonstrates semantic inconsistency between the historical memo and its current assessment; it does not mean the stored April artifact was overwritten.

Source: `backend/portfolio_decisions.py:107`, plus read-time `decision_for_artifact`.

### 3. The Memo Omits Analysis That Was Generated

The April memo contains 17 second-level sections; August contains 16. The latest contains four:

- Allocation
- Decision basis
- Still to establish
- Sources

In the latest 32,297-character memo:

| Section | Characters |
| --- | ---: |
| Allocation | 1,555 |
| Decision basis | 5,198 |
| Still to establish | 11,358 |
| Sources | 13,125 |

The outstanding-check and source sections account for approximately **76% of the document by character count**. This is not 76% of model effort or a screen-area measurement.

The artifact still contains six monitoring triggers, five forecasts, seven implementation notes, eleven portfolio-level commentary items and twenty-five asset-level comments. `_render_markdown` does not include those collections. It also omits the old dedicated strategic, macro-scorecard, quadrant, commodity and broker-theme sections.

There is a second loss: after attaching asset-level commentary, `_run_pipeline` rebuilds `asset_class_targets` from the funding ledger at lines 2973-2974. That removes the attached row-level commentary from those final target rows, although the original comments remain in the separate `allocator_commentary` object.

Restoring the old frontend layout did not restore this generation contract. The new memo text was already missing the sections before it reached the browser.

### 4. The Allocation Universe And Recommendation Changed

| Output | April | August | Latest September |
| --- | ---: | ---: | ---: |
| Target sleeves | 7 | 16 | 25 |
| Energy / Energy Producers | 35% | 20% | 14% |
| Bonds | Not in target list | 18%, broad parent bucket | 12% governments, plus 8% TIPS, 2% long governments, 4% IG and 1% HY |
| Cash | Separate 15% strategic cash statement; not in target rows | 5% | 9.5% |
| Gold | 15%, legacy GOLD label | 8% miners + 6% physical | 4% miners + 6% physical |

These are recorded recommendations, not endorsed allocations. April's seven target rows total 98%, excluding the separate cash statement and unresolved treatment of other existing sleeves. That is a genuine old funding ambiguity. The latest final ledger totals 100% and reports 63.0431% one-way turnover.

The portfolios and research dates also changed. Current Energy was 37.58% in April, 33.66% in August and 50.73% in September. The allocation differences cannot be attributed solely to code or models without a controlled replay using the same snapshot, evidence and model assignments. No such paid replay was performed in this audit.

### 5. The Latest Consensus Contains An Internal Error

The saved synthesis says the blind macro prior had no energy-commodity allocation. Its saved proposal actually contains `ENERGYCOMMODITIES: 5%`. The current lane-summary function passes the full business proposal to synthesis, not just a top-N asset list.

This is a concrete example of an uncorrected comparison error surviving a large validation workload. Structured completeness and source-field review do not verify every narrative statement about the council's own proposals.

## Research And Workload

The latest completed artifact has **149 completed task receipts**, not 149 independent analysts or 149 newly issued requests during its final recovery:

| Work | Completed task records |
| --- | ---: |
| Retrieval | 14 |
| Fact extraction | 39 |
| Fact review | 73 |
| Evidence overviews | 6 |
| Evidence reconciliation | 2 |
| Allocators, comparison and synthesis | 6 |
| Follow-up planning | 1 |
| Investment-detail batches | 7 |
| Commentary | 1 |
| Total | 149 |

Fact extraction and review account for **112** of the 149 tasks. There are only six core allocation/comparison/synthesis tasks. The final recovery reports all 149 tasks reused and zero new model or research requests.

The retained evidence contains 570 fact records and 93 source-packet entries. Under the current support contract:

- 87 facts are supported.
- 416 are unresolved.
- 67 are unsupported.
- 347 fact reviews have an unresolved currency check; 250 have an unresolved publication-date check.
- 206 facts have an invalid publication date, including 205 with a missing date. These are overlapping counts, not additional facts.

All nine field checks must be supported, and the source/text/hash checks must pass, for a fact to count as supported. This makes metadata completeness influential in whether a fact can support conviction. It does **not** mean the other 483 facts were discarded: they remain in the evidence supplied to the allocators with their limitations.

The older artifacts did not use this fact schema. Their zero `facts` count must not be mistaken for zero research. August retained three evidence lanes and 24 source citations, but its evidence summaries/coverage had documented failures.

Current follow-up research is capped by material unanswered questions, not a search for every diagnostic item. This repaired run investigated post-FOMC expectations, oil-flow/Brent uncertainty and TIPS real yields/breakevens. It reused the original three Tavily retrievals; five Parallel Ultra2x task records covered follow-up searches and expansions. New initial discovery uses Parallel.

## Model Changes In The Audited Runs

| Assignment | August | Latest September |
| --- | --- | --- |
| Macro-first allocator | `openai/gpt-5.5` | `~deepseek/deepseek-flash-latest` |
| Portfolio-aware allocator | `google/gemini-3.1-pro-preview` | `google/gemini-3.8-flash` |
| Exposure-equivalence reviewer | `x-ai/grok-4.3` | `x-ai/grok-4.6` |
| Defensive reviewer | Did not run with the three-model pool | `~deepseek/deepseek-flash-latest` |
| Final synthesis | `openai/gpt-5.5`, but synthesis fell back | `~deepseek/deepseek-flash-latest` |
| Commentary | `openai/gpt-5.5` | `~deepseek/deepseek-flash-latest` |

April used `anthropic/claude-sonnet-4`, `google/gemini-3.1-pro-preview` and `x-ai/grok-4.1-fast`; commentary used the Anthropic model. Its saved artifacts label the three proposals `allocator_1/2/3`; the later named-role semantics should not be retroactively asserted for them.

Latest research receipts record native `grok-4.6`, Perplexity `openai/gpt-5.6-sol`, and Parallel `ultra2x` for follow-up discovery. The DeepSeek alias appears on 133 of 149 completed task receipts, spanning extraction, source review and central analytical/writing steps. That is a substantial concentration of responsibility, not 133 independent confirmations. Recorded aliases are not proof of a pinned immutable model release.

## Historical Display Reinterpretation

The April API still returns its original ratings: three STRONG, three MEDIUM and one WEAK. However:

1. `analysis_health` evaluates the historical artifact against the new decision contract.
2. No per-stage receipts is itself classified as an incomplete-analysis issue.
3. The April artifact also has real funding/context gaps under the new calculator.
4. `AllocationTable` renders every rating as UNASSESSED whenever health is not complete.

Consequently, a historical result can look as if the models never produced a rating, despite that rating remaining intact in its saved data. Historical provenance availability, original processing outcome, current investment suitability and model conviction should not be collapsed into one display status.

Sources: `backend/portfolio_decisions.py:227` and `:295`; `backend/routers/runs.py:202`; `frontend/src/components/PortfolioPositioningLab.jsx:167` and `:191`.

## What Should Be Kept Versus Reconsidered

**Keep:** retained raw outputs, checkpoint recovery, credit preflight, dated source references, distinguishing instruments, genuine macro blinding, explicit disagreement, optional-research failure containment, and funded arithmetic where an actionable portfolio is requested.

**Reconsider first:**

1. Restore the memo's analytical section contract independently of the frontend layout. Render the useful strategy, alternatives, implementation and monitoring work already generated; leave detailed validation in the appendix.
2. Preserve model thesis conviction separately from evidence verification and sizing/implementation readiness. Do not silently substitute one for another.
3. Make an explicit product choice between range-led positioning and an executable point portfolio. Both can coexist, but HOLD-within-range and trade-to-target need different fields.
4. Keep historical outputs faithful to their own schema and prompts. Add a separate contemporary review without rewriting their meaning.
5. Let material adverse findings in investment-detail work reopen the affected recommendation, rather than only attaching caveats after weights are frozen.
6. Concentrate further validation on financially material claim/proposal consistency, such as the incorrect energy-commodity comparison, instead of treating all metadata omissions as equal.
7. Preserve tests for the analytical deliverable, not only transport and shape. Current tests explicitly accept blanket UNASSESSED ratings and check that a generated memo has text; they do not require preservation of the original analytical sections.

This is not a recommendation to revert the entire pipeline. The August baseline had two empty/fallback macro-first proposals and a `fallback_first_valid` final synthesis. The old code could also default an ADD/TRIM to STRONG conviction merely because the current-to-target gap was at least ten percentage points. Its polished presentation did not mean the process had completed correctly. The appropriate direction is to retain the reliability repairs while restoring the intended analyst-facing behavior and separating research judgment from implementation checks.

## Verification Limits

- Production artifacts and generation hashes were inspected without writing to production.
- No paid research, model calls, replay, deployment or application-code edits were performed.
- Recorded economic statements were treated as outputs to compare, not independently verified market facts.
- This audit establishes specific architectural and semantic divergences. It does not establish that one portfolio would outperform another.
