# Remediation Completion Review, September 23

## Subsequent Implementation

The authorised [follow-through implementation](portfolio-remediation-followthrough-20260923.md)
now fixes C01-C04 as normal passing regressions and implements dependency-aware
source/case scheduling, incremental research/document persistence, common
scenarios, source context and monitoring safeguards. A production-sized offline
workflow reaches the reader and reuses completed requests on resume. That record
contains the current A00-A14 disposition and remaining acceptance limits.

The review below describes the state **before those changes**. Its failed-test
results are historical, not the current result. No deployment or paid run follows
from the local implementation.

## Verdict

**Partial, not complete.** The previous implementation delivered useful local
mechanisms and measured payload reductions, but did not finish the A00-A14
remediation or establish end-to-end acceptance. The full audit requested more
than cancellation controls, smaller requests and additional validation fields.
Stopping after this first tranche left required engineering work undone, not
merely a paid production verification step.

This review checked the requirements against current code and added four offline
counterexamples. All four fail when expected-failure handling is disabled.
No production process was touched, no paid provider was called, no deployment
was made, and the stopped recovery remains stopped. This pass changes tests and
audit documentation, not the application implementation.

## Newly Reproduced Gaps

### C01 / P1: Stop Can Interrupt a Received Result's Commit

`backend/jobs/executor.py:638` persists cancellation intent and calls
`process.terminate()`. The portfolio command has no SIGTERM handler to stop new
work and drain its result/stream writers. The shield in
`backend/portfolio_runtime.py:419` handles asyncio cancellation, not operating
system process termination.

The new test starts a real local subprocess, receives a fake result, pauses its
event writer for 300 ms, and cancels it through the actual job cancellation API
function. The base checkpoint survives, but the received result is absent after
loading it. This does not show that previously committed results are lost; it
shows that the promised cancellation-during-save acceptance is unmet. Existing
tests cover a sleep process and asyncio task cancellation separately, not this
combined production mechanism.

Required closure: cooperative stop/no further admission, bounded drain of pending
result commits and stream journals, then termination; preserve uncertain provider
identities when a forced kill is unavoidable. Test the real worker signal path.

### C02 / P1: Embedded Source Reviews Bypass Contract Invalidation

`scripts/portfolio_positioning_memo.py:1665` calls `reusable_fact_checks` before
consulting the new model/rules-keyed observation cache. In
`backend/portfolio_evidence.py:189`, embedded `claim_review` reuse checks only
the observation/source fingerprint and verdict shape. It carries no checking
model or rules contract. Already-reviewed facts therefore never reach the new
cache invalidation logic.

The regression passes the first reconciliation's actual returned evidence into
a second reconciliation after changing the mocked model. Only model A is called;
model B is skipped. The prior regression changed models using the original
unreviewed fixture, so it missed this path.

Required closure: distinguish preserved historical support from verification
under the currently requested checking contract. Apply explicit contract
provenance to both reuse paths. Do not automatically discard historical results
or repeat every paid check merely because a route changes; make that policy
explicit and test actual returned/checkpointed evidence.

### C03 / P1: Causal-Link Guard Tests Identity, Not Support

`backend/portfolio_judgment.py:447` treats an `observed` causal link as grounded
when all its IDs exist in the evidence dictionary. An observation explicitly
marked unresolved passes this specific check. With a populated sizing sentence,
the new counterexample produces no financial-case issue at all.

This is not proof that all downstream readiness checks approve that proposal.
It does establish that the new guard does not enforce the support distinction
the financial remediation requires. Missing/unverified source support must not
be represented as observed transmission into margins or free cash flow.

Required closure: inspect the actual source-support and supersession state of
the cited observation, distinguish an assumption from an observed economic
link, and retain uncertainty without converting it to a sell signal. Other
fields must not substitute for a substantive changed-premise sizing argument.

### C04 / P2: Identity Check Confuses Wording and Economic Identity

`backend/portfolio_judgment.py:479` compares normalized display strings and
explicit aliases. It flags an expression with the correct `GOLD_MINERS` ID and
label `Gold miner equities` against the target label `Gold Miners`.

The saved acceptance result already contains four expression warnings: gold,
silver and uranium wording differences plus the genuine infrastructure/bond
mismatch. Those are not equally meaningful defects. The test reproduces the
gold wording false positive.

Required closure: distinguish label differences from contradictory instrument
identity. Preserve the real bond/infrastructure defect without manufacturing
new review obligations for harmless wording. Do not guess or rewrite genuinely
ambiguous exposure mappings.

## Required Work Still Missing

| Audit item | Actual completion assessment |
| --- | --- |
| A00 Stop/preserve | Completed operationally in the prior stop pass. |
| A01 Cancellation | Partial. API, UI and durable intent exist; C01 leaves graceful commit/drain unfinished. |
| A02 Whole workflow planning | Partial. Review and source plans are recorded separately, but there is no complete dependency/optional-work admission plan or defensible remaining-time model. |
| A03 Persistence | Partial. Small model/result events work; synchronous `_snapshot()` copying still occurs before `to_thread`, research results/provider transitions still perform full saves, and C01 is open. |
| A04 Economic cases | Partial. Exact-ID grouping reduces duplication; cross-ID economic equivalence remains unresolved. The stopped fixture still has 57 named cases and 13 sections per reviewer. |
| A05 Source verification | Partial. New cache and narrower selection help, but C02 remains. All 50 selected historical batches are still awaited together before investment details/final settlement. |
| A06 Research priorities | Incomplete. Decision-level allocation of research effort to material producer economics and hedge questions has not been demonstrated or fully redesigned. |
| A07 Provider/funding recovery | Useful local fixes and narrow regressions retained. Full production-sized scheduling, failure and recovery acceptance remains incomplete. |
| A08 Plays/identity | Partial. Relative hedge grouping and identity warnings exist; general cross-output mapping, duplicate component resolution and C04 remain. |
| A09 Financial cases | Partial. New instructions/diagnostics do not supply missing valuation or return research. C03 and substantive corrected-premise sizing remain. |
| A10 Comparable alternatives | Partial. Arithmetic/funding checks exist; current, ideal, smaller-change and final portfolios are not fully compared under common named scenario assumptions. |
| A11 Progress/cost | Partial. Deferred-search accounting improved; remaining work, optional requests, critical path and cost are not one reconciled plan. |
| A12 Original source scope | Incomplete. U01-U07/U15 source/date/correction/monitoring acceptance remains carried forward, not resolved. |
| A13 Final reader | Existing layout preserved, not a newly verified final narrative. No final memo exists from this remediation to score or compare. |
| A14 End-to-end acceptance | Partial. Packet/persistence benchmarks are not a complete production-sized fake-provider DAG, including lookup expansion, source-check tail, interruptions, corrections and final memo. |

### Important Architectural Omissions

- **The publication barrier is still present.** At
  `scripts/portfolio_positioning_memo.py:1676`, `_gather_retained` awaits the entire
  selected source-check batch set. The main path at line 3318 waits for it before
  generating investment details and settlement. Fewer batches is an improvement,
  not removal of the audited late barrier.
- **The final source scope uses a different policy.** At line 3363, newly cited
  final facts are selected by `linked_facts(final) - selected_facts`, without
  rerunning `decision_source_check_plan` for their comparison/correction
  dependencies. Earlier checked provisional citations are not the complete
  dependency set of a changed final recommendation. This needs an explicit
  counterexample in the full workflow test before closure.
- **Persistence is only partly incremental.** `PortfolioRuntime.asave` invokes
  `_snapshot()` on the event-loop thread before handing the writer to a worker.
  `research`, `save_provider_task`, extraction caching and numerous runner
  transitions still call full `asave`. The 20-event benchmark does not measure
  every remaining transition in a complete run.
- **The acceptance test excludes the decisive workflow.** Smaller serialized
  packets and twenty durable fake responses cannot establish that all phases
  settle a coherent memo without multi-hour delays or repetitive diagnostic
  output. The missing full replay was an explicit A14 deliverable, not something
  that required another paid run to begin.

## Verification and Corrections to Prior Claims

New counterexamples:
`tests/unit/test_portfolio_remediation_completion_audit.py`.

```sh
.venv/bin/pytest -q tests/unit/test_portfolio_remediation_completion_audit.py \
  --runxfail --tb=short --show-capture=no
```

Result: **4 failures**, one for each C01-C04. The tests are marked strict expected
failures so normal runs explicitly report known unresolved defects, not passing
fixes. Run with `--runxfail` to see the actual assertions. They must become normal
passing regressions when repaired. No production/runtime behavior was changed
in this review.

The previous **725 passed** result remains a historical test result, not evidence
that the four newly tested cases pass. The prior benchmark's 0.03 seconds measures
twenty concurrent event commits, not the time for complete checkpoint recovery.
Its recovered-result count remains 20; the timing label is corrected separately.

The measured 64% review-input reduction remains valid for the stated original
R360 fixture. It is neither a 64% end-to-end runtime reduction nor proof of
improved financial conclusions. No new score or final memo is claimed.

## Correct Remediation Order

1. Close C01-C03 with failing-to-passing regressions; correct C04 without weakening
   real instrument-identity checks.
2. Finish the dependency-aware task plan and incremental source-check scheduling,
   including material opposing claims and final-decision changes.
3. Remove remaining full-state event-loop hot paths and run a complete real-sized
   fake-provider workflow with signal/crash/slow-write/recovery scenarios.
4. Finish research prioritisation, economic case/play identity, corrected-premise
   sizing and four-view common-scenario comparison; test the financial examples
   from the full audit rather than only checking new fields are present.
5. Close source/correction/monitoring and final-reader acceptance. Only then
   propose a separately authorised live comparison with an explicit work estimate.
