# Portfolio Redesign: Independent Second-Pass Review

## Verdict

**The core diagnosis was correct. The implementation only partially addressed it,
and the September 20 ledger overstated completion.** Smaller detail requests are
a real improvement, but are not proof that the complete workflow has been
redesigned correctly. This pass found seven reproducible defects or missing
behaviours in addition to remaining request-design problems.

This is a review of the current local code, the September 20 saved artifact and
the recorded profile of its 112 model attempts. No application code was changed,
no deployment occurred, and no paid model or research calls were made during
this second pass. Only audit documentation, an offline profiler and explicitly
failing regression examples were added or updated.

## Item-by-Item Assessment

| ID | Reassessed status | What works | What is incomplete or wrong |
| --- | --- | --- | --- |
| R01 | Verified within the tested contract | Reprojection preserves sources, question IDs, context and source-review metadata; original archive remains unchanged. | This is a correctness fix, not a reduction in the evidence legitimately stored. |
| R02 | Correct helper; incomplete integration | Small case requests include related question answers and opposing same-series observations instead of global reference union. | Later reconsideration passes the entire final proposal into that helper. Its explicit one-exposure scope does not actually scope its evidence. A shared cross-asset driver/coverage manifest is still absent. |
| R03 | Reopened: correctness defects | Compact detail records remove a duplicated proposal. | The caller supplies a filtered proposal, so the supposedly whole-book weight table is incomplete. The reuse hash ignores newly relevant but previously uncited evidence and changed question answers. |
| R04 | Targeted fixes verified | Play-ID/name variation, duplicate funding rows, exact duplicate links and chronological numeric changes have regression coverage. Unknown mappings remain unresolved. | These targeted fixes do not prove that all duplicated representations of a decision agree. A canonical decision-table redesign is still incomplete under R08. |
| R05 | Partial; original overlap unresolved | Explicit reuse IDs, structured scope, aliases, critical-premise priority and source history exist. | The three original inventory questions still match no prior case on offline replay. Question-level identity cannot reuse only the overlapping measurements when their broader periods/horizons differ. |
| R06 | Targeted implementation verified | Focused searches use a focused answer schema. Identical source chunks can reuse extraction across groups and checkpoints. | No live evidence that the new neutral extractor preserves financial quality. It is still a per-chunk cache, not proof of full semantic research reuse. |
| R07 | Reopened: review coverage defects | Previous section narratives are no longer appended; sections execute concurrently; local fact lookup exists. | Splitting removes the current assessment's exit/hold/trim rationales. An all-play-question case can omit an unlinked baseline target's argument altogether. A large single play is still indivisible; findings remain content-hash records rather than persistent issue identities across amendments. |
| R08 | Materially incomplete | Final output is a delta; compact detail/check inputs and cleaner writer input remove some repetition. | Provisional output still requests the large multi-representation document. Final input still carries everything. Final consistency reintroduces a full funding object; scoped reconsideration still sends the whole proposal and broad evidence. |
| R09 | Partial; numeric parser defect | No complete previous answer is appended to generic repair. Many presentation faults are repaired locally; valid fields can be retained. | Field repair copies the full original evidence request and operates at top-level field granularity. Partial numeric tokens can be accepted as complete values. |
| R10 | Reopened: recovery defect | Streaming, timestamps, journals and protection against unknown duplicate submissions exist. | A known HTTP 402 rejection can remain `submitting`, blocking recovery after funding. Journal flushing is event-driven, not an independent five-second timer; abnormal-duration alerting was not implemented. |
| R11 | Reopened: compatibility/accounting gaps | Existing checkpoint and request-cache tests pass; changed prompts do not become arbitrary cache hits. | Known-rejection recovery is broken. Cost accounting does not recognise the new extraction task name and classifies it as allocation work. Old workload profiles remain. |
| R12 | Previous verification insufficient | The saved archive is unchanged and the earlier byte reductions reproduce. | The previous benchmark covered selected components, not every dispatch or downstream stage, and did not assert complete review coverage. The 464 passing tests missed the seven counterexamples below. |

## Reproduced Defects

### 1. New Contrary Evidence Does Not Invalidate a Saved Investment Case

`detail_basis` hashes the decision and its existing linked facts, not the complete
evidence scope used by the new request builder. Adding a new contrary fact to a
related question makes it visible to a new detail request, but does not invalidate
the previously saved detail response. `retain_current_details` reports no stale
cases and keeps `detail_status=current`.

Source: [detail_basis and retain_current_details](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_judgment.py:158).

This is a financial correctness problem: new evidence may be retrieved but never
reconsidered in the reused case. The correct signature should cover the case's
selected observation versions, related answer/coverage state and decision
dependencies. Unrelated new evidence should not invalidate every case.

### 2. The Whole-Book Context Is Only the Changed Subset

`_enrich_allocation` derives `recorded_allocation` from its input proposal. The
provisional caller has already restricted that proposal to material cases; the
final refresh caller passes only changed cases.

In the saved-run reconstruction, that means **18 of 20 targets and 98.5% of the
portfolio**, not the full book. A regression example refreshing a 10% producer
position beside an unchanged 90% cash position sends a recorded book totalling
**10%, not 100%**.

Sources: [detail context](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:184),
[filtered provisional caller](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:3180),
[changed-case refresh](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:2961).

The builder needs separate inputs for assigned case rows and the complete
canonical weight table. Reducing an essay must not remove portfolio context.

### 3. Splitting Reviews Drops Current-Book Arguments

Before splitting, `proposal_for_review` includes `current_assessment`. The scoped
baseline builder keeps only the executive summary, selected target rows and
weights. It drops the individual reasons to exit, hold or trim current holdings.

Replaying the saved run supplies **zero of the 18 current-assessment rows** to
the split reviewers. All proposed target IDs happen to be covered; that did not
prove that all investment decisions were covered. An exited holding may not be
a target at all.

A second counterexample has only play-related research questions. No general
section is created, so the fallback assignment for an unlinked baseline target
is never used. Its weight is visible, but its investment argument is not reviewed.

Source: [review splitting](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_independent.py:274).

The fix needs an explicit assignment manifest for target cases, existing-position
actions, excluded opportunities and play components, plus an assertion that each
required case is assigned. Smaller packets alone are not a coverage test.

### 4. A Confirmed Credit Rejection Becomes an Unknown Outcome

The runtime persists `submitting` before dispatch. If OpenRouter explicitly
returns 402, `FundingGuard.call` raises before the runtime marks the request
finished. The checkpoint therefore retains `submitting`. On a funded resume,
the uncertain-outcome guard blocks the request before any new provider call.

The integration counterexample uses the actual runtime and funding guard with a
mocked credit API: the first request is explicitly rejected, then the second
request is blocked despite sufficient funding.

Sources: [402 handling](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_funding.py:223),
[submission and exception state](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_runtime.py:568),
[resume guard](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_runtime.py:514).

Confirmed rejection must be distinct from dispatch-with-unknown-outcome. Preserve
the response receipt, release the reservation, and permit the rejected request
to resume after funding. Do not remove the protection for genuinely ambiguous
network failures.

### 5. An Incomplete Number Can Be Misread as a Complete Number

`completed_json_fields('{"summary":"saved","score":1e')` currently returns
`{"summary":"saved","score":1}`. `JSONDecoder.raw_decode` accepts the numeric
prefix; the wrapper does not require a valid terminating delimiter before
retaining it.

Source: [partial-object recovery](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_recovery.py:83).

This contradicts the stated invariant that missing financial values are never
invented. Only lexically complete values should be retained. The preceding
completed fields should remain usable.

### 6. Funding Accounting Uses an Obsolete Task Name

`work_kind("macro_regime:Extract dated observations from source snapshots")`
returns `allocation`, not `extract`. The classifier still recognises the old
`extract source-linked` wording. Focused brief names have changed as well.

Source: [work classification](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_funding.py:37).

This affects historical cost categorisation and subtracting completed work from
the remaining-work estimate. The existing per-dispatch credit check still
exists; this is not a claim that a model output limit was reintroduced. Use a
typed work category in receipts rather than parsing human task titles.

## Why Large Calls Still Exist

### The Original Diagnosis Was Mostly Right

The original profile showed 25 requests above 100,000 input tokens consuming
85.7% of input tokens. There was no infinite model-call recursion. The major
causes were broad evidence propagation, repeated proposal/review representations,
large output schemas and whole-answer repair. Removing an application token cap
does not remove those causes.

The provisional success produced **46,614 completion tokens**, only 2,553 of
which were reported reasoning. The final success produced **47,486**, only
2,350 reported reasoning. Most output was the business document the schema
requested, not hidden thinking. The provisional schema still requests 77 finding
dispositions' worth of work on these saved reviews, research dispositions,
play assessments, current actions and an alternative portfolio alongside targets.

The diagnosis needs two refinements:

- A broad strategic allocation genuinely needs cross-asset context. It does not
  follow that each later case update, writing task or correction needs the same
  detailed ledger. A useful summary of established case conclusions must retain
  accessible supporting and contrary observations.
- The three oil-inventory questions were overlapping, not perfectly identical.
  Their geography, forward horizon and observation-period fields differ. It
  would be wrong to collapse all their meaning into one question. The reusable
  unit is the common underlying measurement, with separate forecast/period
  dimensions researched only where genuinely new.

### Current Request Construction

The following are offline UTF-8 JSON sizes from the current builders, using the
saved final evidence and existing decisions. They are **not billed tokens or
newly generated results**. Earlier-stage probes use later evidence and are not
phase-matched estimates of savings. The saved artifact has no persisted completed
commentary, although the historical profile records its successful call; the
consistency probes below therefore exclude that missing prose.

| Current request | Bytes | Detailed facts | Questions |
| --- | ---: | ---: | ---: |
| Provisional reconciliation, final-ledger probe | 1,004,421 | 578 | 75 |
| Final reconciliation | 1,265,092 | 578 | 75 |
| Memo commentary | 748,792 | 413 | 46 |
| Final consistency, before adding commentary | 1,122,171 | 428 | 69 |
| Hypothetical one-exposure reconsideration | 724,566 | 413 | 46 |
| Settled consistency, before adding commentary | 1,122,138 | 428 | 69 |
| Research planner, final-ledger probe | 636,893 | 578 | 75 |

The six independent reviewer requests are approximately 231-390 KB each in this
replay. Removing cumulative prior sections is real progress, but has not made
them small per-case requests. Splitting still occurs around a character-planning
threshold, and cannot subdivide a single large play into independently assigned
components.

### Remaining Causes, Located in Code

1. **The final reconciler still receives the complete evidence packet.** Its
   1,265,092 bytes include 652,668 of evidence, 247,388 of reviews and 173,480 of
   provisional decisions. Only 39,945 bytes are exact repeated long strings.
   Deleting literal duplicates cannot solve this; the task needs an input model
   based on changes and decisive unresolved issues.
   [Construction](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_independent.py:427).

2. **The provisional output is still a large full-document contract.** The delta
   change applies only to final reconciliation. It reduces the second rewriting
   step, not the first. We still request several model-written representations
   of the same decision rather than deriving repeated accounting views.
   [Schema](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_independent.py:388).

3. **One-exposure reconsideration does not select one exposure's evidence.** Its
   `scope` limits requested changes, but the evidence builder receives `[final,
   consistency]`, and the prompt includes the complete proposal. This is the
   clearest remaining example of a small task receiving a large packet.
   [Caller](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:3288).

4. **Final consistency reintroduces uncompressed financial-check inputs.**
   `consistency_inputs` returns the full `implementation_comparison` under
   `funding`, including copied proposal rows and the alternative. Its
   `recorded_comparators` field is 144,364 bytes in this replay.
   [Comparator builder](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_judgment.py:396).

5. **The writer remains too close to the audit document.** Its supposedly clean
   final recommendation is 220,922 bytes and its evidence is 449,499 bytes. It
   receives research/reviewer dispositions and alternative records alongside the
   decisions it is meant to explain. It is smaller than before, but still an
   unnecessarily broad writing task.
   [Writer input](/Users/Toms_Macbook/Projects/llm-council/scripts/portfolio_positioning_memo.py:3217).

6. **Repair is smaller in output scope, not reliably in input scope.**
   `field_repair_prompt` deep-copies the original prompt and merely replaces its
   schema. A faulty field in `updates` requests the whole `updates` field again.
   Invalid financial totals request all target rows. The original evidence is
   still resent. Local syntax fixes are useful but not a row/claim repair design.
   [Repair builder](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_recovery.py:65).

7. **Question reuse still depends on whole-question identity.** The original
   three inventory questions remain three unmatched cases on replay. The new
   test proved reuse when given the same canonical key and an explicit alias;
   it did not demonstrate measurement-level reuse for the original overlap.
   [Matching](/Users/Toms_Macbook/Projects/llm-council/backend/portfolio_research.py:104).

The raw-vs-clean final evidence comparison happens to select the same facts in
this saved artifact. I have not attributed additional measured growth here to
archived rejected deltas. Passing those raw objects remains a boundary risk, but
it is not necessary to invent that explanation: the whole-case scope is already
enough to reproduce the large calls.

## What Should Happen Next

1. Fix the seven reproduced failures first: credit-state recovery, stale-case
   invalidation, review coverage, complete weight context, numeric completeness
   and typed work accounting. Preserve useful partial analysis in every case.
2. Complete the actual input/output separation: a canonical decision table,
   versioned investment cases, persistent findings and compact cross-portfolio
   context. Final settlement should receive changed cases and unresolved findings;
   evidence remains discoverable by ID. No token ceiling or arbitrary fact cap.
3. Give corrections and prose their own builders. Supply the affected rows plus
   funding counterparts and a complete weight table; derive accounting copies in
   code. Keep research prose/audit history outside the writer's default input.
4. Reuse shared measurements across related questions, without conflating
   forecast versus observed values, periods, instruments or units. The scheduler
   should buy only genuinely missing dimensions.
5. Extend dispatch-level auditing: bytes by field, included IDs and why they are
   relevant, coverage of every required case, reuse/invalidation reasons and work
   category. Replay the entire mocked workflow with representative large data,
   including failures and downstream corrections, before a separately authorised
   paid comparison.

## Verification and Reproduction

The existing portfolio suite still passes: **464 passed, 7 expected failures,
5 SWIG deprecation warnings**. The seven expected failures are newly added strict
counterexamples, not successful fixes. Running them with `--runxfail` produces
**seven assertion failures**, each at the claimed defect rather than a fixture
or network setup error.

```sh
.venv/bin/pytest -q --runxfail --tb=short --show-capture=no \
  tests/unit/test_portfolio_redesign_review.py

.venv/bin/python -m scripts.audit_portfolio_redesign_review \
  outputs/audits/portfolio-full-rerun-20260920/latest.json \
  --output outputs/audits/portfolio-full-rerun-20260920/redesign-review-20260921.json
```

The profiler evaluates trusted repository prompt expressions and serializes
their inputs. It does not invoke the pipeline or any provider. It verifies that
the source artifact is unchanged. Detailed field sizes are retained in the
generated JSON report. This review supersedes the September 20 ledger's claims
of full local completion, not its valid measurements of specific reductions.
