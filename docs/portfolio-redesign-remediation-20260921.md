# Portfolio Request Redesign: Second-Pass Remediation

Implemented and deployed on September 21. This follows
[the independent review](portfolio-redesign-review-20260921.md) and supersedes
its open implementation statuses, not its historical findings. No paid model
call or modification of a saved production run was performed.

## Diagnosis

The large calls were primarily a request-contract problem, not infinite model
recursion or excessive hidden reasoning. The original provisional/final answers
contained roughly 44,000-45,000 visible completion tokens because the schema
asked for repeated decision, disposition, comparison and alternative records.
Broad evidence and accumulated decision documents then travelled to stages
whose work was much narrower. Whole-field repairs repeated this cost.

The second audit also found real correctness defects: omitted review cases,
stale detail reuse, incomplete funding context, accepting a numeric prefix from
truncated JSON, and incorrectly treating a confirmed credit rejection as an
uncertain paid submission. Those defects are now ordinary passing regressions,
not expected failures.

## Implemented Changes

| Ledger | Implementation and verification |
| --- | --- |
| R01 | Evidence projection remains idempotent. The new observation table retains values, provenance, adverse source checks and fact aliases; identical source passages are represented once and reconstructed losslessly. |
| R02 | Corrections select affected decisions and named funding counterparts. The complete weight table remains visible. Archived rejected candidates no longer reintroduce a whole previous portfolio. |
| R03 | Case hashes include related observations, contrary evidence, question answers and source metadata, rather than just old citations. Both initial and refreshed detail batches receive all portfolio weights. Reuse/invalidation reasons are recorded outside the reader document. |
| R04 | Existing identity, allocation-range and funding checks remain. Grouped findings expand deterministically; duplicate conflicting dispositions stay unresolved. No missing financial values are invented. |
| R05 | Research dimensions have explicit measurement identities: subject, measure, region, observation period, basis, unit, instrument and vintage. Investment horizon does not create another copy of a historical observation. Shared dimensions are bought once per search wave and answers are distributed to their consuming questions. Completed unavailable measurements are not bought again at the same cutoff. |
| R06 | Focused answer contracts and durable source-extraction reuse remain. Successful supplementary research survives other failures. |
| R07 | Review assignment explicitly covers every target, current-position action, excluded opportunity, portfolio argument, play component and otherwise unassigned research question. The dispatcher checks case coverage. Complete weights provide cross-portfolio context; earlier review prose is not accumulated. |
| R08 | Targets are canonical decisions. Reconciliation reference tables and numeric comparison references are derived in code; common finding dispositions can share one explanation. The smaller-change alternative has a weight-and-justification contract. Final settlement sees changed cases and pending findings. Writer inputs omit audit disposition tables; consistency checks use compact arithmetic/funding records. |
| R09 | Truncated numeric prefixes are rejected while preceding complete fields survive. Invalid row fields receive exact-path patches, with full funding weights and scoped evidence. Unassigned paths cannot overwrite valid rows. A missing whole supplementary section uses a separate compact repair context, not a copy of the original request. |
| R10 | Each actual dispatch records field bytes, included evidence IDs and selection scope. Streaming journals flush on a timer, including during provider silence, and preserve events arriving during disk writes. Duration/idle warnings are observational: they neither cancel nor resubmit requests. |
| R11 | Confirmed HTTP 402 responses close the request as rejected and preserve a receipt, allowing recovery after funding. Uncertain submissions remain protected against duplicate spending. Receipts carry typed work categories rather than relying solely on task-title matching. |
| R12 | All portfolio regressions and the mocked full workflow pass. Larger end-to-end fixtures exercise 350 additional observations and 75 research questions, targeted corrections, resume, and changed plays. Both saved-run payload audits complete without modifying the original artifact. |

Implementation centres on `backend/portfolio_requests.py`,
`backend/portfolio_independent.py`, `backend/portfolio_research.py`,
`backend/portfolio_recovery.py`, `backend/portfolio_runtime.py`,
`backend/portfolio_judgment.py` and `scripts/portfolio_positioning_memo.py`.

## Current Flow

```text
Initial source discovery -> citation extraction -> persistent evidence archive
                                    |
            Measurement-aware research planning and missing-dimension search
                                    |
             Independent ideal (no holdings or submitted plays)
                                    |
             Current-book assessment (no ideal or submitted plays)
                                    |
             Submitted-play research and explicit component inventory
                                    |
       Concurrent assigned reviews + at most one archived-source lookup each
                                    |
              Canonical provisional portfolio + grouped findings
                                    |
              Material unanswered questions, reusing measurements
                                    |
              Case-specific investment details + complete weight table
                                    |
              Final settlement: changed cases and pending findings
                                    |
              Reader commentary -> financial claim consistency check
                                    |
       If warranted: one scoped decision correction, affected details/prose
                                    |
                    One settled-document check -> saved memo
```

Every model dispatch has its own receipt. Repairs are bounded by the existing
attempt policy; the workflow does not recurse until models agree. Raw responses,
unapplied candidates, source observations and journals remain inspectable in the
archive. They are not automatically reinjected into subsequent requests.

## Saved-Run Measurements

The comparison uses the same saved evidence and decisions as the second audit.
These are serialized UTF-8 JSON **bytes**, not measured token spend or latency.
Provisional/planner probes use the final ledger, not phase-matched historical
inputs. The consistency probe excludes missing historical commentary.

| Request | Before this pass | After | Reduction |
| --- | ---: | ---: | ---: |
| Provisional, final-ledger probe | 1,004,421 | 891,852 | 11.2% |
| Final settlement | 1,265,092 | 621,542 | 50.9% |
| Memo writer | 748,792 | 560,069 | 25.2% |
| Final consistency, excluding missing prose | 1,122,171 | 742,947 | 33.8% |
| One-exposure correction | 724,566 | 103,783 | 85.7% |
| Planner, final-ledger probe | 636,893 | 461,278 | 27.6% |

Final settlement is 59.0% smaller than the original paid request's 1,515,539
bytes. Its replay includes 362 detailed observations and 35 related questions;
the one-exposure correction includes 39 observations and four questions.
The archive still contains **578 facts, 100 sources and 75 questions**.

All nine independent targets, all 19 current-view targets and all 18 current
assessment rows are assigned. Reviewer requests remain three parts per role,
approximately 121-400 KB each, now including previously omitted arguments.
Review batching groups work; it never truncates an oversized individual case.

The wider replay is in
`outputs/audits/portfolio-full-rerun-20260920/redesign-remediation-20260921.json`.
The component benchmark is in the same directory as
`redesign-components-20260921.json`. Both scripts assert archive immutability.

## Verification and Limits

The full portfolio suite passes **490 tests**, with five existing SWIG
deprecation warnings. Seven former audit counterexamples and 17 additional
remediation tests cover credit recovery, source preservation, coverage,
measurement reuse and separation, scoped repairs, dispatch accounting and
silent-stream persistence. Larger full-workflow fixtures also verify exact
checkpoint reuse and that changing plays does not regenerate the two baselines.

```sh
.venv/bin/pytest -q --tb=short --show-capture=no tests/unit/test_portfolio*.py \
  tests/integration/test_portfolio_positioning_memo.py

.venv/bin/python -m scripts.audit_portfolio_redesign_review \
  outputs/audits/portfolio-full-rerun-20260920/latest.json \
  --output outputs/audits/portfolio-full-rerun-20260920/redesign-remediation-20260921.json
```

No application output-token ceiling was added. No model assignments, provider
tiers, memo layout or financial conclusions in saved runs were changed.

Live verification is still necessary for generated judgment quality, actual
output length, grouped-disposition quality, provider timing and spend. Strategic
requests remain substantial; smaller bytes do not prove better investment advice.
The credit preflight still uses an approximate historical workload profile, not
a guaranteed current-run quote. Per-request credit checks remain separate.

Old inventory questions without measurement bindings are deliberately not merged
by guessing from prose. New planners provide explicit dimension bindings or
reuse existing source-linked answers. Tests establish that shared historical
measurements can serve different questions and horizons without merging their
forward-looking premises; a paid model comparison is needed to assess how well
the planner makes those bindings on real research.

## Deployment Verification

Deployed to `llm-council-analysis` as Fly release **356** on September 21,
2026, following the user's separate deployment request. Image:
`deployment-01M30Q242C734JW562ZC9SND5Z`, digest
`sha256:0215d750c7d5e7b207c4024ae05bc913e92749bc67dd34336c031f59ad96897c`.

- Fly health checks pass; public readiness, the portfolio page and its JS/CSS
  assets return HTTP 200.
- All 26 portfolio runtime manifest entries match the tested local sources.
- The authenticated memo list returns 28 runs; a saved memo loads successfully.
- All 21 underlying memo files included in the pre-deployment snapshot retain
  the same aggregate SHA-256. Persisted and effective model routing hashes are
  unchanged, with no configuration errors.
- No queued or running analysis existed before or after deployment. No paid
  comparison was started; the financial-quality checks above remain outstanding.
- The data volume has approximately 256 MB free. No files were deleted and no
  volume resize was performed; additional capacity should precede a large run.
