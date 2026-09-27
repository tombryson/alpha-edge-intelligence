# Portfolio Research Architecture: Independent Review

## Implementation Status

The subsequent L1-L6 repair pass is **deployed in Fly release 363**. The
[implementation record and updated flow](portfolio-architecture-walkthrough-20260923.md#implemented-surgical-pass)
contains measured before/after results and remaining acceptance limits. The audit
below describes the pre-repair code and is retained as evidence, not current status.

## Current Audit: A Smaller Evidence-To-Memo Pipeline

September 23, after the completed memo and the local brief-plays change. This is
an offline audit and a replacement plan, **not another completed remediation**.
No application changes, paid requests, model changes, deployment or historical
memo rewrites were made in this pass. Earlier implementation notes below are
historical. The ordered L1-L6 queue here supersedes them as the next work plan.

The full [architecture and stage-value walkthrough](/Users/Toms_Macbook/Projects/llm-council/docs/portfolio-architecture-walkthrough-20260923.md)
completes this audit with diagrams, step-by-step construction, correctness/value/
efficiency assessments, actual receipt costs and comparison with past memos.
At the time of this audit L1-L6 remained open; see the implementation status above.

### Judgment

Keep the improved research, independent portfolio, current-book assessment and
financial dissent. Reduce the work required to turn them into one decision and
one readable memo. The system currently confuses discovering a fact with needing
that fact in every related analysis; it also loses an explicit link to a newer
answer. More research, larger context windows and another reviewer do not fix
those two errors.

The 801 previously reported tests are not 801 production requests. Current
collection finds 819 parameterized unit cases across the application; the unit
fixture blocks external HTTP and isolates storage. Deleting tests would not
reduce the provider bill. Test count also does not establish investment quality:
the focused 46-test run passes while the recorded-data probes below reproduce
the handoff defect. Stop using aggregate pass counts as the headline measure of
architectural improvement.

### Reproduced Findings

**L1 / P1: New research is not reliably the current answer.**
`backend/portfolio_research.py:123`, `:496`, `:586`;
`backend/portfolio_tasks.py:108`; `backend/portfolio_requests.py:96`.

The saved uranium follow-up explicitly names the original question through
`reuse_question_id`, but `matching_question` rejects it because period wording
differs: "as of 2026-09-23 and forward" versus "2026 onward". The downstream
`research_readthrough` projection then drops that link. Selecting the original
question yields **zero facts**; explicitly selecting both brings in **24 uranium
observations**. Current local settlement still includes the old unanswered
questions and none of those observations. This is not only a deployed-old-code
issue: it reproduces with today's projection functions.

Do not fix this by treating every similarly worded period as equivalent, choosing
the last-arriving answer, or converting partial research to "answered". Preserve
the existing explicit link as a related-answer relationship. Resolve linked
answers when building the current question view; combine only compatible
dimensions/measurement scopes. Show what the newer evidence establishes and the
specific remaining gap. Keep contradictory observations, scope differences and
old revisions in the archive. Immutable baseline judgments stay historical;
final synthesis and commentary consume the current answer, not their stale
"nothing supplied" premise. No new model call is needed for relationship repair.

**L2 / P1: Relevance expands into almost the whole archive.**
`scripts/portfolio_positioning_memo.py:1561`;
`backend/portfolio_tasks.py:108`; `backend/portfolio_requests.py:96`.

Every observation extracted for a question receives its discovery question ID
and broad economic comparison group. Settlement follows those tags as if all
such observations are decision dependencies. These are different relationships.

| Selection on the saved final-settlement case | Facts |
| --- | ---: |
| Direct decision and review citations | 120 |
| With selected question answers | 416 |
| With discovery-question tags | 1,170 |
| With broad comparison groups | 1,686 |
| Actual final selection, including other closure rules | 1,696 of 1,776 |

The resulting evidence packet is **2,140,358 bytes and contains zero uranium
facts**. An offline alternative uses existing answer citations and typed
comparable/opposing observations, then adds the explicitly linked later uranium
answer: **446 facts, 721,034 bytes, 66.3% smaller**. It includes all 23 fact IDs
cited by that answer; the 24th uranium observation remains available in the
archive. This is a selection experiment, not proof that every excluded fact is
immaterial or that the final analysis improves. Stale answer reconciliation is
still required. It is not a fact-count or token ceiling.

Use the existing typed-comparator selection consistently at the final handoff.
Keep discovery tags for lookup/provenance, not automatic prompt inclusion.
Maintain a small discovery index for other observations; do not delete the
source archive or contrary evidence. Do not add another extraction call merely
to relabel existing facts.

**L3 / P1: The research allowance does not represent downstream workload.**
`backend/portfolio_retrieval.py:53`;
`backend/portfolio_research.py:526`;
`scripts/portfolio_positioning_memo.py:2944`, `:3135`.

The allowance covers discovery estimates, explicitly excluding extraction and
model processing. A cheap search can create extraction, answer synthesis,
review, source checks and case refreshes. In the saved run, **39 of 46 questions
are high priority, 36 are critical, and nine are deferred**. Those labels barely
prioritize anything. These are historical counts, not a forecast for the new
brief-plays path. Concurrent expansion also spends its shared allowance as
first searches finish, not strictly in investment-priority order.

Use the existing planner to return a genuinely ordered list of decision-changing
questions, not another rating agent. Prioritize the size/consequence of the
decision, what remains unknown after reuse, the chance retrieval resolves it,
and the structural horizon. Batch independent first searches; admit deep work
in that order within the existing allowance. Show the marginal downstream model
work as well as retrieval spend. Do not introduce the old exaggerated-credit
gate, a mandatory question quota per asset, or more research allowance.

Core questions include physical flows versus announced capacity, the path from
commodity scarcity to producer cash flow and valuation, and duration versus
bullion hedge mechanics. Their priority follows actual portfolio decisions, not
whether a user play mentions them. Missing tax lots, holdings or preferences
remain investor inputs, not web searches. A five-year decision needs structural
scenarios, not an obligatory five-year forecast for every field.

**L4 / P1: Repeated investment cases and incomplete cross-portfolio comparison.**
`scripts/portfolio_positioning_memo.py:3485-3785`;
`backend/portfolio_independent.py:298`.

Both reviewers enumerate targets, existing actions, excluded opportunities,
research assessments and otherwise unassigned questions. Grouping helps, but a
research question can remain a review obligation even when no decision depends
on it. Provisional reasoning, detailed cases, final reasoning, changed cases,
commentary, consistency and reconsideration then carry overlapping arguments.
The current loops are bounded; the problem is cumulative work, not an infinite
loop. Increasing concurrency alone cannot remove that work.

The completed receipt audit attributes $21.98 to 40 reviews and 35 additional
archived-source lookups, versus $0.27 for 58 source checks. The primary cost
reduction is repeated financial analysis, not deleting all source verification.
Removing 16 play units in a current-code replay of the final archive reduces
total review units only from 89 to 88: 15 questions reappear as standalone duties.
These are not fresh-run forecasts. Unowned historical questions must stop being
automatic work when the brief-play boundary is applied.

The related scenario comparison is also incomplete: exact exposure-name
matching leaves 90% of the independent ideal unknown in every saved scenario,
reproduced in current code. Use explicit exposure relationships to compare
compatible views; retain partial/different instrument distinctions. Do not infer
bond/miner/bullion equivalence from similar names or fabricate return sensitivities.
This defect is why L4 is P1, not merely a cost/presentation cleanup.

Keep one current case per final exposure, with the two independent baselines
preserved separately. Challenge material disagreements, factual premises and
portfolio risks, not every archived object. Use the existing allocator/final
responses for the investment case rather than automatically expanding every
position into another essay. Generate reader prose once after decisions settle.
Reserve any repair for an actual material contradiction; missing optional prose
does not commission a new analysis. Merge/remove superseded stages rather than
adding this alongside them. Retiring legacy generation paths is a later cleanup,
after confirming no old checkpoint needs them; preserve historical readers.

**L5 / P2: Prompt construction and persistence still copy too much.**
`backend/portfolio_requests.py:9`; `backend/portfolio_independent.py:551`;
`backend/portfolio_runtime.py:344`, `:467`.

Final reconciliation first constructs a full observation view, then replaces it
with the scoped settlement view. Repeated projection/copying is unnecessary.
The saved fixture produces a 2.47 MB reconstructed final prompt (without
recalculating its decision-check payload); the traced
Python allocation peak during construction is about 20.1 MB above the already
loaded artifact. This is **not full worker RSS or evidence of a current OOM**.
The archive's evidence object is 7.23 MB and structured output another 1.82 MB;
canonical data is also embedded in several saved views. Source-review metadata
in the projected facts occupies about 624 KB, versus 257 KB of source excerpts.

Select IDs before constructing full rows; construct the chosen request view
once. Reuse the existing record store and incremental events, retaining full
snapshots only at meaningful boundaries. Share repeated source/verdict records
by identity instead of copying their prose into each fact. Keep meaningful dates,
units, scopes, qualifications and adverse evidence. Do not replace the system
with a new database, vector store, orchestrator or cache hierarchy. Measure full
worker peak RSS before claiming memory remediation complete.

**L6 / P2: Useful portfolio shapes are present but not presented.**
`frontend/src/components/PortfolioPositioningLab.jsx:134`, `:444`, `:472`;
`backend/routers/runs.py:99`; `backend/portfolio_memo.py:218`.

The visual stacked allocation component still exists, but `!independent`
suppresses it for workflow 3/4. The small memo endpoint omits structured ideal,
current-aware and smaller-change views, leaving Markdown to carry them. The
latest artifact has a five-exposure independent ideal, ten-exposure current-aware
proposal, sixteen-exposure recommendation and fourteen-row smaller-change option.
The latter has **17.3914% one-way turnover**, versus **33.4108%** for the destination.
The minor-adjustment alternative is not missing analytical work.

Restore a compact, deterministic portfolio-shape comparison from these saved
objects: **Current / Independent ideal / Recommended / Smaller change**. Make
the recommended and smaller-change options directly comparable; retain the
current-aware proposal as supporting analysis. Use one reusable graphic and one
allocation table with stable exposure colours, exact values and accessible labels.
No image-generation or model call is needed; an exported image, if useful, must
come from those same numbers. Do not normalize invalid weights into 100%, or
colour unlike instruments as equivalents without an explicit relationship.

Keep the newer narrative sequence and both themes. Repair composition, not the
whole page: render the executive summary as Markdown blocks, preserve paragraphs
and lists rather than splitting/rejoining their sentences, write each investment
argument once, and keep internal finding IDs/repeated diagnostics out of the
reading path. Show a short comparison explaining what the smaller change achieves
and gives up. Sources and detailed support stay at the end. No new copywriting
agent and no truncation of substantive output.

### Target Flow And Boundaries

```text
Existing research -> current question answers + sources
                           |
          +----------------+----------------+
          |                                 |
 Independent ideal                 Current-book assessment
 (no holdings or plays)             (no ideal or plays)
          +----------------+----------------+
                           |
          Material challenge / decision questions
          Reuse first; focused research within existing budget
                           |
          Final funded recommendation + smaller-change option
          Plays introduced HERE, once, using available evidence
                           |
          Arithmetic and material claim checks
                           |
          One narrative + deterministic portfolio-shape graphics
```

This replaces repeated stages; it is not an extra layer. There can still be
concurrent retrieval/extraction and distinct reviewer perspectives. The diagram
does not promise a fixed number of API calls. Retrieval may be deep where the
decision warrants it; deep research is not a default obligation for every gap.

The accepted play boundary is unchanged: one short score/verdict/reason/action
per idea at final synthesis; no play research, decomposition, component review
or play-only follow-up. Missing play research cannot block the memo. An adopted
allocation receives normal checks. Plays appear near the end. The previous
audit's proposal to prioritize dedicated play research is withdrawn.

### Small Implementation Queue

| Order | Replace/remove | Completion evidence |
| --- | --- | --- |
| L1 | Lost answer links and stale missing-evidence state | Recorded uranium answer reaches settlement and writer with its actual qualifications; old baselines unchanged; conflicting/scope-distinct evidence preserved |
| L2 | Discovery/topic expansion as a dependency rule | Actual prompts include all decisive/contrary references with materially lower bytes; no output cap and no archive deletion |
| L3 | Indiscriminate high/critical labels and race-ordered expansions | Most consequential unanswered core questions use the existing budget first; no play-created research; receipts separate discovery and downstream work |
| L4 | Repeated per-object reviews, unowned-question duties, case rewrites and exact-label-only scenario mapping | Fewer model requests; declared compatible exposures compared; independent views and material objections preserved |
| L5 | Full-view construction followed by replacement; redundant copies | Lower projection/snapshot CPU and worker peak RSS, with successful resume/cancellation and unchanged artifact provenance |
| L6 | Hidden shape objects, flattened prose and duplicated arguments | Exact four-view graphic, useful smaller-change option, readable desktop/mobile light/dark memo; no new paid call |

Start with L1 and L2 together: shrinking an incorrect packet alone is not success.
L6 can be implemented independently using saved outputs. Do not buy another full
run merely to discover whether these deterministic changes work.

Use a small set of recorded end-to-end cases to judge progress: the missing-answer
case, conflicting/scope-distinct sources, a normal completed memo, and interruption
with checkpoint reuse. Retain focused safety regressions; consolidate duplicated
fixtures/assertions rather than deleting coverage to hit a lower number. Report
paid calls and input/output tokens by stage, actual billed cost, elapsed time,
peak RSS, whether current evidence reaches the decision, and reader quality.
Do not report a test count or lower byte count as proof of better investment
analysis. Live quality, total cost and latency require a subsequent authorized
comparison, not a promise from the offline benchmark.

### Audit Evidence

`outputs/audits/portfolio-lean-audit-20260923/audit.py` and `metrics.json` replay
current projections against the saved September 23 artifact. No providers run.
The artifact SHA-256 remains
`ded21d5cb92868f6884139d5bbdf906d85bca695267d244c0ad793a758301c81`.
The 0-versus-24 question selection and all 23 answer-citation inclusions are
asserted. The narrowed packet is explicitly experimental, not production code.
Forty-six existing focused tests passed; 819 unit cases were only collected, not
all executed. Original live receipt costs and reading measurements remain in
[the completed-memo comparison](portfolio-finish-comparison-20260923.md).

## Implementation: Lean Pass, September 23

This update supersedes the open-defect labels in the original review below.
Changes are local and undeployed. No paid requests, historical-output edits,
model substitutions, new agents, review stages, output caps or layout changes.

| Item | Current disposition |
| --- | --- |
| RA01 | Fixed exact-query reuse and separate attempt records. Pending expansion resumes the frozen retrieval context, even after original dimensions were marked searched. No recursive expansion of a resumed attempt. |
| RA02 | New source versions can be inspected for unresolved dimensions; unchanged successful inspections are not repeated. Inspection cannot bypass discovery admission. |
| RA03 | Answers are deduplicated, not selected by last arrival. Distinct supported alternatives survive; same-scope numeric disagreement is explicit. Different periods and superseded observations do not create false conflicts. Semantic adjudication remains with the existing analysts. |
| RA04 | Declared aliases survive the actual review projection and share evidence relationship resolution. Contrary facts and question gaps follow those aliases. No new instrument-ID migration or change to capital-transfer rules. |
| RA05 | Known URLs now use Parallel Extract, retaining concurrent 20-URL batches and successful partial results. Accepted/uncertain legacy Task submissions remain on their saved path. Deep discovery processor assignments are unchanged. Live cost/recall/latency comparison remains unproven. |
| RA06 | Removed the inconsistent new-run hard gate on the historical high forecast. Forecast is advisory; zero paid balance, fixed charges, unknown pricing and actual provider rejection still stop paid admission. Shared executable plan and calibrated cross-provider estimates remain open, not replaced with another planning layer. |
| RA07 | Compact research answers now retain support qualifications. Existing document inspection can reach new reports. No mandatory pre-allocator source-check stage was added; pivotal-source timing and locator quality still need evaluation. |
| RA08 | Versioned inspection reuse is implemented. Full origin-release lineage and point-in-time structured feeds are not implemented in this pass. |
| RA09 | Existing calculations, cases, caveats and financial reasoning preserved. No mandatory valuation forms or new calculation agent. Instrument-specific cash-flow/bond calculations require properly scoped source inputs and separate acceptance. |
| RA10 | Existing planner now explicitly asks whether plausible answers change a decision. Instructions shortened, with the same response schema. The actual improvement in question selection requires a live comparison; no new ranking call or automatic quota. |
| RA11 | Question-result persistence uses small durable events and one full phase save. Removed redundant evidence projection and repeated construction of an already fitted review packet. Whole-archive discovery indexes and overall review workload remain substantial. |

### Verification and Workload

Ten new research regressions cover the four counterexamples, real review-packet
alias projection, exact-context recovery, inspection budgets, changed documents,
period distinctions and correction handling. Provider tests cover Extract-only
dispatch, partial source failure, cache reopen, ambiguous POSTs and completion of
already-paid legacy Task extraction after a processor change. All are offline.

- Final full unit suite: **748 passed**, with five existing PyMuPDF/SWIG
  deprecation warnings. Earlier portfolio-only run: **650 passed**; focused
  post-edit run: **128 passed**, followed by **10 research regressions passed**.
- Correctness lint (`E9,F`) and `git diff --check` pass.
- Independent planning rules: **17 -> 12**, **3,290 -> 2,271 bytes (-31%)**.
  No removal of observations, source passages or investor constraints.
- Review packet benchmark before/after the projection optimisation: **13 sections
  per reviewer and 4,488,291 total bytes in both**. It reduces local repeated
  construction, not the analyst's evidence or paid request payload.
- Final complete downstream replay: **95 -> 102 simulated model requests**,
  **37 -> 31 full-checkpoint writes**, **27,286,625 -> 27,485,673 request bytes**
  (+0.73%). All seven extra requests extract observations for document inspections
  previously skipped by RA02; the other task counts are unchanged. This trade-off
  is explicit, not described as a request-count reduction.
- That replay completed with limitations, 100% total weights, four concurrent
  model slots and all 102 successful requests revalidated from cache. It injected
  a source-check failure and five supplementary-retrieval failures without losing
  the memo. Wall time was 131.1s versus the previous 141.6s, but these are local
  mocked runs, not evidence of faster live inference or better financial judgment.

Evidence is under `outputs/audits/portfolio-r360-review-20260922/`:
`research-efficiency-probes-after-20260923.json`,
`research-efficiency-packets-before-20260923.json`,
`research-efficiency-packets-after-20260923.json`, and
`research-efficiency-workflow-final-20260923.json`.
The stopped artifact's SHA-256 remains unchanged.

### What This Pass Does Not Claim

The concrete research defects are repaired locally. The whole institutional
architecture is **not** certified complete. No live financial-quality gain,
provider saving or live completion time is claimed. Keep the independent ideal,
current-book assessment and later critique of plays. Evaluate future additions
by their effect on decisions and critical-path cost, not checklist completeness.
No new research/review layer is justified by this pass.

## Original Review (Before This Implementation)

Date: September 23, 2026. Scope: the current local working tree, including the
undeployed follow-through, not merely commit `b478f64`. This is a review, not a
deployment or another financial run. No production code, model assignment,
checkpoint or historical output was changed by this pass.

## Conclusion

The operational remediation was useful, but it did not establish research
correctness. Four additional implementation defects are reproducible below.
The larger weakness is that the system is better at accumulating observations,
producing arguments and checking their citations than at ensuring that the
decisive investment uncertainties were actually investigated.

The next improvement should not be more analysts, more mandatory fields, more
reconciliation rounds or tighter output caps. It should be **decision-linked
research with reliable identities, preserved disagreement, appropriate retrieval
tools and explicit economic calculations**. Keep the existing independent ideal,
current-aware assessment and later play critique. Evolve the internals in place.

The institution-quality question is: "Can we trace this position decision to
the information available at the time, reproduce its economics, identify what
could invalidate it, and deliver it before the information becomes stale?"
Counting sources or completed stages does not answer that question.

## Evidence and Boundaries

Read paths include initial Parallel/Perplexity research, citation hydration,
publisher context, extraction, question/measurement reuse, phase restoration,
review scoping, source checking, case development, settlement, financial
calculations, progress, persistence and funding admission.

New executable counterexamples:
`scripts/audit_portfolio_research_architecture.py`.
Saved result:
`outputs/audits/portfolio-r360-review-20260922/research-architecture-review-20260923.json`.

```sh
.venv/bin/python scripts/audit_portfolio_research_architecture.py \
  --artifact outputs/audits/portfolio-r360-review-20260922/stopped-recovery.json \
  --output outputs/audits/portfolio-r360-review-20260922/research-architecture-review-20260923.json
```

All probe providers are synthetic, HTTP access is prohibited, and scratch
checkpoints use a temporary directory. These are diagnostic counterexamples,
not tests claiming that defects are fixed. The relevant existing three test
modules still pass: **51 passed**. That is evidence of a coverage gap, not
evidence against the counterexamples.

The stopped historical artifact remains 24,440,094 bytes with SHA-256
`eebf7815a78f3c9d80dc31ea6313e2479397219e7a12dc0053353d4b290c2b09`:

| Retained research | Count |
| --- | ---: |
| Observations / source records | 947 / 102 |
| Questions answered / partial / unanswered | 6 / 13 / 5 |
| Not answered, but with searched dimensions recorded | 9 |
| Sources recorded as excerpt-only / selected PDF pages | 94 / 8 |
| Observations with typed observation kind / available_at field | 947 / 783 |
| Source records with an origin_release_id | 0 |

Those are stored metadata counts, not independent verification of dates or source
adequacy. An excerpt can be sufficient. The historical artifact predates local
changes; it does not prove that each newly reproduced defect caused that run's
outcome. It does show why raw observation volume is a poor success measure.

## Current Flow

```text
Mandate, horizon, risk tolerance and research cutoff
    |
    +-- Broad orientation lanes, concurrently
    |      Parallel Task research + Perplexity research in each lane
    |      -> hydrate citation URLs -> extract observations -> reconcile context
    |
    +-- Independent question plan -> focused research -> sealed evidence
                |
                +-- Independent ideal portfolio ------------------+
                |                                                 |
                +-- Holding/company context -> current research    |
                      -> current-aware assessment ----------------+
                                                                  |
                         Submitted plays -> components -> research
                                                                  |
                         Two reviewer roles, grouped case sections
                         -> optional saved-evidence lookup per section
                                                                  |
                         Provisional funded recommendation
                         -> challenge questions -> focused research
                                                                  |
                         Decision source checks (2 workers)
                         -> ready investment cases (2 workers)
                            sharing 4 model slots
                                                                  |
                         Final settlement -> changed source/case checks
                         -> commentary -> consistency assessment
                         -> optional scoped reconsideration -> memo
```

The code is **not entirely serial now**, nor is there an unlimited recursive
research loop in the reviewed v4 path. Review lookups and reconsideration are
bounded. The remaining problem is cumulative work and sequential dependencies:
several research waves, many case sections, citation checks, final changes and
prose checks can all lie on the critical path. Four parallel slots cannot make
an unnecessarily large workload small.

## Confirmed Implementation Defects

### RA01: An expansion does not necessarily search again [P1]

`scripts/portfolio_positioning_memo.py:2963`, `:2998`, `:3037`;
`backend/portfolio_research.py:222`.

The expansion uses the same question ID and a subset of the original dimensions.
`saved_source_lane` accepts that as the original purchased packet, without
matching the new retrieval attempt or expanded question. `search(...,
expansion=True)` still invokes this reuse path.

**Observed:** two differently named research/structuring lanes, one provider
query, identical source packets and the question still unanswered. This can
spend analysis work on old evidence while appearing to have expanded research.

**Remedy:** separate an economic question's identity from a retrieval attempt's
identity. Resume an exact attempt; expand only through a new, explicitly
admitted attempt with its own query, requested dimensions and parent attempt.
Preserve all previous results. Do not disable valid paid-task reuse.

**Acceptance:** first search is insufficient; a genuinely different second
request receives different sources. Resume either attempt without another POST.
An uncertain accepted attempt is never blindly repeated.

### RA02: Search history can block new primary-source inspection [P1]

`backend/portfolio_research.py:500`;
`scripts/portfolio_positioning_memo.py:2909`, `:2924`, `:3013`.

A successful retrieval/structuring attempt marks every requested dimension as
searched, even if no answer was established. `remaining_search` removes those
dimensions before the code considers `inspect_source_ids`.

**Observed:** supply a newly available primary document for the same unanswered
question in the next phase. Zero document inspections occur, and the question
is labelled `not_repeated` with "no new unanswered dimension" despite remaining
unanswered. Measurement-level reuse can also carry this searched flag forward.

**Remedy:** separate attempted, answered and exhausted. A new document/version,
changed material evidence or explicitly justified different method can justify
work on the same dimension. An unchanged request cannot. Evaluate saved-document
inspection separately from admission of a paid search.

**Acceptance:** new-document inspection runs; unchanged retries do not; a failed
inspection does not automatically authorize another discovery task. Budget
exhaustion remains visible and does not become an invented investment conclusion.

### RA03: Answer order can silently choose between opposing findings [P1]

`backend/portfolio_research.py:325`, especially `:359`.

Coverage selects one answer per dimension by status rank, then the last entry.
It preserves an answer already labelled `conflicting`; it does not preserve two
separately supplied `answered` alternatives as disagreement.

**Observed:** two synthetic, source-supported forecasts for the same scope imply
opposite export changes. Reversing their input order reverses the selected fact.
Both results say `answered` and have no missing dimension. Raw observations can
remain archived, but the research answer consumed downstream becomes one-sided.

**Remedy:** keep a set of source-backed propositions per dimension. Deduplicate
exact equivalents. Resolve compatible scopes/vintages explicitly; retain
unresolved alternatives. Detect obvious typed numerical conflicts mechanically;
use existing analysis for semantic conflicts. Do not turn every differing
forecast into equally weighted evidence or add a new mandatory adjudicator.

**Acceptance:** permutations preserve the same propositions and disagreement;
an explicit corrected vintage can supersede the old value with provenance.

### RA04: Equivalence is recognised for grouping but not for evidence scope [P1]

`backend/portfolio_exposures.py:99`;
`backend/portfolio_tasks.py:106`, `:132`.

`economic_case_aliases` recognises declared aliases. Evidence relationship
selection does not read the same aliases. Different modules can therefore
disagree about which economic case an observation belongs to.

**Observed:** a target `GOLD_ETF` explicitly aliases `BULLION`. Review grouping
recognises the equivalence, but a BULLION-linked contrary observation is absent
from the target's decision evidence. Adding an explicit question link restores
it. Explicit question links or other references can already avoid this defect;
it is not a claim that all alias-labelled evidence is lost.

**Remedy:** one canonical relationship resolver for planning, question matching,
case grouping, evidence selection, source checking and financial comparison.
Use opaque exposure/instrument IDs with human labels. Keep equivalence,
substitution and partial overlap distinct. Never infer that bullion and miners
are the same instrument just because both concern gold.

**Acceptance:** renaming and explicit aliases leave evidence and calculations
unchanged; real instrument differences remain separate.

## Architectural Weaknesses

### RA05: Known-URL extraction is routed through deep research [P2]

`backend/portfolio_sources.py:30` sends citation URLs to
`ParallelSourceProvider.gather`, which uses the Task endpoint at
`backend/portfolio_retrieval.py:14`, `:226`. Discovery and extraction share the
configured source processor. This is a real implementation choice, not a claim
that Task cannot extract sources or that the earlier user selection was ignored.

Parallel separately documents [Search](https://docs.parallel.ai/search/search-quickstart)
for retrieval and [Extract](https://docs.parallel.ai/extract/extract-quickstart)
for focused or full content from known URLs, including PDFs. My recommendation:
benchmark Extract for citation hydration and Search for simple discovery;
retain ultra2x Task for material multi-source investigations. Do not silently
substitute services or claim a latency/cost saving before measuring comparable
source recall, table fidelity and billable usage.

Extraction is explicitly outside `ResearchBudget`; OpenRouter preflight does not
check Parallel or Perplexity. There is no single all-provider cost view. Include
discovery, extraction and model processing separately in the admitted plan and
actual accounting. An unavailable provider balance should say unknown, not zero.

### RA06: Execution, progress and affordability describe different plans [P2]

`backend/portfolio_work.py:6` describes stage dependencies. Actual scheduling
lives in `_run_independent_pipeline`. `backend/portfolio_funding.py:136` separately
hard-codes extraction/review counts and September 16 token profiles. New-run
preflight still requires its high estimate (`:208`); recovery/per-call forecasts
are more permissive. Changing the execution graph need not change the estimate.

Use one small executable work-plan representation as the source of dependency,
required/optional status, cache identity, estimated cost and progress. Initially
wrap existing functions, not a new distributed orchestration platform. Admit
known work first; expose contingent scope and uncertainties separately. Keep
operator-approved spend controls distinct from a fallible forecast. A forecast
must not masquerade as an exact minimum purchase requirement.

### RA07: Source verification comes late and is not economic sufficiency [P2]

In v4, initial reconciliation selects no new fact checks unless decision IDs
are supplied (`scripts/portfolio_positioning_memo.py:1673`). Allocators and
reviewers therefore form views before the later selected source-check pass.
Corrections and final case refresh are implemented and valuable. However, an
early mistaken premise can propagate into many arguments before repair.

Check cheap deterministic properties on intake. Inspect and verify pivotal
observations before the first substantive judgment that depends on them; do not
reintroduce checking every archived fact as a global barrier. Separate "the
source says this", "this is comparable", "this is reliable" and "this supports
the investment conclusion". `research_readthrough` also drops answer-level
`support_status`/qualified IDs, although fact-level warnings remain: propagate the
distinction in compact answer records, not just in a distant fact appendix.

Publisher selection still uses lexical matching: two PDF pages or two HTML
matches plus neighbours (`backend/portfolio_documents.py:13`, `:118`). The
improved table handling preserves selected layout, but cannot establish that
the decisive footnote or original release was selected. Benchmark locators,
full heading paths and semantic relevance before relying on those selections.

### RA08: Time and source lineage need stronger semantics [P2]

Typed dates, available-at values, source hashes and correction links already
exist. Preserve them. They are not a complete point-in-time data layer: published
dates may be provider-reported, excerpts may come from mutable pages, and no
upstream release identity is enforced across syndicated URLs. Five URLs can
still represent one originating claim; the current prompt warns against this
but source normalization deduplicates URLs, not that common origin.

Record original release, document version/content hash, observation period,
actual availability and retrieval time separately. Keep contradictory releases
and unknown timestamps visible. For a historical decision snapshot, exclude
known-later evidence from decision inputs while retaining it in the archive;
do not discard the memo. Unknown timing is a qualification, not proof of fraud.

For supported macro series, use version-aware structured data rather than
reconstructing numbers from prose. [ALFRED's real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
distinguish historical observations from what was known at a chosen time.
This is an example of the required semantics, not a recommendation to replace
every commodity data source with FRED.

### RA09: The financial engine still relies heavily on prose [P2]

`backend/portfolio_judgment.py:399` computes a useful but narrow set of
differences, spreads, midpoints and weight changes. `:308` compares the four
portfolio shapes using qualitative benefit/harm weights; it deliberately returns
unknown portfolio returns. This is honest, but not a substitute for valuation,
cash-flow sensitivity or sizing analysis.

The missing capability is a compact **decision case**, not another essay:
economic claim; investable expression; observed inputs; explicitly labelled
assumptions; contrary evidence; cash-flow/valuation transmission; a break-even
condition; alternative use of capital; and what would change the action.
Populate it from existing case/review stages. Apply only relevant calculations;
do not require the same form for cash, sovereign bonds and mine developers.

Examples of research questions and calculations, not current market conclusions:

| Case | Research that can change the decision | Useful calculation |
| --- | --- | --- |
| Oil producers | Actual flows and inventory draws; restoration timing; forward curve; realised prices, hedges, fiscal terms, sustaining capex and valuation | Cash-flow sensitivity and the commodity price needed to justify the valuation |
| Fertiliser | Feedstock availability/cost; product spreads; outages versus operating capacity; trade restrictions and working capital | Margin sensitivity under coherent input/output price scenarios |
| Gold/silver miners | Realised prices, operating costs, capex, royalties, dilution, jurisdiction and balance sheet | Producer cash flow and valuation versus bullion exposure, not metal price alone |
| Uranium producers | Contracted versus uncontracted sales, delivery obligations, realised pricing, production capacity and balance sheet | Contract-aware cash flow and execution downside, not spot price alone |
| Gold versus bonds | Investor currency; nominal/real yields; duration, inflation and term-premium shocks; currency hedging and liquidity needs | Carry and duration/convexity sensitivity for defined bonds; gold scenarios with explicit assumptions |

Retain unknowns when inputs are absent. A scenario is not a forecast probability.
A 7/10 play score needs an explained rubric; it is not a calibrated expected
return. High risk tolerance does not imply unlimited concentration, and a long
horizon does not cure liquidity or refinancing risk.

### RA10: Research priority is still largely phase- and label-driven [P2]

Planning can now tag earnings, valuation and other consequences. Scheduling
still sorts critical/high labels and applies fixed phase fractions, with no
evidence that this prioritises questions that could materially alter the book.
The blind stage must remain holdings-blind. After its snapshot is sealed,
prioritise questions by plausible change to thesis, sizing, funding or risk,
uncertainty and expected investigation effort. Prefer an ordinal materiality
assessment to invented precise expected-value-of-information numbers.

Ask: "Would either plausible answer alter this decision?" If not, archive the
interesting question instead of automatically researching it. A material new
premise can justify reopening a question; a missing formatting field cannot.

### RA11: Work amplification remains possible without recursion [P2]

Each review section still receives a catalogue of every other observation
(`backend/portfolio_tasks.py:189`), without their values, units or target periods.
This can be expensive while making relevant dissent difficult to recognise.
Keep searchable typed observation access and show relevant opposing propositions;
do not simply cut the archive to an arbitrary number of facts.

The targeted-question path still calls full `asave()` before and after
structuring each result (`scripts/portfolio_positioning_memo.py:3006`, `:3020`).
Provider result events are incremental, but these surrounding full boundaries
remain. Extend the existing durable record mechanism to these records and
materialise at meaningful phase boundaries. Reuse existing cancellation/drain
tests; benchmark real full-write count and bytes, not just request payloads.

Neither issue alone establishes the duration of a future run. Measure queue,
provider, extraction, verification, serialization and finalization times
separately before attributing a delay to the model.

## Recommended Target

```text
Mandate + immutable information cutoff
    -> public opportunity discovery and decisive premise questions
    -> question/attempt registry and one admitted work plan
         +-> saved evidence or authoritative structured data
         +-> known URL: targeted document extraction
         +-> simple discovery: focused search
         +-> unresolved material investigation: Parallel Task
    -> versioned observations and source-origin links
    -> proposition sets: support, contradiction, scope and uncertainty
    -> independent ideal snapshot
         || current-portfolio assessment (independent of that allocation)
    -> user plays introduced and researched explicitly
    -> economic cases + deterministic sensitivities + independent challenge
    -> funded comparison: ideal/current/smaller-change/final
    -> human-readable memo, with audit material at the end
```

This is a modular monolith evolution. Existing async workers, provider adapters,
record store and renderer are enough to start. No separate Codex agent, message
bus, graph database or workflow service is required to repair these problems.
Use ordinary records and indexed relationships first. Shared research across
runs can follow later, keyed by release/version, scope and cutoff, with private
holdings/play boundaries preserved. Do not let cross-run cache reuse redefine
what was available at the decision time.

The institutional principle is traceability, not bureaucracy: BCBS discusses
data origin-to-use lineage, consistent definitions and accurate, complete,
timely aggregation. Those are useful design analogies here, not a claim that
this app is a regulated bank or compliant with BCBS 239. [BIS implementation discussion](https://www.bis.org/publications/implementation-principles-effective-risk-data-aggregation-and-risk-reporting-bcbs-239-principles).

## Ordered Work and Acceptance

| Order | Scope | Evidence required before closing |
| --- | --- | --- |
| 1 | RA01-RA04 correctness | Turn these counterexamples into ordinary regression tests; expansion/resume, new-document inspection, order invariance and cross-alias evidence all pass |
| 2 | RA06 single work plan; RA11 write boundaries | Dispatch/progress/cost consume the same task identities; cancellation preserves results; fresh and resumed runs show known versus contingent work |
| 3 | RA05 retrieval tool split; RA07 pivotal-source inspection | Frozen-URL/table corpus comparison; no regression in relevant/contrary source recall; actual extraction cost/latency measured |
| 4 | RA08 point-in-time and origin lineage | Revisions, syndication, ambiguous dates and known-later sources survive archival but cannot silently alter the admissible historical view |
| 5 | RA09-RA10 economic cases and prioritisation | Several worked producer/bond/hedge cases reproduce economics; assumptions and unknowns explicit; new facts can change sizing or research priority |
| 6 | Full financial acceptance | Intake-to-reader replay and separately authorised matched-input paid comparison; measure financial correctness, readability, spend and time to usable memo |

Acceptance must include the initial intake. The previous 95-request simulator
starts from retained research; it cannot demonstrate that retrieval expansions,
source selection and initial financial extraction work correctly end to end.
Keep that test, but add these dimensions rather than inflating test counts:

- Permute provider completion order, source order and answer order: same evidence
  set and conflict visibility, regardless of scheduling.
- Change labels, split equivalent rows or add aliases: economics and evidence
  unchanged; genuine distinct instruments remain distinct.
- Add ten syndicated articles from one release: no tenfold corroboration.
- Supply one decisive contrary primary release: premise and sizing must be
  reconsidered, without forcing a predetermined buy/sell direction.
- Change plays/holdings only: the sealed blind proposal and its input hash stay
  unchanged; subsequent evaluation explicitly considers the changes.
- Reuse a historical date with a revised series: select the right vintage.
- Fail one supplementary provider: preserve usable analysis and qualify only
  affected decisions. Unknown acceptance never triggers a duplicate paid POST.
- Compare retrieval methods and analyst models on the same saved evidence,
  mandate and plays; separate stochastic model changes from architecture changes.

Measure expert-adjudicated claim correctness, citation entailment, decisive
question coverage, contrary-evidence recall, financial arithmetic, opportunity
cost/sizing clarity and recommendation stability. Also measure total cost,
critical-path latency, time to first useful memo, cache correctness and reader
length. None is a substitute for the others.

## What To Keep

Keep blind/current separation, delayed plays, open-ended opportunity discovery,
source excerpts instead of generated prose as evidence, explicit model
provenance, versioned checks, preserved partial outputs, funded arithmetic,
received-result durability and uncertain-submission protection. Keep the
existing memo presentation. Do not turn evidence qualifications back into a
whole-run failure or impose another arbitrary output ceiling.

**Disposition:** review complete; RA01-RA04 are reproduced but not fixed in this
pass. RA05-RA11 are grounded design/performance gaps and proposals, not asserted
production incidents. No new final memo, live latency result or financial-quality
improvement is claimed. The next step is the first correctness batch, not a paid
full rerun to see whether it happens to work.
