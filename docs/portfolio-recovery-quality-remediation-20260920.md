# Portfolio recovery and decision-quality repairs

## Status

Deployed from `codex/final-migration-hardening` to Fly.io as release **355** on 20 September 2026. No paid analysis, model reassignment or modification of the saved production memos was performed. This addresses the engineering findings in `portfolio-deepseek-recovery-comparison-20260920.md`; a subsequent live comparison is still needed to establish whether the financial conclusions improve.

Deployment verification: readiness check passing; all 25 portfolio/research manifest files match the local tested code; public JavaScript and CSS assets match the tested frontend build; all runtime model assignments match the pre-deployment snapshot; both audited production artifacts retain their pre-deployment SHA-256 hashes. The saved-memo list returns 27 reports, the latest memo endpoint loads successfully, and no portfolio analysis was started.

## Research recovery

- Restore focused research records and phase reports from `partial_artifact` on checkpoint resume, alongside provider task identities and expenditure reservations. Do not restore the aggregate later-phase evidence into the independent allocator.
- Retain the historical lane archive as well as the latest keyed lane result. Older checkpoints overwrote some question keys between phases; their earlier source observations remain in `evidence_runs` and must not disappear.
- New source records carry an explicit phase. For older records, use the phases where retrieval actually occurred, not every later appearance of the question. If a key was overwritten across multiple phases, admit it at the latest possible phase. Unknown provenance is withheld until the challenge phase, rather than guessed to be independent.
- Restore observations, citations and dimension-specific answers before the research planner. Revalidate their source references; an earlier price narrative cannot silently displace later physical-market evidence.
- Match exact question identities and explicitly declared reuse IDs within the same region, observation period and horizon. Preserve distinct financial concepts and different scopes. Only genuinely new unanswered dimensions request discovery.
- Resume failed extraction from already purchased source text without repeating the discovery call. Retain partial answers on later failure or deferral.
- Do not divide a remaining affordable task into unusable fractional phase allowances. The total run allowance is unchanged. Report carried expenditure and reused observations together.

### Saved-run regression

The interrupted production artifact was serialized into both supported checkpoint forms and resumed through the runtime and question-research path with discovery disabled. The larger saved-run regression uses the actual archived business data in a record-store checkpoint, rather than pretending an in-memory merge tests resume.

| Information boundary | Observations available | Source entries |
| --- | ---: | ---: |
| Initial research | 274 | 48 |
| Independent research restored | 329 | 63 |
| Current-portfolio research restored | 402 | 88 |
| Play research restored | 477 | 98 |

All 33 observations from the saved oil-balance lane are available before independent allocation. All 75 unique fertiliser observations become available at the plays boundary, not earlier. All 203 observations missing from the failed handoff are retained downstream. No provider request was made in this regression. Ambiguous older overwritten lanes are conservatively introduced later; new phase-labelled records do not have this ambiguity.

## Evidence comparison

Source matching now normalizes presentation: HTML entities and common text tags, Markdown escapes, inline emphasis and table separators. It does not alter numeric magnitudes, signs, units, benchmark identities or dates. Raw excerpts and source digests remain intact, with a recorded normalization method.

This fixes escaped decimals such as `0\\.9610` without accepting `0.962` as the same observation. The saved warnings are refreshed selectively; publication-date gaps, reviewer disagreements and actual source mismatches survive. A retrieved term-premium level does not establish its complete causal decomposition.

## Decisions and accounting

The existing allocators and reviewer now distinguish action basis (investment, risk, mandate or liquidity) from evidence status. Missing research alone is not an action basis. This is symmetric for additions and sales; neither forced retention nor a mechanical sell rule is introduced. Explicit research-gap trades remain under review, and the existing scoped reconsideration can revisit them without discarding the proposal.

The current-book packet explicitly includes the real cash identifier and balance, even when cash was previously supplied only as a portfolio aggregate. A proposed cash/T-bill sleeve must be identified as liquidity, and an instrument switch must explicitly dispose of the old cash balance. Renaming an instrument is not evidence of equivalence, particularly across currencies.

Unresolved cash accounting and invalid holdings relationships enter the existing scoped repair even if the prose reviewer misses them. A scoped response can correct cash disposition and the smaller-change alternative while leaving unrelated exposures unchanged. Both alternatives are checked against the actual book. Invalid repairs preserve the prior analysis and report the affected issue; weights are never silently normalized or invented to force 100%.

The saved 17% liquidity case and the overfunded smaller-change case pass offline accounting regressions after an explicit, fixture-supplied cash-transfer decision. This demonstrates the repair mechanism; it is not a new model judgment, execution instruction or retrospective alteration of the saved run. The unmodified historical memo still has its original unresolved accounting.

## Financial consistency and plays

The existing final reviewer now receives compact structured baseline allocations, the original cash balance, funded comparisons and computed calculation counts. This makes the independent baseline's 10% Treasury-note position and the eight unresolved calculations directly inspectable.

The contract distinguishes TIPS-versus-nominals from TIPS-versus-rolling-cash, bullion carry from miner distributions, and Brent from WTI. It specifies the appropriate calculation operations and requires unresolved arithmetic to remain qualified. These are reviewer inputs, not a claim that deterministic software can prove every prose investment inference.

Explained model scores remain visible as provisional when critical research is incomplete; evidence confidence and component-specific gaps are shown separately. One incomplete leg does not null every other component or the whole explained judgment. Missing assessments and unexplained placeholder scores are not manufactured into neutral ratings. Relative preference for gold over bonds is not reinterpreted as an exclusive allocation or a short-bond instruction.

## Reader

- Render nested macro scorecards through their human-readable assessments instead of `[object Object]`.
- Replace generated recovery labels with a dated portfolio memo title; preserve custom titles.
- Identify retained/provisional scores accurately, group repeated research-question headings, and remove internal question IDs from newly rendered prose.
- Preserve the legacy page composition, light and dark themes, and collapsed supporting research.
- Version the derived read cache for the title change. Completed saved memo text remains untouched by the normal read API.

The local read-only preview at `http://127.0.0.1:5194/portfolio-analysis?run_id=completed.json` renders the existing structured decisions with the updated presentation in memory. It is not a rerun or a corrected investment recommendation.

## Verification

Focused regressions cover checkpoint round trips (inline and record-store), phase separation, the actual interrupted artifact, paid-source extraction recovery, question reuse, wrong-number rejection, cash disposition, bounded alternative repair, action-basis review and recorded baseline/count inputs. The portfolio/source unit suite and production frontend build are run alongside browser checks across desktop/tablet/mobile and both themes, plus the partial and legacy readers.

Final results: **412 unit tests passed**, **14 browser theme/viewport/reader combinations passed**, frontend production build passed, and `git diff --check` passed. The build retains its existing bundle-size warning; the unit suite reports third-party SWIG deprecation warnings. No external research calls were made.

Remaining release validation: run the same portfolio and plays through the repaired architecture, then compare evidence uptake, action justifications, funded alternatives and final prose against the existing saved memo. Offline tests establish correct data flow and accounting behavior, not the quality of an unexecuted model response.
