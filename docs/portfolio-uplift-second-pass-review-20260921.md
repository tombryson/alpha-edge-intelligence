# Portfolio Uplift: Second-Pass Review

## Remediation Status

**R01-R09 are fixed and deployed in Fly release 360.** All nine original offline counterexamples now pass, including inside the production image, and 30 regression cases cover them and adjacent merge, recovery, correction, scenario and monitoring failures. The original audit below is retained as the record of what was broken, not a description of the current implementation. See [the deployment record](./portfolio-uplift-implementation-20260921.md#deployment-record).

| Finding | Repair and verification |
| --- | --- |
| R01 Typed review | Reviewer validation, recovery and support predicates share the present typed fields, including periods, measurement basis, instrument applicability and table locators. Contradictions cannot be called supported. Missing optional metadata remains a limitation, not a reason to discard the memo. Recovery also preserves proposed source-based corrections. |
| R02 Supersession | Canonical correction edges survive merge order and raw-source restoration. Reviews are reused only against the matching current source fingerprint; changed source text requires revalidation. Correction chains reach scoped evidence packets. |
| R03 Play inventory | Completeness is assessed against the original submitted idea before freezing, with a receipt bound to the input and components. Partial inventories receive one focused repair; unsuccessful repairs retain recognised components. A later source-grounded omission invalidates the receipt. Semantic completeness still depends on the reviewing model, not a hardcoded commodity parser. |
| R04 Inspection retention | Each successful inspection is checkpointed as active phase evidence before further discovery. Discovery/extraction failures and restoration retain those facts, citations and answered dimensions without falsely marking unanswered dimensions searched. |
| R05 Funding explanation | Funding arithmetic and declared-source validity have separate statuses. Invalid funding explanations reach existing decision checks and reviewer context; a balanced allocation is not discarded. |
| R06 Prose corrections | Checker paths and patch application use the same current-document projection, including sleeve rationales and scenario assumptions. Exact-text/hash guards remain; weights, identities, scores and archived cases cannot be changed by a prose patch. |
| R07 Scenarios | Partial numerical scenarios retain supplied qualitative direction and reasoning. Actual calculations remain intact; missing outcomes stay unknown rather than becoming invented returns. |
| R08 Monitoring | Equivalent timestamps are one observation. Conflicting values at any required point and unknown timestamp offsets cannot falsely satisfy persistence. Genuine distinct observations still work. |
| R09 Attempt timing | Token/content timestamps, request identity and character counts reset per attempt while receipts remain archived. Provider completion is measured separately from local completion work. |

The wider uplift is **not** declared complete: the additional design scope and controlled financial-quality comparison below remain open. No deployment, paid calls, model changes, output-token caps, UI redesign or checkpoint deletion were part of this repair.

### Repair Verification

- Full unit suite: **655 passed, 5 warnings, 129.23 seconds** (`.venv/bin/pytest tests/unit -q --disable-warnings --maxfail=10`).
- Original independent audit: **9/9 pass**, exit 0 (`.venv/bin/python -m scripts.audit_portfolio_uplift_second_pass`). The original probes are also exercised by the regular regression suite.
- Adjacent redesign, research and handoff modules: **65 passed**.
- Focused Python correctness lint (`ruff check --select F,E9`) and `git diff --check` passed after removing an unused test import.
- No browser or frontend build rerun in this backend-only repair. Existing reader verification is historical, not a claim of a new browser check.

## Original Audit Verdict

The uplift is **not complete**. The execution changes and several core helpers are implemented, but nine reproducible defects remain. The earlier ledger used "Implemented locally" too broadly: it sometimes meant a helper existed and its positive test passed, rather than the full acceptance condition held through extraction, merge, recovery and publication.

This is an audit of local code, not a claim that these nine counterexamples all occurred in the last paid memo. No production implementation was changed, no deployment was made, and no paid provider calls were made in this review.

## Original Audit Verification

- Existing full unit suite rerun: **625 passed, 5 warnings, 143.35 seconds**.
- New independent offline audit: **nine of nine acceptance probes failed** against the code at review time; all nine now pass after the repair above.
- Audit script correctness lint passes. The probes mock all research/model calls and use in-memory runtimes.
- Run with `.venv/bin/python -m scripts.audit_portfolio_uplift_second_pass`. Exit status 1 means at least one acceptance probe remains unresolved, not a provider failure.
- The previous six browser checks and frontend build establish compatibility of the saved-content reader. They do not prove new financial analysis is better. They were not rerun in this backend audit.

## Original Findings

### R01 / P1: A contradicted reporting period can still be source-supported

**Location:** `backend/portfolio_evidence.py:73`, `:89`, `:190`.

The extraction schema now includes reference period, forecast target period, availability, applicability and measurement details. The reviewer schema still uses the old `FACT_FIELDS`. `observation_fields()` removes the old observation-date requirement when a reference period exists, but does not replace it with a reference-period check.

**Reproduction:** the source says Q2 earnings; the normalized fact says Q3. Even explicitly returning `checks.reference_period = unsupported` produces `claim_status = supported` and `fact_observation_is_supported(...) = True`.

**Impact:** a number can be verified against the wrong quarter or forecast horizon. Correction acceptance and downstream finding closure use that same support predicate.

**Required repair:** make the reviewer, support predicate, correction validator and projected review dimensions share a type-specific field contract. A contradicted period or instrument is material; unknown optional release metadata must still remain a nonfatal limitation. Do not restore a universal mandatory-field gate.

### R02 / P1: A later merge can erase a recorded supersession

**Location:** `backend/portfolio_evidence.py:383`; recovery also merges raw research through `backend/portfolio_research.py:90`.

`merge_briefs()` unions question/comparison relationships but otherwise takes the later fact row. It does not preserve `superseded_by` from an earlier reviewed record. The older review can also disappear when the later raw copy lacks the normalized source digest.

**Reproduction:** correct the August Brent observation from 82.6 to 90.9, then merge a raw copy of the original observation. The old row loses `superseded_by`; the new row retains `supersedes`, leaving the relationship inconsistent.

**Impact:** subsequent restoration or merging can present a retired premise without its retirement marker. The new corrected record is not deleted, but the original can look like another active observation rather than a superseded one.

**Required repair:** merge immutable observations separately from their versioned reviews and correction relationships. Preserve explicit supersession edges independent of input order, relink them through canonical IDs, and never inherit a verification result across changed source content without revalidation. Test merge order, source variants and crash/resume.

### R03 / P1: Play completeness is checked only after an incomplete inventory is frozen

**Location:** `backend/portfolio_independent.py:700`, `:708`; `backend/portfolio_research.py:287`.

Any nonempty decomposition is marked frozen. Repair is requested only when the entire component list is empty. `complete_component_plan()` then covers only those frozen components.

**Reproduction:** supply a five-part fertiliser/gold/silver/oil/uranium thesis and a decomposition containing only gold miners. It is frozen, no repair call occurs, and coverage contains one planned component.

**Impact:** "every component covered" can conceal omitted submitted ideas. The new test that starts with six already-correct components does not test this earlier failure boundary.

**Required repair:** require an explicit completeness assessment against the original submitted text before freezing. Preserve supported existing components while repairing identified omissions; allow an omission discovered by a later reviewer to invalidate the inventory's completeness receipt. Use source-grounded semantic decomposition, not a hardcoded commodity list or a mandatory search for every component.

### R04 / P1: Successful document inspection falls out of active evidence after supplementary failure

**Location:** `scripts/portfolio_positioning_memo.py:2919`, `:2940`, `:2958`.

An inspected report is saved in `document_inspections`, but its facts join the active lane only after the subsequent discovery/processing path returns successfully. The exception path returns the other lane without the inspected facts. Restoration does not consume `document_inspections`.

**Reproduction:** existing-document inspection answers the price dimension; costs remain unanswered; supplementary discovery raises an error. The saved inspection has the price fact, while returned active evidence has zero facts. The earlier answered dimension becomes unresolved.

**Impact:** useful already-obtained research is archived but unavailable to the memo, recreating the failure-containment problem this uplift was meant to remove.

**Required repair:** commit each successful inspection into the phase's canonical evidence and recovery lane immediately. Treat later discovery as an additive result. Preserve facts, citations and answered dimensions on provider failure, budget exhaustion and extraction failure.

### R05 / P2: Invalid funding explanations are collected but not surfaced as unresolved

**Location:** `backend/portfolio_decisions.py:174`.

Funding-flow errors are returned in `funding_flow_issues`, but do not affect `issues` or a separate funding-explanation status. No explicit consumer of this field was found elsewhere in the application.

**Reproduction:** a valid 50/50 gold/cash book moves to 60/40, but the addition declares funding from a nonexistent position. The result is `status = balanced`, `issues = []`, with the contradiction only in the separate flow list.

**Impact:** correct aggregate arithmetic can be mistaken for a validated funding explanation.

**Required repair:** retain arithmetic balance, but expose a separate unresolved funding-flow status and route it into the existing decision checks/reviewer context. Do not discard a balanced illustrative allocation or describe proposed trades as executed. Check source existence, actual reductions and, where amounts are supplied, aggregate funding capacity.

### R06 / P2: Some prose sent for factual review still cannot be corrected

**Location:** `backend/portfolio_judgment.py:598`; reviewed document contract in `backend/portfolio_independent.py:555`.

`decision_document()` includes current-sleeve actions and scenario assumptions. The shared patch paths exclude the `current_sleeve_actions` root and the scenario assumption `claim` field.

**Reproduction:** correct an explicitly wrong bond price/yield statement in each field. Neither patch applies; rejection reasons are `unknown_path` and `unsupported_field`.

**Impact:** an acknowledged factual error can survive in exactly the document the checker reviewed. Generating paths from a hand-maintained subset does not make that subset match the whole document contract.

**Required repair:** declare editable prose in the same canonical document schema used to build the checker input. Cover every reader-facing financial prose field, while retaining exact-original/hash checks and prohibiting numeric allocation, identity or score mutation. Add schema-walk coverage tests rather than another small list of happy-path examples.

### R07 / P2: Incomplete numerical scenarios suppress available qualitative analysis

**Location:** `backend/portfolio_judgment.py:231`.

`scenario_comparison()` returns a nonempty list even when every numerical outcome is incomplete. `if calculated:` then returns that list without using the reviewer-supplied qualitative scenario.

**Reproduction:** provide an inflation shock but no sensitivities, plus a qualitative cash purchasing-power assessment. The result is `incomplete`, with no qualitative direction or explanation.

**Impact:** supplying partial numerical assumptions can produce a less useful comparison than supplying none.

**Required repair:** choose the quantitative/qualitative presentation per scenario and exposure based on completeness, not list truthiness. Preserve genuine computed values and explicit missing inputs alongside qualitative reasoning; do not invent sensitivities or returns.

### R08 / P2: One observation can satisfy a two-observation monitoring condition

**Location:** `backend/portfolio_decisions.py:516`.

Persistence deduplicates on the original `observed_at` string instead of normalized observation time/period.

**Reproduction:** the same quote at `09:00:00Z` and `09:00:00+00:00` satisfies `consecutive_count = 2` and returns `triggered`.

**Impact:** repeated representations of one quote can be mistaken for sustained evidence. No recurring monitoring was activated by the uplift, but saved-condition evaluation is wrong in this case.

**Required repair:** canonicalize timestamp/period identity before sequence evaluation, preserve source versions, and treat conflicting values at any required point explicitly. Cover timezone equivalents, duplicated providers, date-only observations and genuine distinct periods.

### R09 / P2: Retry telemetry reuses the first attempt's token timestamps

**Location:** `backend/portfolio_runtime.py:572`, `:585`, `:715`.

The progress task is reused across attempts, and `first_token_at`/`first_content_at` are not reset. Later callbacks preserve the old values. Negative first-token duration is then clamped to zero.

**Reproduction:** two mocked responses each delay their first token by 0.1 seconds; the first returns invalid JSON. The successful second attempt reports a first-token delay of zero and a generation interval that starts during the previous attempt.

**Impact:** the new metrics can mislead provider comparisons and diagnosis of retry-heavy runs.

**Required repair:** store attempt-local timing and identifiers, retain previous attempt receipts, and calculate aggregate task timing separately. Separate provider generation time from local validation/checkpoint time where measured; do not change models or cut output to improve the reported metric.

## Original Reassessment of All 17 Uplift Items

This table records the state before R01-R09 were repaired. Current item statuses are in [the implementation ledger](./portfolio-uplift-implementation-20260921.md).

| Item | Honest status after this review |
| --- | --- |
| U01 Source context | Partial: PDF coordinate extraction and lookup work, but R04 loses successful lookups from active evidence. General HTML/structured-data inspection is not implemented. |
| U02 Typed observations | Partial: fields are extracted and projected; their verification contract is incomplete (R01). |
| U03 Correction propagation | Partial: corrected records are created, but merge/recovery can lose supersession state (R02). |
| U04 Opposing evidence | Selection/relationship union tests pass, including the frozen copper fixture. End-to-end reliability still depends on R02/R04. |
| U05 Case refresh | Dependency hashing and affected-case dispatch are connected and tested. They cannot compensate for evidence omitted or misclassified upstream. Model response quality remains unproven. |
| U06 Scoped corrections | Partial: expanded paths work, but two reviewed prose locations remain unpatchable (R06). |
| U07 Funding | Core arithmetic and new-position separation work. Declared funding-flow validity remains incomplete (R05). |
| U08 Play coverage | Partial: downstream inventory coverage works; completeness of the original decomposition does not (R03). |
| U09 Scope/horizon | Implemented in the current workflow's research and allocation inputs. No fixed numerical drawdown or midpoint is inferred from high/5+ settings. |
| U10 Investment mechanics | Analytical contracts are implemented. This is not proof that generated causal chains, valuations and retained-weight explanations satisfy financial acceptance. |
| U11 Scenarios | Partial: qualitative output exists, but R07 suppresses it with incomplete numerical input. The comparison also lacks a dedicated independent-ideal risk view. |
| U12 Scheduling | Affordable first searches and completed initial lanes overlap. Failure containment is incomplete (R04); live critical-path improvement is unmeasured. |
| U13 Private baselines | Frozen blind inputs, overlap and mocked resume tests pass. Full memory-aware admission/crash stress acceptance is not established by those tests. |
| U14 Provider performance | Optional routing policy works without changing the model or replaying completed work. Retry telemetry needs R09; live policy comparison remains pending. |
| U15 Monitoring | Binding and basic persistence work. Duplicate observation identity can trigger a false condition (R08). |
| U16 Editorial/reader | Short theme and expandable rationale preserve the reader. New-run editorial quality still needs comparison; factual correction coverage depends on R06. |
| U17 Evaluation | Partial: existing tests pass, but missed nine failure-boundary cases. The two real audit fixtures are local/untracked and skip in a clean checkout. No controlled paid acceptance run has occurred. |

## Additional Design Scope Still Open

1. Source inspection is currently limited to URLs ending in `.pdf`. `context_required` does not cause an existing HTML excerpt to be expanded, and content-type detection for PDF download endpoints is absent. This was disclosed as a limitation, but U01 should not be labelled fully complete against the broader design.
2. The scenario comparison evaluates destination and smaller-change ledgers against current holdings. It does not give the independent ideal its own comparable scenario view, although the uplift asked for all four alternatives.
3. The fixed model semaphore and branch-overlap tests do not establish memory-aware admission, a full dependency/wait trace, or crash-point coverage of simultaneous branch completion. Do not claim those acceptance criteria without the corresponding implementation/tests.
4. Source fixtures in `outputs/audits/portfolio-final-review-20260921/` are not tracked. Preserve small redistributable fixtures or a documented fixture acquisition mechanism so CI does not silently skip the two real-world regression checks.

## Why The Previous Pass Missed This

The tests tended to begin after the risky handoff: with a complete component inventory, a freshly corrected fact before merging, a fully answered inspection, no numerical scenario inputs, and a single successful model attempt. Those tests establish useful local behavior, but not the boundaries where the original failures occurred.

The remedy is not another broad redesign or more generic model reviewers. Add small regression cases at these existing boundaries, repair the specific data/status transitions, and then run the controlled comparison. Preserve useful output throughout; none of these findings justifies failing an entire memo for an optional field.

**Original recommended order:** R01-R04 first, then R05-R09; close the explicitly outstanding design scope; convert the probes into the regular regression suite; only then deploy or spend on a quality comparison. R01-R09 and the regular regression coverage are now addressed locally; the broader acceptance work is still explicit above.
