# Portfolio Remediation Follow-Through

Status: local implementation, not deployed. No paid request, model-route change,
credit purchase, or restart of the stopped recovery. The original artifact and
checkpoints remain unchanged. This follows the September 23 completion review;
it does not replace the historical diagnosis with a claim that the failed run
finished.

## Reproduced Defects

| Defect | Change | Acceptance |
| --- | --- | --- |
| C01 Received result lost on SIGTERM | The real worker entry point handles SIGTERM, closes admission, cancels the owning task once and drains durable writers before exit. Boundary writes also retain their lock until the writer settles. The existing ten-second forced-stop fallback remains. | A real subprocess receives a fake response, pauses its writer and is stopped through the production job cancellation function. The result survives checkpoint loading. This does not claim to cancel an already accepted remote request. |
| C02 Embedded review bypasses contract invalidation | Embedded and cached checks preserve rules/schema contracts and original model provenance through merging and signed-evidence refresh. September 23 streamlining intentionally removes model choice from validity: unchanged evidence can retain its prior checker. Changed evidence/rules still invalidate checks. Historical unversioned checks remain labelled `legacy_unversioned`. | Returned evidence survives a model change without another call; changed values and rules require a new check. Old model-dependent keys are accepted only against matching rules/schema. See [streamlining](portfolio-source-check-streamlining-20260923.md). |
| C03 Existing ID mistaken for supported economics | An observed causal link requires source-supported, non-superseded observations, not merely IDs present in the archive. | The unresolved-observation counterexample produces a case limitation without changing weights or inferring a sell. |
| C04 Harmless names treated as identity conflicts | Same-name miner/producer singular/plural and equity suffix variants are recognised. Commodity and instrument words remain significant; explicit aliases remain supported. | Gold miner equities versus Gold Miners passes; genuine bullion/miner and bond/infrastructure conflicts remain flagged. |

The four original counterexamples are normal regression tests, not expected
failures. The reproduction descriptions in the completion review are historical.

## Workflow Changes

```text
Independent source orientation and premise research
                |
       +--------+----------------+
       |                         |
Sealed ideal proposal    Current-exposure research and proposal
       |                         |
       +------------+------------+
                    |
           Plays and focused questions
                    |
        Two independent review roles
        (two ready sections each; four shared model slots)
                    |
         Provisional funded recommendation
                    |
         Material unanswered questions
                    |
     +--------------+--------------------+
     |                                   |
Two source-check workers        Two investment-case workers
     |                          Each starts when its own
     +-- completed fact IDs --> dependencies settle
     |                          Failed checks remain qualified
     +------------------+----------------+
                        |
                  Final settlement
                        |
         Recompute changed source dependencies
         (including opposing forecasts/corrections)
                        |
           Refresh only changed investment cases
                        |
          Commentary and final consistency check
                        |
        At most the existing targeted reconsideration
                        |
               Existing memo renderer
```

No extra analysis role or recursive research loop was added. Settlement still
waits for the selected material dependencies. The removed barrier is the blanket
requirement for every selected source batch to finish before *any* investment
case starts. A case can legitimately depend on many observations; its scope is
not silently reduced to meet a batch target.

Final settlement, factual correction and post-review decision changes now use
the same dependency selector as the provisional recommendation. The full small
workflow test adds a new final forecast and confirms that its opposing forecast
also enters source checking. It runs with and without a decision revision and
with small and large evidence archives, including checkpoint reuse.

The work plan records all major stages, dependencies, required versus optional
work, known request counts and pending scope. Large fact-ID inventories stay out
of the progress projection. Completed workflows report zero remaining work;
unfinished downstream scope does not receive an invented time estimate. This
is not yet a calibrated whole-run ETA or a guaranteed quote for optional work.

## Persistence and Source Context

- Research results, provider identities/reservations, citation extractions,
  publisher context and document-inspection results use durable record events.
  They no longer require a complete artifact rewrite for each result.
- Async boundary snapshots copy their JSON graph cooperatively. Submission
  guards are frozen before yielding, and the durable writer is drained on
  cancellation. Large final artifacts still require materialisation.
- Publisher sections and inspected observations are restored on resume, at
  their original information boundary. They cannot leak plays into the blind
  independent proposal.
- Requested HTML context now retains table cells, row/column spans, captions,
  heading hierarchy and adjacent qualifications. PDF coordinate alignment is
  retained. Metadata dates are not invented as observation dates. A failed or
  unsupported document fetch preserves the original excerpt.
- This is selective document inspection, not a general browser/crawler. Dynamic
  pages, arbitrary structured downloads and ambiguous visual tables can still
  remain unresolved. The code must retain that limitation rather than claim
  complete publisher coverage.

## Financial Changes

- Research planners can identify the decision consequence and whether a question
  concerns earnings, valuation, hedge mechanics, physical supply or merely a
  quote. Within the same materiality tier, consequential economics takes priority
  over a quote refresh. This is not a commodity allowlist or a forced conclusion.
- Explicitly equivalent exposure IDs can share a review case. Substitutes and
  partial overlaps cannot. Review grouping does not merge their capital.
- Current, independent ideal, smaller-change and final weights are assessed
  against the same named scenario definitions. Hypotheses and unsupported
  assumptions stay labelled; missing sensitivities are not converted into
  numerical returns. Common-factor directional weights are not loss estimates.
- Unchecked, superseded or contradicted observations cannot automatically
  trigger monitoring. Source support, publication availability, series identity
  and persistence remain distinct tests.
- Corrected-premise sizing, causal links and opportunity costs feed the existing
  case and final-review stages. These mechanisms identify missing economics;
  they do not manufacture valuation research or certify financial prose.

## Production-Sized Offline Acceptance

Command:

```sh
.venv/bin/python scripts/audit_portfolio_workflow.py \
  outputs/audits/portfolio-r360-review-20260922/stopped-recovery.json \
  --output outputs/audits/portfolio-r360-review-20260922/workflow-acceptance-20260923.json
```

The input is the actual 24,440,094-byte stopped artifact, with 947 observations.
Its SHA-256 remains
`eebf7815a78f3c9d80dc31ea6313e2479397219e7a12dc0053353d4b290c2b09`.
The harness starts from its retained research, then exercises real downstream
orchestration, validation, source checks, cases, settlement, consistency,
reconsideration, persistence and memo rendering. All provider responses are
synthetic or retained fixture values. Network access is prohibited.

The measured replay reaches a rendered memo with a 100% allocation, overlaps
case work with source checks, survives an injected terminal source-check error
and five supplementary research failures, and revalidates all 95 completed
model requests through a reopened checkpoint without contacting a provider.
There are 100 recoverable cache entries, including research results. The JSON
report records request counts/bytes, timelines, writes and memory, not just a
pass count. Peak harness memory includes original and resumed runtimes in the
same process; it is not a production-worker memory estimate.

The 125,917-character rendered fixture memo proves output survives; it is not a
new financial conclusion, a readability score, or approval of that length.
The harness does not exercise live retrieval latency or model judgment. Real
SIGTERM, interrupted writes, uncertain accepted requests and storage failures
are covered by separate focused fault tests, not claimed as every combination
inside the full replay.

Latest saved replay: 141.61 seconds, four peak active model requests, 37 full
boundary writes and 320 incremental events (1,001,266 event-manifest bytes).
Pipeline peak RSS before reopening the checkpoint: 477,073,408 bytes. Whole
harness peak with both runtime instances: 818,585,600 bytes. These are local
simulator measurements, not expected live request durations or Fly memory.

Verification on September 23:

- Full unit suite plus portfolio memo integration tests: **739 passed**, five
  existing SWIG deprecation warnings, 233.61 seconds.
- Final focused cancellation/workflow/recovery/persistence suite: **28 passed**,
  including the strengthened actual `_async_main` subprocess test. It confirms
  exit code 130, a cancelled reader artifact and the retained received result.
- Four full-workflow variants pass with final-source/opposition selection,
  decision revisions, small/large evidence and reused checkpoints.
- Focused Python correctness/unused-import lint and `git diff --check` pass.
- This pass makes no frontend layout changes. Historical browser results are
  not presented as a newly performed visual review.

## Audit Disposition

| Item | Current disposition |
| --- | --- |
| A00 | Stopped recovery preserved; no restart. |
| A01 | API/UI stop plus real worker signal/drain regression implemented. Provider-side acceptance/charging cannot be undone locally. |
| A02 | Major-stage dependency/admission plan and source/case scheduler implemented. Calibrated whole-run ETA remains unestablished. |
| A03 | Hot result/provider/extraction/document transitions are incremental; cooperative boundary copying and durable drain tested. Full artifact boundaries still exist and are measured. |
| A04 | Exact and explicitly equivalent economic cases group; partial/substitute relationships do not. Ambiguous semantic identity remains unresolved by design. |
| A05 | Versioned cache/embedded reuse, incremental source completion and consistent final-dependency selection tested. Historical broad reviewer references still require substantial checking. |
| A06 | Economics-priority metadata, source-section reuse and within-tier ordering implemented. Live research adequacy/spend distribution requires evaluation, not assertion. |
| A07 | Funding/uncertain-outcome safeguards retained; offline supplementary failure, resume and cancellation regressions pass. No historical uncertain ID resubmitted. |
| A08 | Explicit identity/equivalence and label precision improved. Existing component inventory and completeness tests retained; ambiguous mapping is not silently resolved. |
| A09 | Source-supported causal links and changed-premise case checks implemented. Substantive valuation and sizing quality require a real model-output audit. |
| A10 | Shared-scenario four-view comparison implemented, with explicit unknown returns and funding checks. |
| A11 | Whole-stage plan and compact progress projection supplement existing timing, deferral and usage accounting. No false promise of remaining time or cost. |
| A12 | HTML/PDF context, context recovery, contract provenance and monitoring support added to existing typed-date/correction/funding regressions. Universal document parsing is not claimed. |
| A13 | Existing presentation preserved and final rendering exercised. No new paid final memo to score against the legacy memo. |
| A14 | Large downstream replay, completed-request recovery and focused fault tests implemented. Live latency, standalone production memory and financial-quality acceptance remain separate gates. |

## Next Acceptance, Not Automatic Work

Do not deploy or buy a run on the strength of test count alone. Before a separately
authorised live comparison, disclose the admitted workload, unresolved optional
scope and available credit. Compare actual producer economics, hedge mechanics,
play debate, changed-premise sizing and final readability with the prior and
legacy memos. Report provider time, persistence time and attempts separately.
No numerical market assertion or optimistic runtime estimate is inferred from
the offline simulator.
