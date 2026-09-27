# September 22 Remediation Implementation

**Latest:** the [September 23 follow-through](portfolio-remediation-followthrough-20260923.md)
fixes the four counterexamples below, implements the next scheduling/persistence/
financial safeguards, and adds a full downstream offline replay plus checkpoint
reuse. It is the current item-by-item status; no deployment or paid run occurred.

**Historical September 23 completion re-audit:** this work was partial. The
[completion review](portfolio-remediation-completion-review-20260923.md) adds four
reproduced unresolved defects in signal cancellation, embedded-check contract
reuse, observed-link support and expression-label precision. Its conclusions
qualify the implementation claims below; the four counterexamples did not pass
at the time of that review and now have passing regressions.

Status: **local changes, no deployment and no paid rerun**. The stopped recovery
remains stopped. Its artifact and original checkpoints were not modified. This
implements a substantial first tranche of the revised A00-A14 queue; it is not a
claim that every financial or end-to-end acceptance issue is closed.

## Changes Implemented

### Cancellation and Reader State

- `POST /api/analysis-jobs/{job_id}/cancel` persists cancellation intent and signals
  only the subprocess handle owned by this server. It never signals a saved PID.
- Queued work does not start; in-process supplementary preparation is cancelled;
  a worker that does not terminate receives a follow-up kill after ten seconds.
- Jobs have distinct `cancelling` and `cancelled` states. Late progress cannot
  restore a running state. Another server's job returns an ownership error.
- The portfolio progress panel provides Stop analysis and reports request errors.
  It distinguishes a requested stop from confirmed termination.
- A small `.portfolio-status/<run>.json` record updates reader status and ETags
  without rewriting the original analysis. Accepted provider requests are not
  represented as refunded or provider-cancelled.

### Request Persistence

- Streaming submissions, model results, review-section results and reusable
  observation checks commit small events to `<checkpoint>.events/`.
- Large paid responses remain content-addressed in `.portfolio-records/`.
  Records and request-event manifests are fsynced before acknowledgement.
- Recovery replays events newer than the materialized checkpoint. A submitting
  request retains its uncertain-outcome guard; a completed response retains its
  original model, request ID, usage and cache identity.
- Async pipeline updates no longer call synchronous `update_partial`. Model
  submission/completion and review-section updates use incremental events. Full
  materialization remains at analysis boundaries and some retrieval-provider
  and funding transitions.
- This is not a complete event-sourced replacement. Full boundary snapshots still
  copy assembled partial state; progress and metadata handling have other costs.

### Review and Evidence Work

- Repeated occurrences of the same exposure identifier are grouped across the
  ideal, current-aware, current-action and play views. Distinct identifiers are
  not treated as equivalent by guessing from names.
- Relative hedge play dimensions stay together as one comparison. Original
  component IDs and quoted user ideas are retained, not deleted.
- Detailed packets contain decision citations, relevant research answers,
  same-period competing forecasts and explicit corrections. Other observations
  remain in an uncut discovery index with access to archived source excerpts.
- Each reviewer admits at most two ready sections at once. Both independent
  reviewers share the existing four model slots, preventing one role from
  enqueuing its entire workload ahead of the other.
- Review work plans record dependencies, sections, economic cases and bytes.
  Findings can identify their economic case and the specific observations they
  challenge, separately from supporting observations.
- The downstream source selector starts with live proposals/alternatives,
  challenges to their observations and unresolved dispositions. Topic membership
  alone no longer makes every historical observation a mandatory check.
- Source checks are cached per normalized observation, current source content,
  model and exact checking rules/schema. Rebatching or an ID alias does not repeat
  a check; changed source content or model invalidates it. An unresolved check is
  retained as unresolved, not promoted to supported.
- Internal budget deferrals count as zero provider submissions and have a
  separate counter.

### Financial Safeguards

- Existing investment-detail/reconciliation stages receive specific case issues:
  missing return links, unsupported observed links, absent marginal sizing cases
  and changed premises without renewed sizing arguments.
- Missing economics is classified as uncertainty, not adverse evidence. These
  checks neither change weights nor discard the proposal or start another role.
- Play expression labels are checked against their declared target identity.
  A mismatch is explicitly unresolved rather than silently using an unrelated
  asset ID. Declared aliases are supported; the code does not guess a new mapping.
- The final checker receives these issues through its existing input. This does
  not prove that a future model will produce a good valuation or sizing argument.

## Offline Acceptance Evidence

`scripts/audit_portfolio_remediation.py` uses the actual stopped 24,440,094-byte
artifact. SHA-256 remains
`eebf7815a78f3c9d80dc31ea6313e2479397219e7a12dc0053353d4b290c2b09`.
Results: `outputs/audits/portfolio-r360-review-20260922/remediation-acceptance.json`.

| Measure | Result |
| --- | --- |
| Same original R360 input, before/after review sections | 26 -> 12 per reviewer |
| Same original R360 input, total review bytes | 11.48 MB -> 4.13 MB per reviewer, about 64% less |
| Stopped recovery input, current review plan | 13 sections, 4.45 MB per reviewer |
| Stopped input, source-check plan | 632 pending / 79 batches -> 398 / 50 batches |
| Combined materialized checkpoint and reader artifact | 45.51 MB |
| Twenty distinct concurrent fake results | All 20 recovered; zero full rewrites |
| Incremental storage for those results | 424,471 bytes including content records |
| Twenty concurrent result-event commits | Approximately 0.03 seconds; not full checkpoint replay or network latency |
| Largest sampled result-event loop delay | Approximately 2 ms in the isolated replay |
| Full boundary save | Approximately 2 seconds locally |
| Peak benchmark process RSS | Approximately 290 MB |
| Provider calls from this acceptance script | Zero |

The first selector draft expanded to 106 batches because topic groups were too
broad. The production-sized test caught it before release. Grouping review units
alone also failed to reduce work until detailed evidence selection was corrected.
These failures informed the implemented changes; they are not hidden by the
passing small tests.

Focused regressions cover concurrent durable results, crash replay, stale-event
materialization, write failure, source-version invalidation, original-model reuse,
cancellation before dispatch/during preparation, owned-process termination,
late progress and reader-cache invalidation. Browser cancellation tests pass at
1440 and 390 pixels in light and dark themes, including failed request/retry.

Final local verification on September 23:

- Unit suite plus portfolio memo integration tests: **725 passed**, five existing
  SWIG deprecation warnings, 202 seconds.
- Mocked browser cancellation checks: **four scenarios passed**. No paid API
  requests are used by these checks.
- Frontend production build and focused frontend lint passed. The existing
  bundle-size warning remains.
- Focused Python correctness lint and `git diff --check` passed. This is not a
  claim that every unrelated pre-existing lint issue in the worktree is resolved.

## Still Open Before End-to-End Acceptance

1. Fifty source-check batches remain substantial on this historical artifact.
   Its reviewers did not distinguish challenged claims from contextual citations.
   Do not remove these conservatively retained challenges solely to reach a count.
2. Automatic semantic equivalence between differently named exposures remains
   unestablished. The grouping deliberately does not equate US_TIPS with another
   independently generated ID without an explicit relationship.
3. Research priority and spend across difficult producer-economics questions,
   compared with readily available macro quotes, still need decision-level replay.
4. Common-scenario comparison across all four portfolio alternatives and the
   original U01-U07/U15 source/monitoring scope remain open in the full audit.
5. Financial case checks identify deficiencies; they do not themselves supply
   missing cash-flow, valuation or forward-return research. A changed-premise
   sizing argument must still be assessed substantively.
6. Cancellation of local execution cannot establish the outcome or final charge
   of a provider request already accepted. Preserve the three historical IDs.
7. The real-sized test covers request persistence and payload generation, not a
   complete fake-provider DAG with every optional lookup, failure and recovery.
   Do not infer a guaranteed live runtime or final quality from these benchmarks.

No final memo has been produced by this work. No new readability score, financial
quality score or successful production recovery is claimed.
