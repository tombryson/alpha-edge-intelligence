# Independent Portfolio Architecture: Live Comparison

## Run Status

Live run started on 18 September 2026 at 01:08:38 UTC and finished at 04:10:34 UTC (11:08 to 14:10 Melbourne time), including disk-recovery interruptions. Final allocation and commentary are saved. **The release gate failed** on funding-ledger, citation-integrity, latency and reading-quality defects. The application's "Analysis complete with limitations" status describes retained output, not release approval or a funded trade plan. No deployment has been made.

- [Read the new live memo](http://127.0.0.1:5194/portfolio-analysis?run_id=independent-live.json)
- [Read the previous production memo](http://127.0.0.1:5194/portfolio-analysis?run_id=baseline.json)

These local links use the read-only preview; neither starts another analysis nor changes production data.

The run uses the latest completed production memo's saved portfolio snapshot, not the offline UI fixture. The prior artifact is `portfolio_positioning_job_portfolio_recovery_20260917_121841.json`, with a 17 September research cutoff. The new artifact is `outputs/audits/portfolio-independent-uplift/live/independent-live.json`.

The input has 12 held asset classes, a 48-category available universe, no individual positions, no company-research packets and no submitted investment plays. This is an asset-allocation comparison, not a company-level underwriting exercise. Missing investor mandate details remain missing.

Fresh neutral research was collected. Requested role models match the prior run, but evidence dates and prompts differ, and floating aliases can resolve differently. This is not an evidence-identical causal A/B test and does not establish investment performance.

## Verified Changes

| View | Previous run | New live run |
| --- | ---: | ---: |
| Macro-first proposal | 17 exposures | 11 exposures |
| Portfolio-aware proposal | 20 exposures | 8 exposures |
| Exposure reviewer | 19-exposure allocation | Critique, no additional allocation map |
| Defensive reviewer | 23-exposure allocation | Critique, no additional allocation map |
| Current holdings assessed | Existing workflow | All 12 |

The successful ideal-portfolio receipt precedes the holdings-aware request. The ideal input contains no current book, available-asset catalogue, company evidence or user plays. The holdings-aware request includes the book but excludes the ideal and plays. Both saved proposals total 100%. The initial ideal totalled 94%; the model repaired it, without software rescaling its weights.

Requested models:

- Independent ideal, defensive review, evidence processing, reconciliation and commentary: `~deepseek/deepseek-flash-latest`, resolving in the observed receipts to `deepseek/deepseek-v4.1-flash`.
- Current-portfolio assessment: `google/gemini-3.8-flash`.
- Exposure-equivalence review: `x-ai/grok-4.6`.
- Research: native `grok-4.6`, Perplexity `openai/gpt-5.6-sol`, and Parallel `ultra2x`.

## Initial Analytical Comparison

These are model proposals, not verified investment recommendations or an approved trade list.

The independent view chooses its own economic exposures, including AI/power infrastructure, quality/value equities and liquid alternatives. Its proposed oil-linked equity weight is 8%, versus 15% in the current-aware proposal. The latter assesses every existing exposure but proposes only eight allocations; it does not retain each existing category merely because it exists.

The exposure reviewer makes consequential distinctions: infrastructure/power is not interchangeable with semiconductor equity, quality/value is not equivalent to broad index beta, and bullion is not equivalent to miners. The defensive reviewer challenges TIPS duration risk, cash reinvestment risk and both views' vulnerability to a growth/inflation downturn. Final reconciliation retains these distinctions in its reasoning, but its weights remain unchanged from the provisional comparison.

Residual analytical concerns include proposed exits justified partly by missing evidence or small weights, despite no supplied minimum-position mandate; broad grouped exposures with potentially overlapping constituents; and a US-dollar-centric ideal without a supplied currency policy. These need interpretation, not automatic acceptance.

## Final Model Proposal

The final synthesis passed its response validator at 03:54:52 UTC, after three attempts. Its 12 model-selected targets total 100%:

| Exposure | Independent ideal | Final model proposal |
| --- | ---: | ---: |
| Cash and short-duration government debt | 20% | 20% |
| TIPS | 12% | 12% |
| Oil-linked equities | 8% | 8% |
| AI infrastructure and power | 11% | 11% |
| Quality/value defensive equities | 16% | 16% |
| Financials | 6% | 6% |
| Physical precious metals | 5% | 5% |
| Non-energy commodities | 2% | 2% |
| Broad US equity index | 12% | 11% |
| Intermediate investment-grade credit | 6% | 5% |
| Liquid alternatives/carry | 2% | 2% |
| Healthcare equities | Not separately selected | 2% |

The final weights are identical to the provisional comparison. The model largely adopts the independent portfolio, adds a small healthcare allocation and adopts the current-aware view's diagnosis of existing resource concentration. This demonstrates a genuinely separate starting view, but it does **not** demonstrate a substantive weight revision after the investment-case review. Whether the small weak-conviction sleeves improve the portfolio remains an analytical judgment, not a validated performance result.

Compared with the prior memo's 25 positive allocations, the new model chooses 12. The prior recommendation retained gold, silver, copper, uranium and lithium miners at a combined 8.5%; the new proposal exits those miner expressions and uses separate bullion/non-energy commodity exposures instead. Prior energy producers were 14%, with another 4% in energy commodities; the new proposal uses an 8% oil-linked equity sleeve without a separate direct-energy allocation. Prior pharma and healthcare services totalled 10%; the new healthcare sleeve is 2%. These are economically meaningful differences, but the broader renamed exposures are not all like-for-like instruments and must not be treated as mechanically interchangeable.

The analytical improvement is freedom to select an exposure structure and to explain departures from the existing book. Remaining weaknesses include near-total adoption of the ideal, weakly evidenced exits of small holdings, unresolved overlap between factor/sector sleeves, and confident allocation judgments despite missing currency, tax and horizon constraints. Fresh evidence also differs from the baseline; these differences cannot all be attributed to architecture.

The application then produces **25 ledger rows, including three duplicated positive exposures, with 121% specified weight**. Energy adds another 8%, healthcare another 2% and broad equity another 11% under current-book identifiers. The old cash row also lacks a final value. The financial proposal and its application ledger therefore disagree. The live artifact should be retained for analysis, but not treated as a funded trade plan or a passed release gate.

## Release Findings

1. **Research remains too large.** Initial discovery produced 133 unique citation URLs; the initial merged source packet had 138 source records, increasing to 155 after follow-up. Grok's coverage lane alone returned 95 citation entries. Initial source extraction required 40 model batches. The architecture has not yet solved upstream workload growth.
2. **Evidence prompts and outputs are excessive.** One consolidation request used 198,634 input tokens and exhausted 16,000 output tokens. Its retry returned 27,462 output tokens after about 14.5 minutes. The ideal request used 212,648 input tokens; a reviewer used approximately 229,000. Fact excerpts, research summaries and coverage narratives are repeatedly sent through downstream calls. Full evidence should remain stored, with a leaner analytical projection and concise reconciliation output.
3. **Reference checking assumes matching identifiers.** The provisional comparison tried to link differently named cash and energy exposures. The checker required null references because the identifiers differed, triggering a full-response repair. Subsequently the model also misstated two original ideal weights, which the checker correctly caught. Explicit source-exposure references and an economic-equivalence assessment are needed, rather than removing numerical checks or assuming string equality establishes equivalence.
4. **Forecast uncertainty is sent to search as a factual gap.** A follow-up asked whether official Q3 GDP would confirm GDPNow. Its expansion asked what BEA reported on 29 October, after the 18 September cutoff. Not-yet-released data belongs in monitoring; a current search cannot resolve it. The three-question budget alone does not prevent unnecessary work.
5. **Processing placeholders contaminate analysis.** Evidence consolidation echoed the supplied placeholder "Reconciliation incomplete; three research lanes retained unreconciled" despite completing a substantive consolidation. Pending system status should not be supplied as analytical evidence.
6. **Repair scope and progress reporting need work.** Reference-field errors lead to another full response, not a small targeted repair. During live follow-up research, the headline still said allocation comparison, while the active-request list correctly showed research. A failed earlier stage should not obscure the presently active phase.
7. **Open exposure names are not reconciled with the funding ledger.** Both provisional and final model target tables total 100%, but `funding_ledger` adds another 21 percentage points from existing energy, healthcare and broad-equity action rows under different identifiers. It reports 121%, plus an unspecified legacy cash row. These are not necessarily separate economic allocations. Preserve distinct instruments while explicitly linking current holdings, proposed exposures and replacements. Do not fix this with arbitrary label matching or proportional rescaling.
8. **Reviewers can misattribute the saved views.** The defensive reviewer says the independent ideal keeps 10% healthcare. The actual independent ideal has no standalone healthcare sleeve; the current-aware view has 10% `PHARMA_BIOTECH`. Structured reference checks do not catch this error in reviewer prose. The ideal's executive narrative also mentions healthcare without a corresponding explicit sleeve, so its own narrative/table consistency needs attention.
9. **Fact identities change during follow-up merging.** Eighty-one of the original 513 observations have the same substantive fields, source references and excerpt but different IDs after merging. `merge_briefs` derives IDs from a fingerprint containing `source_digest`; normalization recomputes that digest against the merged source packet. A subsequent merge therefore assigns another ID. References inside the merged brief are rewritten, but references in the saved ideal/current/reviewer outputs are not. Of their 93 distinct cited facts, 21 no longer match the final evidence ledger, including key monetary-policy claims. Only the remaining 72 reached selective source review. Stable observation identity must be separate from source-content/verification hashes, with explicit reference integrity tests across initial and supplementary merges. The raw observations have not been deleted.
10. **Internal citation IDs make the real prose harder to read.** The live browser preview exposes long `fact_...` identifiers repeatedly inside analytical paragraphs. The offline fixture did not exercise this density. Render readable, linked source references while retaining full internal IDs in provenance; do not redesign the page or strip attribution. The broader section structure is restored, but the real analytical text still needs this citation presentation work.
11. **Selective verification is not closed over the final recommendation.** The final synthesis cites 69 distinct facts. Sixteen references no longer resolve, and another seven resolve but were not source-checked. Checking only the provisional proposal's citations is insufficient when investment-case work or final synthesis can introduce additional claims. Review the newly cited material claims without repeating all research or discarding the memo.
12. **The renderer still exposes raw analytical packets.** `portfolio_memo.text()` flattens nested market/scorecard objects into long semicolon-delimited paragraphs. This repeats the same observations and leaks labels such as "UNASSESSED", "Evidence status" and "unreconciled" into the main narrative. The completed memo is 15,355 whitespace-delimited words versus 3,619 in the saved baseline, including tables and sources. More retained analysis is useful, but direct packet serialization is not a readable financial memo. Preserve the existing visual layout and render selected narrative fields with meaningful paragraph boundaries; keep provenance and schema diagnostics in the appendix.
13. **The writer adds unjustified certainty and comparison errors.** It describes the independent ideal and final recommendation as independently rejecting the existing configuration, although final synthesis explicitly receives the ideal. That is not independent confirmation. It also calls the final financials weight of 6% a middle position between 6% and 8%, when it simply equals the ideal. Assertions that zero cash is "indefensible on any reading" overstate a conclusion without an investor mandate. Commentary needs factual comparison checks and calibrated financial reasoning, not a more emphatic restatement of the chosen weights.

The run has already failed a reasonable latency expectation: approximately one hour elapsed before the independent allocator started. Passing offline tests is therefore insufficient for release approval.

The follow-up round extracted 40 additional facts, then reran full evidence consolidation with 219,095 input tokens and again exhausted a 16,000-token response limit. Focused searches must lead to focused evidence updates; otherwise the expensive whole-packet rewrite defeats the intended workload reduction.

That follow-up consolidation eventually completed at 03:22:59 UTC. Its second attempt alone took 22.6 minutes and returned 29,032 tokens. The first attempt took another 8.8 minutes. The run then selected 72 allocation-linked facts for nine review batches rather than reviewing all 553 extracted facts.

The 72 checks yield nine fully supported, 56 unresolved and seven unsupported records under the aggregate field contract. That does **not** mean only nine financial observations have supporting text: the narrower observation dimension is supported for 59, unresolved for 12 and unsupported for one. Examples of aggregate failures include an inappropriate USD field on a CPI percentage/calendar event, missing units on metal quotes, and release-date versus effective-date distinctions. The genuinely substantive observation mismatch is a source discussing general credit spreads that was labelled specifically as global high-yield spreads. Those are different limitations and must remain distinguishable downstream.

Final synthesis also exceeded 16,000 output tokens. Its first attempt sent 303,797 input tokens and took 12.9 minutes through Morph. A retry through Phala returned 15,868 tokens in 62 seconds but failed the identifier-based reference checks. Both resolved to the same DeepSeek model. Provider performance therefore contributes materially to latency, alongside the oversized prompts and repeated full-response generation; stage count alone does not explain runtime.

## Recovery And Verification

Primary-source spot checks during this audit, separate from the frozen model inputs:

- The [16 September Fed statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm) confirms the 25-basis-point hike and 3.75-4.00% target range.
- The [26 August BEA second estimate](https://www.bea.gov/news/2026/gdp-second-estimate-and-corporate-profits-2nd-quarter-2026) retains Q2 GDP growth at 1.5%, but revises private domestic final sales growth to 4.2% and core PCE inflation to 3.6%, both annualized. The second-estimate source and its unchanged headline are already in the saved research. The narrative nevertheless keeps foregrounding the advance estimate.
- The [Atlanta Fed GDPNow page](https://www.atlantafed.org/research-and-data/data/gdpnow) identifies 5.1% as a Q3 model nowcast, not an official GDP release. My analytical assessment: Q2 realized GDP and Q3 expected GDP are not conflicting measurements of the same quarter. The memo correctly acknowledges the distinction in places but repeatedly treats the difference itself as an unresolved contradiction. Same-quarter forecast comparisons, vintage changes and underlying demand would make a stronger growth argument.
- The [BEA release schedule](https://www.bea.gov/news/schedule/full) confirms that the Q3 advance estimate is scheduled for 29 October, after the frozen research cutoff.

This is a limited primary-source check, not independent verification of every retained market claim. These additional audit observations were not injected into the running pipeline.

A local `OSError: [Errno 28] No space left on device` interrupted coverage-lane aggregation. The downstream attempt was stopped and the checkpoint resumed. All nine initial research requests and 39 completed extraction batches were reused; only the empty extraction response was rerun. All 40 batches then completed, yielding 513 initial facts. One unavailable citation was also retried. No files were deleted during this first recovery; disk space recovered without intervention.

A second disk-full failure occurred after the final writing response was accepted in memory, before its receipt/cache could be persisted. The final allocation and all earlier accepted analysis remained saved. With explicit user approval, `npm cache clean --force` removed the downloadable cache and freed approximately 3.6 GB, without removing project files or installed dependencies. `finish_saved.py` reconstructs only the final writing request, whose full cache-key hash exactly matches the original request recorded in the log. It retains the frozen evidence, model assignments and cutoff, reuses the final allocation, and performs a request-level credit check. It does not rerun discovery, proposals, reviews or synthesis.

The recovered writing request completed in 171 seconds, with 275,595 input tokens, 4,876 output tokens and a reported OpenRouter cost of $0.061971. Hash comparisons confirm the evidence, research results, both initial views, reviews, provisional recommendation and investment details were unchanged. Exactly one new request receipt was added during this recovery.

Across both local attempts and this final recovery, 90 distinct retained model-request receipts and 20 research/retrieval receipts remain. Model receipts report $3.059837 in OpenRouter charges. This excludes xAI, Perplexity and Parallel charges and the lost original writer response, so it is not the total run bill. These counts are execution work, not 90 independent analysts. The current recovery's own workload summary is smaller because earlier work was reused; `request-audit.json` deduplicates receipts across the saved pre-recovery backup and final artifact.

The failure also exposes a persistence defect: `PortfolioRuntime.query.accept()` emits progress before durably saving the accepted response. A full output disk can make that log write fail first, losing the accepted response when the process exits. Accepted-result persistence must precede fallible progress reporting, and a secondary write-failure path must preserve the response where storage is available. The audit does not pretend that the lost original writing response was recovered.

There were also truncated model responses and an upstream Alibaba error reported by OpenRouter. Raw responses, failed attempts and completed work are retained. Individual source checks occur later; an extracted fact is not automatically an independently verified market fact.

The focused offline suite passed 94 tests during this live exercise. No submitted play was included, so live play scoring is not validated by this run. A controlled fixed-evidence comparison, user review and deployment approval remain separate gates.

The final real artifact and saved baseline both passed read-only Playwright checks at 1440px and 390px in light/dark themes: no page errors, memo content present, both new-architecture tables present, sources collapsed, and the portfolio workspace contained within the viewport. Screenshots were inspected. These functional checks do not override the narrative-quality and accounting defects above.

Audit inputs, checkpoints, receipts and read-only comparison utilities are under `outputs/audits/portfolio-independent-uplift/`. Provider credentials remained in process memory and were not written to the report or audit environment snapshot.

## Required Before Release

1. Preserve observation IDs across supplementary merges. Add an invariant that all existing proposal references still resolve, and review all materially cited claims rather than silently skipping orphaned references. Verification hashes may change without changing an observation's identity.
2. Add explicit current-to-proposed exposure relationships. Funding, comparisons and implementation must use the same relationships while keeping unlike instruments distinct. Assert a 100% funded result with no duplicated economic capital and separately recorded exits.
3. Keep full sources and excerpts in retained artifacts, but pass compact analytical evidence to allocators. Attach targeted supporting and contrary observations to investment-case batches. Replace whole-packet supplementary consolidation with a focused update.
4. Separate currently answerable research questions from future outcomes to monitor. Do not search for releases after the frozen research cutoff.
5. Repair the affected reference fields only and preserve valid prose/weights. Check quoted proposal figures and reviewer attributions against the saved views, without conflating investment disagreement with malformed output.
6. Give active work priority in the progress headline. Establish per-phase latency expectations and overall request deadlines, retaining partial results when optional work exceeds them.
7. Persist accepted responses before progress reporting. Check local storage headroom and preserve a separate emergency response record when the normal artifact/checkpoint save fails.
8. Close source review over final material citations, including newly introduced observations. Do not conflate an unresolved source check with a false financial claim.
9. Use editorial narrative fields in the main reader, with readable linked citations. Keep structured source packets and system statuses inspectable in the appendix without serializing them into prose.

These are findings from the exercised build, not changes silently applied during the experiment. The active pipeline code has not been modified for this test.
