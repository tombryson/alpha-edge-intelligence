# Portfolio Analysis Workload Audit

17 September 2026. Based on the deployed runner, saved production artifacts, retained provider receipts, and local replay of the actual checkpoints. This is an execution and architecture audit, not a claim that the financial recommendations have been independently verified.

The findings below describe the audited production workflow. The [implementation
update](#implementation-update) records the subsequent remediation and its
verification. It is deployed in release 344; see the deployment record below.

## Executive Finding

The workflow is over-expanded. The count of 112 represented completed internal tasks, not 112 distinct analytical stages. Some batching is justified; the expensive duplication is not explained by batching alone. Three identical copies of each portfolio-aware role run against the same evidence. Each proposal is then elaborated in small batches that repeatedly receive the entire large evidence ledger. Judges and final synthesis also pass through that enrichment mechanism.

This combines an older three-memo ensemble with newer source-review and detail-expansion machinery. The result is multiplicative work, repeated large prompts, poor cost visibility, and heavy checkpoint I/O. Recovery fixes preserve work, but do not by themselves simplify this architecture.

## What The 112 Actually Were

Snapshot: `portfolio_positioning_job_portfolio_recovery_20260917_003009.json` and its checkpoint. There were 118 receipt rows, 113 distinct task hashes, 112 complete tasks and one failed task. Receipt rows include retries; completed-with-limitations tasks also count as complete. A cached task is not a new paid call.

| Completed task category | Count | Purpose |
| --- | ---: | --- |
| Research retrieval | 9 | Three research topics, each using native Grok, Perplexity and Tavily |
| Source fact extraction | 25 | Source-text batches: 9 macro, 8 sector, 8 coverage |
| Research brief composition | 3 | One brief per research topic |
| Source-support review | 39 | Review 307 facts, eight facts per batch |
| Evidence reconciliation | 1 | Combine the three briefs |
| Allocation proposals | 9 | One blind macro prior plus eight completed portfolio-aware proposals; the ninth portfolio-aware proposal had failed |
| Investment-detail batches | 26 | Elaborate four proposed sleeves at a time |
| **Total complete at that checkpoint** | **112** | **Not the final planned workload** |

The original credit-failed run had 81 complete tasks, nine failed tasks and four dependency gates. Recovery advanced the retained work to 112, then 119 before the memory interruption. Neither 112 nor 119 meant that final judgement and memo synthesis had completed.

The nine research tasks also conceal provider-internal activity. The three native Grok receipts reported 48 web searches in total and zero X searches. A task count is therefore neither a count of distinct reasoning roles nor a complete count of external requests.

## Actual Execution Shape

```text
Three distinct research topics
  x Grok + Perplexity + Tavily
  -> source extraction batches
  -> one brief per topic
  -> merged source-review batches
  -> evidence reconciliation

One blind macro allocation
  -> investment-detail batches

Three memo replicas, each containing:
  portfolio-aware allocator
  exposure-equivalence reviewer
  defensive-regime reviewer
    -> investment-detail batches for every proposal
  allocation judge
    -> investment-detail batches for the judged allocation
  memo commentary

Cross-memo synthesis
  -> investment-detail batches again
  -> final commentary

Conditional trade follow-up:
  another Grok + Perplexity + Tavily research pass
  extraction + brief
  reconcile old and new evidence, including source reviews
  another allocation judge + detail batches + commentary
```

Relevant implementation: `portfolio_positioning_memo.py:143`, `:153`, `:1963`, `:2213`, `:2463`, `:2640`, `:2721`.

## Findings

### 1. Identical Role Requests Run Three Times

**High priority.** The retained requests for the portfolio-aware allocator, exposure-equivalence reviewer and defensive-regime reviewer each have exactly one unique canonical prompt across `memo_1`, `memo_2` and `memo_3`. Each role uses the same model in all three replicas. The shared macro prior is already separate and is reused.

These are stochastic replications, not distinct research mandates or new sources. They may produce different answers, but there is no measured stability benefit recorded to justify the extra expense. Agreement between these replicas must not be presented as three independent evidence confirmations. The cache deliberately includes the lane in its key, so identical prompts under different memo labels do not share a result.

**Recommendation:** retain all four defined roles, once each, followed by one comparison. Use a second request only for a specific unresolved disagreement or failed task. Do not replace this with another user-facing fast/deep mode or disable roles.

### 2. Generic Request Handling Silently Expands Every Allocation

**High priority.** `_query_stage` detects `asset_class_targets` in the response schema and automatically runs additional requests for implementation, pricing, investment cases and alternatives. This happens for initial proposals, allocation judges and synthesis, not just the eventual proposal a user reads.

Four sleeves per detail batch is an output-size safeguard. However, applying it to every intermediate proposal multiplies the workload. An allocation with 20 sleeves causes five extra model requests before it can even be compared with alternatives. Repeating enrichment after each judgement redoes work that may be discarded or substantially revised.

**Recommendation:** make proposal generation, challenge/comparison, and final enrichment explicit orchestration steps. Keep role proposals concise but financially substantive. Elaborate the selected proposal once, preserving meaningful alternative arguments. A generic model wrapper should not launch a hidden sub-pipeline.

### 3. Detail Requests Repeatedly Send The Whole Ledger

**High priority.** Observed allocator prompts contained roughly 635-696 thousand JSON characters; detail prompts reached 718,607 characters. Requests commonly consumed about 200,000-234,000 input tokens to explain four sleeves.

The projected evidence brief alone contained 626,635 characters. Its 307-fact ledger contained 517,218 characters. Within those facts, `claim_review` objects accounted for 202,365 characters; both `interpretation` and merged `interpretations` were carried. Full raw documents were removed from the downstream projection, but detailed audit metadata and overlapping narratives were not.

The detail request also repeats the entire allocation and portfolio context. In a recorded Grok detail request, provider-reported cost was about $0.86, of which about $0.84 was input cost. This is context retransmission, not expensive new research.

**Recommendation:** keep the full ledger and all raw receipts as evidence artifacts, but give analytical roles a compact decision-oriented view. Supply detail batches with relevant facts, conflicting evidence, exact source IDs and essential portfolio constraints. Retain a shared cross-asset summary and access to the complete ledger so relevance selection does not conceal contrary evidence. Do not solve this with arbitrary text truncation.

### 4. Follow-Up Research Can Re-Review The Existing Ledger

**High priority.** The conditional trade follow-up merges the existing brief with newly collected evidence and calls `_run_evidence_reconciliation` again. That function batches all merged facts for review; it does not select only new or changed source claims. Its review prompt also includes the changed research query, so exact-request caching is not a reliable substitute for incremental verification.

**Recommendation:** reuse field-level checks bound to an unchanged fact fingerprint and source digest. Review only new/changed claims, then reconcile the trade-specific implications. A changed research question alone should not invalidate the evidence supporting an unchanged observation.

### 5. More Tasks Have Not Produced Stronger Source Coverage

**High priority.** At the 119-task checkpoint there were 88 source records representing 74 URLs. Twenty-two records, all native-Grok citation records, had no source excerpt. Fifty-seven source records lacked a publication date. Grok summaries were available to brief composition, but citation URLs without text could not independently substantiate extracted facts.

Of 307 facts, the current rules classified 12 as supported, 266 as unresolved and 29 as unsupported. Only 113 passed source-matching checks; 194 still needed verification. Missing publication dates affected 171 facts, and 23 facts had a supporting excerpt that could not be found in the retrieved source.

**These counts do not establish that 295 facts were false.** Missing provenance and conservative all-field verification explain much of the unresolved count. They do establish that collection and metadata quality, not the number of model passes, constrain verification. An unsupported status is also the saved model/source-check assessment, not an independent financial adjudication.

**Recommendation:** retrieve usable text and date metadata for the small set of decision-critical sources, particularly citation-only URLs. Separate 'missing metadata', 'source contradicts claim' and 'interpretation disputed'. Preserve uncertainty without treating every missing date as an economic negative or preventing a useful memo.

### 6. Checkpoint Serialization Was Capable Of Killing The Worker

**High priority; immediate memory fix deployed.** The production checkpoint reached 147,231,016 bytes. The kernel killed the worker at 01:30:37 UTC with an explicit out-of-memory message. The writer constructed a whole-document Unicode string and UTF-8 representation.

Local replay of that exact checkpoint measured 1,122.83 MiB peak serialization allocation before the fix and 1.52 MiB after streaming serialization. Decoded data was identical. Release 341 contains the streaming writer, atomic saves, and completed-receipt recovery for an interrupted cache commit.

The remaining architecture is still inefficient: each completion or cache reuse rewrites the large checkpoint and artifact, synchronously inside the async workflow. Prompt dictionaries, serialized request messages, cache receipts and artifact receipts duplicate substantial content on disk. This makes even zero-model-call recovery take minutes.

Immediate follow-up, deployed in release 342: cache hits now defer persistence until the next existing phase boundary or new result. Newly generated results still checkpoint immediately. Tests explicitly verify zero per-hit writes and preservation of the next persisted snapshot. The larger append-only storage redesign remains outstanding.

**Recommendation:** append immutable request/result records once, reference large prompts and raw responses by content hash, and atomically update a small run manifest. Keep the current checkpoint format readable during migration. Do not delete forensic data to obtain smaller files.

### 7. Recovery Previously Changed Accepted Inputs

**High priority; fixed.** Accepted-with-limitations enrichment was not cached. A retry regenerated an optional macro-prior detail, changing downstream prompt hashes and causing completed allocators to run again. That retry was stopped.

Accepted outputs, including their unresolved fields and warnings, now remain stable on resume. The offline replay verified all 119 completed tasks could be reused with zero model calls. Frozen research, model assignments and the original cutoff are preserved. Explicitly repairing an accepted result should be a new version, not a side effect of ordinary resume.

### 8. Cost And Progress Are Not First-Class Run Contracts

**High priority.** The job reports coarse stages and reaches 88% on entering Stage 3, although substantial allocation, enrichment, judging and follow-up work remains. The current task count cannot tell a user how many roles, requests, retries or cached results it represents. Perplexity's provider result does not expose equivalent top-level usage accounting, and unknown/unreported costs cannot be treated as zero.

No end-to-end request plan or reliable cost estimate is presented before the nested work begins. Account credit and provider in-flight reservations then become failure mechanisms, rather than an explicit continuation decision.

**Recommendation:** expose business phase, completed/pending model requests, reused results, retries, actual reported cost and unreported-cost providers separately. Show an estimate/range before starting. Preserve funded work on credit failure and allow continuation without switching models. Avoid inventing a hard spending limit without user direction.

### 9. Failure Messages Obscured The Process Failure

**Medium priority; fixed.** The OOM-killed job displayed an earlier token-limit warning as its main error. The executor now gives signal termination precedence over older artifact errors. SIGKILL identifies external termination and points to server logs; it does not assume every SIGKILL is OOM.

### 10. Analytical Detail Exceeds Available Portfolio Inputs

**Medium priority.** This run supplied an asset-class portfolio and no individual holdings. The system can discuss a macro allocation, but cannot establish instrument-specific duration, currency hedging, trading costs or investor constraints from absent inputs. Repeatedly asking models for these details cannot create the missing facts.

**Recommendation:** distinguish a readable asset-class investment memo from implementation checks requiring actual instruments and an investor mandate. Show unknowns where relevant, preserve useful arguments, and avoid repeated enrichment attempts for information that only the user or an external source can provide.

### 11. Interrupted Cache Migration Can Lose Discoverability

**High priority; found by this audit, immediate fix deployed in release 342.** The prior structured cache lookup accepted the current code-manifest key and one previous-manifest key. After a code change, a resumed run migrates entries only as it visits them, but saves the new manifest on its checkpoint. If that recovery is interrupted before visiting every cached task, a further resume no longer has the original manifest needed to locate untouched entries. The data is still in the cache, but the lookup can issue another model request instead of finding it.

An offline two-task reproduction confirmed this: complete A and B under an old manifest; resume under a new manifest and visit only A; resume that checkpoint and request B. The mock provider was called again for the already completed B. No paid calls were used. This is separate from the accepted-with-limitations cache bug already fixed.

The immediate patch retains cache-manifest ancestry in the checkpoint and validates matching entries across that history. The same interruption regression now makes no extra model calls. The scoped suite passes 234 tests. The later 131-task checkpoint also reuses every completed structured result offline: 122 structured tasks, plus nine saved retrieval tasks, with 13 completed-with-limitations results preserving their warnings.

**Recommendation:** store a version-independent request-contract identity alongside the code provenance and validate matching retained results against current rules. Preserve migration ancestry for legacy entries. Test interruption at every point in a cross-version resume, not only uninterrupted replay. This affects discoverability and expense, not permission to reuse semantically changed inputs.

### 12. Checkpoint Writes Block Active Network Requests

**High priority; immediate fix deployed in release 342.** Streaming solved peak serialization memory, but the synchronous writer still ran on the async event loop. A completed request could block all other requests while serializing the entire checkpoint and artifact. Grok progress callbacks also rewrote the entire payload. The latest recovery accumulated `ConnectError` and `ConnectTimeout` failures, while an independent OpenRouter models-endpoint request from the same VM succeeded. Event-loop blocking is a confirmed implementation defect; the original blank exceptions do not establish it as the sole cause of every connection failure.

New-result persistence now uses an ordered background writer and immutable snapshots. It remains awaited before returning a newly accepted result. Cached results are already durable and are persisted at the next phase boundary. Streaming research progress is logged, including its provider response ID, and the terminal research result is checkpointed. Phase-boundary writes remain synchronous. Additional transport cause diagnostics retain underlying exceptions for future diagnosis.

Regressions verify that the event loop progresses while a writer is blocked, older snapshots cannot overwrite newer ones, and terminal research remains durable. This is not an append-only storage migration: total file size and repeated whole-file writes at actual completions still need architectural attention.

## Recorded Cost

Accounting covers the original newer run and four retained recovery artifacts through the stopped 01:38:47 UTC recovery. Provider request IDs are deduplicated across artifacts and reused receipts. These are reported OpenRouter costs, not the whole account bill, not an estimate of the unfinished run's final cost, and not a total for both requested runs.

| Work | Distinct receipts with reported cost | Reported USD |
| --- | ---: | ---: |
| Fact extraction, including retries | 30 | 0.228107 |
| Evidence briefs, including retries | 6 | 0.153890 |
| Source reviews, including retries | 42 | 0.344339 |
| Evidence reconciliation | 1 | 0.072025 |
| Allocator proposals, including retries | 16 | 3.427124 |
| Investment details, including retries | 38 | 13.396986 |
| **Total observed** | **133** | **17.622471** |

Those receipts reported 12,249,717 input tokens and 900,901 output tokens. Investment details account for approximately 76% of this observed spend. Fact extraction, brief composition, source review and reconciliation together account for about $0.80. Removing source verification because its batch count looks large would target the wrong cost centre.

Separate native xAI, Perplexity and Tavily charges, unreported provider charges, and work performed after these snapshots are not included. Both requested runs remain incomplete, so this table is a bounded audit snapshot, not a final invoice.

Reproduction: `outputs/audits/portfolio-20260917-recovery/audit_workload.py`; machine-readable results: `workload-accounting-latest.json` in the same directory. The inputs are original-credit-failure.json, latest.checkpoint.json, stopped-cache-retry.json, memory-interrupted.checkpoint.json, and connection-interrupted.checkpoint.json. No provider calls are made by the audit. The previous memory-interruption accounting snapshot remains in workload-accounting.json.

## How This Happened

The three-memo ensemble is present in committed `HEAD` (`2de86fe`, 8 September 2026); it was not introduced by today's recovery changes. The newer fact extraction, nine-field source review, four-sleeve enrichment and runtime/checkpoint modules are part of the uncommitted portfolio-integrity work. They expanded the existing nested ensemble rather than replacing it with a bounded explicit workflow.

The exact uncommitted edit times cannot be established from git history alone. The 16 September remediation notes document the output-batching work. Tests verify local contracts and resume behavior, but they did not assert realistic full-run call counts, input-token volume, cost, memory or throughput. That testing gap allowed individually reasonable changes to form an excessive combined workflow.

## Recommended Target

1. Collect distinct research topics and hydrate decision-critical sources.
2. Extract and verify facts once, with incremental updates and a compact analytical projection.
3. Generate one independent macro prior.
4. Run the three complementary portfolio-aware roles once each.
5. Compare their proposals once; request targeted additional evidence only for material unresolved disagreements.
6. Enrich the selected proposal once and write the memo.
7. Preserve all raw evidence, uncertainty, dissent and request receipts outside the reading path.

This retains model diversity and the four analytical roles. It removes repeated whole councils and repeated implementation prose. It does not prescribe an arbitrary total task count: source batching should depend on actual evidence volume. The important constraint is that each expensive pass has a distinct, testable purpose.

## Required Regression Checks For A Simplification

- A full fixture asserts exactly one invocation per role and makes duplicate same-model/same-prompt requests visible.
- Instrument-detail generation occurs once for the final chosen proposal, not for every intermediate allocation.
- New research reviews only changed claims while preserving prior source-bound checks and dissent.
- Prompt projection preserves relevant numbers, dates, benchmarks, sources and contrary evidence, with measured input-token reduction.
- A 150 MB historical checkpoint resumes without model calls, without whole-document serialization copies, and without rewriting that payload for every cache hit.
- End-to-end tests report total requests, input/output tokens, cost when available, peak memory and saved artifact sizes.
- Partial optional metadata does not erase the memo; failed critical work remains visible and recoverable.
- The memo's existing presentation, light/dark themes and model assignments remain unchanged.

## Recovery Status

Release 342 contains the immediate transport, stable-resume, streaming-write, signal-error, cache-ancestry and active-request persistence corrections. It does not implement the recommended analytical simplification above. Image: `deployment-01M2PKNFGTDGJ22B1N441QHXDY`, digest `sha256:5b2f53a48b4de32d915246d10f92591a372c10c6b6107c14ac2d599a7c2a7ba6`. Production hashes match all five tested runtime files; readiness and Fly checks pass. The UI and model assignments are unchanged.

Job `a07cf25c-e0af-44b0-b8ca-12a5ea6cd462` was deliberately stopped at 02:37:30 UTC after waiting for checkpoint writers to close. Its checkpoint subsequently retained 131 completed tasks, 119 reused from its parent, and two failed judge attempts. The 216,565,953-byte checkpoint is also backed up locally as connection-interrupted.checkpoint.json. Original runs and prior completed work are preserved. The earlier 11:05:23 UTC run has not yet been resumed live. Brightstar remains cancelled.

At the post-deployment check no jobs were active. OpenRouter had $12.613694119 remaining. The attached 3 GB data volume had 655,847,424 bytes free; this run's checkpoint and artifact alone occupy about 340 MB, before another recovery copy or temporary save. Approval has been requested to extend that volume to 5 GB rather than delete saved runs. Further paid work is paused pending that storage choice. The choice of whether to simplify the earlier recovery's repeated role/enrichment workflow has also been presented separately.

## Implementation Update

Implemented after the request to finish the audit changes and reduce workload.
No configured model, research topic or analytical role was removed. Implementation
and testing did not start a new paid run or recovery, resize storage or create a
commit. Deployment was subsequently requested and is recorded below.

### Version-Two Workflow

```text
Same three research topics and provider lanes
  -> hydrate citation-only source text where available
  -> extract, review and reconcile the evidence
  -> one blind macro prior
  -> three complementary portfolio-aware roles, once each
  -> one allocator comparison
  -> existing single conditional follow-up round
  -> final allocation synthesis using all proposals and updated evidence
  -> investment details for the selected proposal only
  -> one final commentary
```

The comparison, synthesis and commentary retain their configured assignments.
The generic model wrapper no longer launches enrichment for every intermediate
allocation. No new operating mode or role toggle was introduced. Existing
version-one checkpoints retain their original orchestration and request shapes
to preserve paid results; ordinary recovery does not apply the new workflow to
old results or silently regenerate accepted-with-limitations outputs.

### Findings Addressed

| Findings | Implemented change |
| --- | --- |
| 1, 2 | One invocation per analytical role; detail-writing only after final synthesis. |
| 3 | Compact analytical projection retains every fact, source reference, dissent, observation and uncertainty while removing source digests and redundant positive-review metadata. No arbitrary text truncation or relevance filter discards evidence. |
| 4 | Reuse prior review verdicts only when both the fact fingerprint and current source-text digest match. New or changed claims are reviewed again. |
| 5 | Deduplicate citation-only URLs, reuse available source text and use existing Tavily extraction for missing text. Freeze extraction results. Do not substitute model narrative for a source or invent publication dates. |
| 6, 12 | Content-addressed immutable records plus a small atomic manifest, retaining the ordered background writer. Old inline checkpoints remain readable. |
| 7, 11 | Stable accepted-output reuse and cache-manifest ancestry remain covered by interrupted-resume regressions and the actual historical replay. |
| 8 | Funding preflight and per-request checks; distinct task, request, reuse, retry and reported-cost counts; business-phase progress without the false 88% marker. |
| 9 | Signal termination retains precedence over older warnings. Credit interruptions have a specific saved-work message. |
| 10 | Final-detail prompts explicitly retain unknown instrument, duration, hedge, cost and mandate fields instead of inferring absent user inputs. |

Source hydration improves the opportunity for verification; it does not guarantee
that a page is retrievable, dated or correct. Existing unresolved evidence stays
unresolved. Full financial validation still requires a completed, independently
reviewed live analysis; offline regression does not establish investment quality.

### Funding Contract

`POST /api/portfolio-positioning/preflight` is read-only. Job submission checks
funding before creating the worker, and the worker checks again before research.
The check uses OpenRouter account credits and the inference key's remaining
allowance, taking the lower balance when the key has a cap. A null key cap does
not imply an unlimited account. An optional server-only
`OPENROUTER_MANAGEMENT_API_KEY` supports the credits endpoint when needed.

The estimate uses current exact-model pricing and median/max token usage measured
from the September 16 receipts, adjusted for workflow and completed tasks. It
includes one conditional follow-up, not retries or separate xAI, Perplexity and
Tavily charges. The historical prompts were larger than the compact workflow, so
this is deliberately conservative pending new measured receipts, not a quote or
hard spending limit. Unknown balances or pricing are reported as unverified;
they are not treated as zero cost or sufficient credit.

New queued/running portfolio jobs reserve estimated headroom within the API
process. Within each worker, uncached requests check live balance and reserve
conservative prompt/output headroom for concurrent requests. These are local
planning reservations, not provider-side escrow: other applications, provider
billing delays, unexpected retries and external-provider balances can still
interrupt a run. UTF-8 message bytes provide a conservative text-token envelope
for request headroom, not a measured billed-token count.

On insufficient credit or HTTP 402, new model calls stop while already-started
calls finish and persist. The artifact records `awaiting_credit`; the subprocess
exits 75. For existing job-API compatibility its terminal job status remains
`failed`, with an explicit add-credit/saved-work message. The existing recovery
action resumes the checkpoint after a successful new funding check. There is no
automatic credit purchase, model substitution or background restart.

### Storage And Verification

Version-two CLI runs store large requests, raw responses and normalized results
in a shared `.portfolio-records` directory beside run artifacts. References use
SHA-256 identities and are verified on read. Small checkpoint manifests and
receipt indexes point to those immutable records. **Backups and transfers must
include `.portfolio-records` as well as the JSON artifacts and checkpoints.**
No record garbage collection or deletion of saved runs was introduced. Legacy
checkpoints continue using their original inline layout.

Same offline fixture, including conditional follow-up:

| Measurement | Legacy workflow | Version two |
| --- | ---: | ---: |
| New model requests | 47 | 19 |
| Research requests | 12 | 12 |
| Completed logical tasks | 59 | 31 |
| Checkpoint bytes | 3,261,925 | 111,675 |
| Artifact + checkpoint + referenced records, bytes | 6,169,517 | 811,753 |

The full version-two storage total includes its immutable records; the smaller
manifest alone is not presented as the whole storage footprint. These fixture
measurements are not forecasts of a real portfolio's final request count or cost.

Verification passed: **260 scoped Python tests**, frontend build and targeted
lint, browser regression for existing memo structure and both responsive themes,
runner-copy equality and `git diff --check`. The two previously documented
unrelated failing test modules remain excluded; this is not a claim that the
entire repository suite passes. Actual historical checkpoint replay reused all
122 structured tasks without model calls, preserving 13 limitation warnings;
nine retrieval tasks remain cached, for 131 retained completed tasks in total.
Both original failed runs remain preserved and were not relaunched.

### Deployment Verification

Deployed 17 September 2026 in Fly release **344**, image
`deployment-01M2PQEQEWQMTQW0S4PB5387ZM`, digest
`sha256:9c5d9dd35561817ae8db643e55fa3b2bff3eac38145c72877a6fa12f051e3221`.
Machine `683d6eeb612638` is healthy; Fly smoke, HTTP readiness and DNS checks pass.
All 15 checked runtime-file hashes match tested source. Frontend assets are
`index-BKLRBHLv.js` and the unchanged `index-BjVH35BX.css`.

Final deployment verification found and corrected a metadata gap: partial and
credit-paused artifacts now always retain the runtime's workflow version, so a
version-two recovery is not estimated as the heavier legacy workflow. Both
workflow versions are covered. The final scoped suite passes **262 tests**.

The production-container record-store smoke test passes, including immutable
record reads and workflow-version preservation after a credit pause. Authenticated
saved-memo loading and credit preflight pass. Preflight successfully read the
OpenRouter balance and live configured-model pricing; the tested one-sleeve
read-only fixture returned `ready`. This is not a paid analysis or a guarantee of
funding for every portfolio. The balance at verification was $12.61.

No active jobs were present. The same 19 portfolio JSON files remain, including
both original failed runs and their checkpoints. No recovery, model-setting change,
storage resize or commit was performed. The 3 GB data volume is unchanged.

## Local Progress And Checkpoint Pass (Not Deployed)

The subsequent running portfolio exposed a visibility defect: the job retained
"Gathering macro and market research" through fact extraction and source review.
Completed receipts were available, but queued and in-flight work was absent from
the status feed. Request timestamps included semaphore queue time, and worker
heartbeats advanced `last_output_at` without any new output.

The local remediation adds:

- Real phase and batch counts, with conditional follow-up research kept separate.
  For example: `Checking facts against sources: 50/67 batches saved; 4 running;
  13 queued (9 retries)`. This is a test fixture based on the observed workload,
  not a claim about the current production run or a completion forecast.
- Active/queued request records with model, role, attempt, queue timestamp,
  actual dispatch timestamp and concise retry reason. Credit-check time is
  distinct from model execution time. Counts do not imply an overall percentage.
- Separate last-response, last-completed-result, checkpoint and worker-heartbeat
  timestamps. A heartbeat no longer advances portfolio `last_output_at`.
- Checkpoint sequence, saved time and retained-task count in the checkpoint,
  artifact and job progress feed. A result is counted as saved only after the
  atomic checkpoint write succeeds. Failed writes retain the prior saved time.
  An artifact-write failure after a successful checkpoint is reported separately.
- Explicit boundaries after extraction, source review and final assembly, in
  addition to the existing per-response/per-attempt checkpoints. Immutable
  response records and cache-compatible resume remain the recovery mechanism.
- A compact live status band above the existing memo workspace. Request and phase
  details start collapsed and have bounded scrolling. Refresh reconnects to an
  active job; failed polling keeps the previous status with an explicit warning.
  Terminal jobs cannot continue displaying requests as running.
- Portfolio-filtered job listing and structured polling/SSE progress. The legacy
  `stage_message` also carries the detailed phase count for existing clients.

Queue/dispatch events do not rewrite the full checkpoint. Cache hits reuse the
parent checkpoint and are persisted at the next boundary or new result. An
in-flight response lost to a hard process termination may still need to be
requested again; this pass does not claim recovery of responses never received.
The `.portfolio-records` directory remains required for complete backups.

The memo's layout and themes, model assignments, analytical prompts, four-request
concurrency, validation/recovery policy and retry budgets are unchanged. This is
an observability and durability pass, not a promise of faster model responses.

Verification: **285 scoped Python tests passed** (with the two existing exclusions documented
above), targeted ESLint, production frontend build and responsive Playwright
checks. Browser cases cover both themes, checkpoint/response timing, retries,
refresh, failed polling, interruption, legacy jobs without structured progress,
and the unchanged saved-memo presentation. Historical checkpoint replay reuses
all 122 structured tasks and preserves 13 limitation warnings with zero model
requests. The frontend build retains its existing large-chunk warning.

Reproduce the new checks with `tests/unit/test_portfolio_progress.py` and
`tests/browser/portfolio-progress.mjs`; screenshots are under
`outputs/audits/portfolio-progress/browser`. No provider calls, deployment,
production restart, cancellation or automatic recovery were performed in this
pass. The active production analysis is not retrofitted with the new telemetry.
