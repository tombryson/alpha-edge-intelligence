# Research handoff remediation

Implementation following [the research-led run audit](portfolio-research-led-comparison-20260919.md). These changes are local. They have not been deployed and the production analysis has not been restarted.

## Changes

### Evidence and research reuse

- Signed changes such as an inventory draw of 95 becoming `-95` are accepted only when the quoted clause establishes the direction and the metric is a change. Levels, mismatched magnitudes and ambiguous/opposite directions remain flagged. The transformation is recorded; it is not treated as a completed financial source review.
- Old signed-change warnings can be corrected from the retained source excerpt without downloading it again. Other verification issues and adverse source reviews remain attached.
- Dimension-specific answers are merged and revalidated instead of resetting partial research to unanswered or deferred. A failed or empty follow-up cannot erase a valid saved answer. A sourced conflict stays visible.
- Retrieval disposition is separate from answer coverage. Exhausting the discovery allowance does not relabel previously successful research as absent.
- Later phases search only genuinely new missing dimensions. Successfully searched dimensions are retained across phases and recovered from older lane records. The existing expansion mechanism can still investigate a surviving gap, after distinct material subjects receive their first search.
- Phase-qualified lane records prevent one phase from overwriting another's result. Provider task IDs, results and immutable receipts remain checkpointed.
- With submitted plays, earlier phases leave more of the existing discovery allowance for their material premises. This does not increase the allowance or reveal the ideas to the independent allocator.

### Investment decisions and reviews

- Investment prompts retain observations, dates, units, benchmarks, source excerpts and adverse verification information, without repeating interpretations and audit metadata on every fact. The full original ledger remains saved.
- Focused question answers appear ahead of the explicitly labelled initial market context. Allocators are asked to state the implication and portfolio consequence of the material research, including contrary evidence.
- Reviewers receive an explicit list of researched premises not cited in the two proposals. They must test materiality, not assume those premises demand a bullish or bearish conclusion.
- Financial prompts distinguish concentration from thesis merit, producer margins from spot-price momentum, index from sector valuation, and insurer economics from a generic yield-curve argument.
- Oversized reviews are grouped by research scope. A grouping target controls subdivision, not deletion of observations or rejection of an entire analysis. Unselected detailed observations remain in a structured catalogue, with the full source ledger available in the artifact.
- Completed review groups are saved immediately. Later groups receive the earlier findings and their source-linked facts. Failed optional groups qualify the combined review rather than discarding successful groups; a credit interruption preserves the already completed groups for recovery.
- Output-token allowances have not been reduced. The existing output expansion on truncation remains in place.

### Investment plays

- If the planning model omits component identities, a small request repairs just the decomposition using the submitted text. It does not repeat market planning or research.
- Valid frozen components are preserved. Relative preferences are distinguished from short trades, and the original submitted thesis remains authoritative.
- If decomposition still cannot be obtained, the omission is explicit. Neither a component inventory nor a play verdict is invented.

### Reader

- Incomplete workflow-4 artifacts display their saved independent and current-aware drafts, clearly identified as proposals rather than a final allocation.
- Credit-paused and stopped runs do not retain the misleading "analysis is in progress" summary in the memo view.
- Empty reconciliation, implementation and final-metric panels are omitted. Current cash is read from the actual snapshot.
- Two-column draft allocation tables wrap on mobile so weights remain visible.
- Completed memo text and the legacy presentation are unchanged. Old partial artifacts are projected into the corrected reader without rewriting the saved analysis. The derived reader cache version is advanced accordingly.

## Offline verification

The saved production artifact was used to inspect all four signed inventory changes and to measure reviewer packaging. The original failed prompts were approximately 900,000 JSON characters each. The initial review plan now has two requests per reviewer, approximately 353,000 and 335,000 characters before adding any newly generated earlier-review findings. These are character measurements, not provider token counts or a cost guarantee. No observations are clipped, and both original proposals remain saved.

Regression coverage includes signed and ambiguous changes, old-checkpoint answer recovery, partial/deferred states, distinct-question priority, new-dimension-only searches, uncited evidence in reviewer inputs, scoped component repair, review interruption/failure retention, cross-section source handoff, complete research/play scope coverage and non-mutating partial-reader projections.

The frontend production build succeeds. The reader browser checks cover desktop/mobile, light/dark, latest partial and legacy August, including accordion behavior and draft-table overflow. The local preview uses saved artifacts, not newly generated conclusions.

Verification result: 394 portfolio/source-context unit tests passed; all eight browser combinations passed with no JavaScript errors. The build retains its existing bundle-size warning. `git diff --check` is clean.

## Remaining release check

The next paid recovery must verify that the models actually reconcile the new research, complete their play debate and produce a coherent final memo. Unit tests establish the data flow and failure handling; they cannot establish the quality of a financial judgment that has not yet been generated. Additional credit alone was not the remedy, and deploying this code is not the same as completing the stopped analysis.
