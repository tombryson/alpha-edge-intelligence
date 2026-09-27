# Portfolio Decision Remediation

Implemented locally on `codex/portfolio-decision-remediation` in LLM Council
and Trading Terminal, September 18-19, 2026. No deployment, live model change,
paid rerun, or modification of a historical memo was performed by this build.

## Decision Flow

1. Load the explicit investment brief. Missing scope remains unspecified.
2. Research the market independently of holdings and submitted plays.
3. Save the independent ideal, then the separately formed current-book view.
4. Both existing reviewers critique both views and each economic leg of plays.
5. Reconciliation records finding dispositions, explicit exposure relationships,
   questions already answered by saved evidence, and material research gaps.
6. Focused, checkpointed retrieval addresses the remaining high-impact questions.
7. Review provisional investment cases; reconcile the final destination and a
   concrete smaller-change alternative. Refresh only stale/new investment cases.
8. Compute funding, turnover, baseline comparisons and supported arithmetic.
   Evaluate supplied scenario/monitoring inputs without inventing risk estimates.
9. Save the final proposal before commentary and final claim review. The existing
   defensive-review model checks factual corrections, not a new whole allocation.
10. Render through the existing memo structure. Technical review stays in the
    collapsible supporting analysis, not ahead of the memo.

## Changes By Finding

| Finding | Implementation |
| --- | --- |
| Ling rejected JSON mode | Normalise hyphenated/underscored provider errors. Retry the same model without the unsupported format option. Preserve both receipts, requested/resolved model and provider. No model substitution. |
| Portfolio scope was assumed | Persistent optional brief in Trading Terminal's analysis dialog using existing settings storage. Scope/objective, currency, horizon, liquidity/drawdown limits, tax/FX policy and restrictions flow into every new run. The alternate exposure-page entry also loads the brief. |
| Ideas were treated as one bundle | Review and final schemas request separate economic legs, mechanisms, pricing, contrary evidence, confidence, action and questions. Unresearched legs have no fabricated neutral score. Reader shows partial adoption and individual legs. |
| Research considered only the provisional view | Union questions from both starting views, both reviewers and play legs; exact-question deduplication retains affected exposures/plays. Reconciliation can resolve a question using named saved facts. |
| Three-question truncation | Explicit cost/time envelope, with decision-impact ordering, five initial sources, concurrent independent requests, conditional expansion and separate results/checkpoints. Missing/rejected/late research qualifies the decision; successful work survives. |
| Fact identifiers changed after extraction | Observation identity is independent of source content. Preserve historical stable IDs, source variants and aliases. Changed content invalidates source-check fingerprints, not citation identifiers. Colliding lane-local IDs are relinked locally, never globally guessed. |
| Cash comparisons disappeared | Explicit equivalent/overlapping/substitute relationships between each target and ideal/current/holdings. Reference weights are computed, not copied from prose. |
| Risk overlap could look like capital | Substitutes never inherit current weights. Partial holdings attribution requires an explicit verified capital component, not common factor exposure. Duplicate attribution is surfaced. Known incompatible instrument types cannot count as equivalent. |
| Financial quantities conflated | Measurement metadata carries period, annualisation, horizon, inflation index and nominal/real basis. Typed mismatches are recorded at the claim. Midpoint/difference calculations use actual numeric facts. Unknown inputs are not inferred. |
| Factual corrections ignored | Findings have stable IDs and accepted/rebutted/unresolved dispositions. One bounded final check can patch exact prose fields only, never weights, identifiers, scores or verdicts. Original text, reason and evidence are retained. |
| Final investment cases were stale | Reuse requires unchanged decision assumptions, expression and linked evidence. Changed cases are reassessed in existing batches; previous details never overwrite final decisions. New final/patch citations receive source review. |
| Destination treated as trade justification | Hold/smaller-change/chosen-case reasoning, cost assumptions and conditions are recorded separately. Funding and turnover are computed for destination and the explicit alternative. Existing scenario code is used only with supplied assumptions. |
| Final result vulnerable to late failure | Save final proposal and readable memo before optional commentary/claim checks. Existing credit recovery and per-stage records remain in place. |
| Duplicated executable pipeline | Root `portfolio_positioning_memo.py` is now a compatibility entry point to `scripts/portfolio_positioning_memo.py`. Imports, tests and production execute the same module. Both paths enter the provenance manifest. |

## Research Envelope

`PORTFOLIO_FOLLOWUP_BUDGET_USD` defaults to 7.20 and
`PORTFOLIO_FOLLOWUP_SECONDS` to 1800. At the current ultra4x discovery estimate
of $1.20/task this permits six discovery tasks, including expansions. This is
not a six-question guarantee, a required minimum, or the cost of the full run.

Prices are from [Parallel's published pricing](https://parallel.ai/pricing),
checked September 18. `PORTFOLIO_FOLLOWUP_TASK_PRICE_USD` can override the
estimate when pricing changes. This envelope excludes citation extraction,
OpenRouter and other providers. It is an application scheduling estimate, not
a provider-side spending reservation. A local polling timeout does not cancel
an already-submitted provider task; its ID remains resumable.

OpenRouter preflight now includes the bounded final claim review and potential
refreshed detail batches. Estimates remain estimates; retries and external
provider charges are not guaranteed by that check.

## Controlled Repair

The new API option `preserve_portfolio_baselines: true` may accompany
`reassess_portfolio_run_id` on a new portfolio job. It is not enabled implicitly.
It requires the original version-three checkpoint and artifact. The two saved
starting views and saved evidence are reused; only downstream review/research
and decisions are rebuilt. Source hashes and baseline hashes link the new
artifact to the old. Changed holdings or mandate are rejected for this mode;
those require a genuinely new analysis. Output cannot overwrite the source.

The original research cutoff is retained by checkpoint recovery. Source dates
and observation dates remain separately checked. Unknown historical vintage
must remain uncertain: a repaired decision is not automatically a perfect
point-in-time experiment. Frozen baseline errors are treated as errata in the
reconciliation, never silently rewritten and called independent.

## Verification

- Initial portfolio and Model Routing unit/integration suite: 337 passed on that
  code, including the mocked end-to-end baseline-preserving repair.
- Nine Trading Terminal browser scenarios passed, covering optional plays,
  saved brief persistence, original-job payload, failed storage, retry and
  concurrent edits/deletion. No real settings or analysis jobs were written.
- Three brief normalization/round-trip tests passed. SQLite close/reopen test
  confirms the brief and plays persist without overwriting other settings.
- Trading Terminal TypeScript check passed.
- Council production frontend build passed, with its existing bundle-size warning.
- Council reader checks passed across desktop/tablet/mobile and both themes;
  two portfolio tables and lazy supporting analysis remain intact.
- New regression cases cover the actual Ling message, stable fact IDs, cash
  mapping, non-equivalent bullion/miners, duplicate capital, query reuse,
  GDP/PCE/CPI/nominal comparisons, exact patches, stale details and frozen repair.

## September 19 Audit Corrections

The initial test pass did not cover six material failure paths. The follow-up
implementation addresses them without changing the memo layout, replacing models,
deploying, or making paid research calls:

- Holdings capital can be attributed only through the existing exposure identity,
  an alias supplied by the input book, or a book-supplied component with its exact
  capital share. A model's equivalence assertion or `capital_component: true` is
  not verification. Unknown mappings remain visible and do not report zero turnover.
  Snapshot construction preserves the supplied implementation/identity metadata.
- Failed or empty detail refreshes cannot certify old reasoning. Stale cases are
  archived separately, and current status requires a successful substantive response
  tied to the decision and its evidence. Unchanged cases retain that provenance.
- Computed comparisons now enter final reconciliation. The existing final reviewer
  can request one scoped reconsideration, including explicit funding counterparts.
  Unrelated decisions and both baselines remain unchanged. Bad, unbalanced or failed
  revisions retain the original proposal and qualify the affected decisions. Changed
  decisions are checkpointed before optional detail/commentary work; superseded prose
  is not republished. The preflight estimate includes this conditional work, not a
  mandatory extra council.
- Accepted factual findings need a separate reviewer check pointing to the current
  corrected text and available supporting fact IDs. Acceptance alone does not close
  a finding. This is traceable model review, not proof of semantic truth.
- Play components identified by the existing reviewers are saved under stable IDs,
  grounded in quotations from the submitted idea. Their union survives reconciliation;
  omitted components receive explicit unassessed entries. If no decomposition arrives,
  the system does not present a blended score as a complete assessment. Understanding
  every component of free text still requires model/human judgment; it is not a
  deterministic financial-language parser.
- Empty or one-sided measurement metadata is unresolved. Arithmetic checks economic
  measure, benchmark where applicable, units, currency, observation date, measurement
  basis and differing release vintages. An alternative with greater turnover is
  flagged and is not labelled a smaller change in the reader.
- Supplementary observations and source records survive a failed or exception-raising
  reconciliation step. They remain available to the allocator, explicitly unreconciled;
  retrieval success is separate from whether the investment question is resolved.

Regression coverage includes the full miners-to-bullion false-zero-turnover case,
failed refresh with stale prose, missing play components, unrelated percentage
arithmetic, correction closure, scoped funded revisions, failure rollback, failed
supplementary synthesis and checkpoint reuse after a revised decision. Browser checks
retain both portfolio tables, lazy research, light/dark themes and the existing layout.

Final verification for this follow-up pass: 352 portfolio/Model Routing tests passed,
11 frontend API-auth tests passed, and the independent-reader browser test passed
at 1440/768/390px in both themes, including the new decision-review warnings.
The frontend production build passed with the existing bundle-size warning.
No production deployment, paid analysis, or historical artifact rewrite was performed.

Offline audit command:

```sh
.venv/bin/python -m scripts.audit_portfolio_decision_remediation \
  outputs/audits/portfolio-plays-review-20260918/latest.json \
  --output outputs/audits/portfolio-decision-remediation-20260918/offline-audit.json
```

The original run has 285 facts, one missing final fact reference, a failed Ling
review, two plays with no per-leg assessments, and no investment brief. The
offline regression preserves all 285 observation IDs after source refresh and
leaves the source artifact unchanged. The local fixture lacks 56 raw record
sidecars; the report discloses this rather than claiming a complete raw-log audit.

## Remaining Evaluation

No paid repaired run has been executed. That is the remaining empirical test:
recover Ling, resolve material questions, compare the linked new memo with the
original using the same brief and frozen starting views, then assess correction
survival, financial judgment, actual cost and runtime. Schema/tests establish
software behaviour, not superior investment returns or the truth of every claim.

The portfolio-scope preference is still unspecified until the user supplies it.
Do not manufacture risk sensitivities, tax lots, valuation evidence or a mandate
to make the output appear complete. Missing material information remains local
to the affected decision rather than invalidating the entire memo.
