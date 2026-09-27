# Portfolio Source-Check Streamlining

Status: implemented locally, not deployed. The running September 23 recovery has
not been interrupted, resubmitted, or switched to these rules.

## Problem

The current recovery selected 544 of 1,762 archived facts for source checking.
Only 127 were directly cited by the provisional decision or explicit review
challenges. Automatic comparison expansion supplied another 417, including 392
forecasts. A shared economic topic and forecast period was enough to qualify,
even when the subject or metric differed. That produced 68 batches of eight.

Source checks assess whether a retrieved passage supports the stated claim.
They are not new research, independent confirmation of the publisher's accuracy,
or investment judgment. These checks still matter for mismatched units, periods,
table columns, instruments, geography and forecasts presented as observations.

## Changes

1. Select cited decision/alternative facts and explicit factual challenges as
   before. Automatic additions now require a matching metric, benchmark, unit,
   period, observation kind/type, currency, applicability and measurement basis.
   Topic-group membership alone is insufficient. Corrections remain included.
   All other observations stay in the archive and reviewer discovery catalogue;
   analysts can explicitly cite them. No research is deleted.
2. Group claims by their cited source set. Pack up to 16 claims while targeting
   32 KB of additional context beyond one complete source record. This avoids
   sending a large common document once per claim. A large indivisible claim
   keeps its complete context. These are request-packing targets, not output
   limits or text clipping. Full source text and metadata remain intact.
3. Bind completed checks to the observation, source-content fingerprint and
   checking rules/schema, not the model name. Both embedded checks and per-fact
   checkpoint records survive model changes with their original model attribution.
   Legacy model-dependent keys are accepted only if the remainder of their
   contract matches the current rules/schema exactly. Changed sources, values
   or checking semantics still require checking again for versioned checks.
   Existing unversioned historical checks retain their `legacy_unversioned`
   label; they are not relabelled as a new verification.
4. When all cited source text is absent, record an unresolved check in code;
   do not ask a model to certify nonexistent text. Adding that source invalidates
   the fingerprint and reopens the check. This never marks a claim supported.
5. Reused checks are applied before releasing dependent investment-case work.
   Mechanical availability/date/numeric checks and portfolio arithmetic remain
   in their existing deterministic code; no extra agent or mandatory stage.

## Offline Replay

Input: `portfolio_positioning_job_portfolio_recovery_20260923_070012.json`,
read-only snapshot of its evidence, proposal, reviews and original check plan.

| Measure | Previous | Streamlined |
| --- | ---: | ---: |
| Archived facts | 1,762 | 1,762 |
| Direct/challenged facts retained | 127 | 127 |
| Facts selected for checks | 544 | 137 |
| Requests before cache reuse | 68 | 20 |
| Serialized evidence payload bytes | 4,767,687 | 1,005,047 |
| Largest evidence payload bytes | 145,845 | 104,554 |
| Source occurrences across requests | 125 | 60 |

That is 70.6% fewer requests and 78.9% less serialized evidence before reuse.
Tighter selection alone would yield 18 old-style batches, but a largest payload
of 145,895 bytes. The grouped/context-aware packing uses two additional calls
to reduce repeated text and the largest request. This trade-off is explicit.
The maximum 16 claims did not apply on this fixture: groups contain 1-12 claims.

These measurements do not establish elapsed time, token bills, answer quality,
or financial performance. No paid comparison was submitted. Completed checks
may reduce the actual request count further. Future runs may have different
source sizes and dependencies; 20 is not a fixed request allowance.

## Verification

Final full unit suite: **792 passed**, five existing SWIG deprecation warnings.
Focused correctness lint (`F,E9`) and `git diff --check` pass. The first full
pass found one old assertion requiring a model swap to repeat source checks;
it was replaced with a regression requiring reuse with original attribution,
then a fresh check when the fact value changes. The complete suite was rerun.
No frontend changes or paid model calls were made in this pass.

The replay asserts input hashes unchanged, all direct/challenged dependencies
retained, every selected fact packed exactly once, and complete cited source
records preserved. Reproduction:

```sh
.venv/bin/python scripts/audit_portfolio_source_checks.py \
  outputs/audits/portfolio-credit-recovery-20260923/source-check-input.json \
  --output outputs/audits/portfolio-credit-recovery-20260923/source-check-streamlining.json
```

Regressions cover source grouping, long documents, multiple-source claims,
different periods/units/geography/instruments, opposing measurements, explicit
citations and corrections, checkpoint and embedded-check model swaps, old-key
compatibility, changed source/value/rules, and absent-source deferral/reopening.

## Limits

Exact structured comparison is intentionally conservative: semantically similar
metric labels may not auto-match. Reviewers still have the observation catalogue
and can cite additional contrary claims directly. This is not a claim that
opposing research is exhaustively identified or that sources are independently
corroborated. No new taxonomy, semantic matching model or verification loop was
added. Other review-workload issues in the architecture ledger remain separate.
