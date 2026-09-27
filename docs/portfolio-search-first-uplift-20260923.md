# Portfolio research-direction uplift

Status: implemented locally, not deployed. The active Fly memo is unchanged.
No new paid research or memo run was submitted during implementation.
The approved profile has been applied to the local audited Model Routing store;
a subsequent dry run reports no outstanding profile changes. Fly overrides and
running processes were not changed.

## Responsibilities

| Existing assignment | Responsibility | Approved model |
| --- | --- | --- |
| Decision & Memo | Design material research questions, then compare allocations and write the memo | anthropic/claude-opus-5.5 |
| Evidence Processing | Extract observations, preserve source context, assess answer coverage | openai/gpt-6-luna-pro |
| Allocation & Review | Independent ideal, current portfolio and specialist reviews | openai/gpt-6-sol |
| Research | Deep-research escalation processor | Parallel ultra2x |

No new model group, planner pass or mandatory review stage. Existing research-plan
calls use the decision model instead of the evidence model. Initial orientation
remains the existing three broad, holdings-blind subjects with explicit queries.

## Retrieval flow

```text
Existing orientation searches (concurrent)
  -> evidence processing
  -> existing research planner, now decision model
  -> reuse recorded observations / inspect known reports
  -> Parallel Search advanced: objective + complementary queries, five results
  -> evidence model extracts observations and checks missing dimensions
  -> selective Extract if an identified page could resolve a missing dimension
  -> one justified follow-up: focused Search, or Task for a difficult critical gap
  -> existing allocation, review and memo stages
```

Independent research does not receive holdings or investment plays. The current
portfolio assessment does not receive the ideal's weights. Plays enter after
both baseline assessments. The new adapter does not alter those boundaries.

The research planner can explain why a difficult multi-source investigation may
be necessary. That does not immediately launch a Task. Escalation requires a
successful Search, successful evidence processing, a still-unanswered high-impact
or critical premise, and remaining phase/run funds. Retrieval or extraction
failure is not a reason to purchase another service. A failed supplementary call
retains earlier evidence and marks the unresolved question.

Search and Extract share the question-specific objective, keyword queries,
consuming model hint and session. Extract uses only identified URLs; unrelated
pages cannot enter through a model-supplied inspection list. Deep research may
retain more than five necessary sources; historical Task normalization remains
unchanged. Search results are deduplicated while retaining their source excerpts.
Search receives the question, economic scope and missing dimensions, not a replay
of the observation ledger. Existing observations remain available to planning,
coverage assessment and checkpoints. No retrieved source text is truncated.

## Recovery and cost

- Accepted Tasks, including older processors, resume their saved run IDs.
- Search/Extract save submission intent and durable result receipts. Ambiguous
  paid POST outcomes are never blindly resubmitted.
- Pending follow-ups preserve the original API choice, queries and session.
- Changing the consuming model alone does not invalidate purchased web evidence.
- Search reservations use $0.005, not the configured deep-task price; Task
  reservations still use the selected processor price. Extract/model charges are
  explicitly outside that discovery estimate. No credit balance is invented.
- First searches take priority over follow-ups. There is no recursive research
  loop and no new output-token limit.

## Verification boundary

Verification on 23 September 2026:

- Full unit suite: 782 passed (5 warnings).
- After the final Search objective refinement: 87 focused retrieval/research
  tests passed, including oversized observation-ledger reuse without a new call.
- Focused correctness lint (`F,E9`) and `git diff --check`: passed.
- Frontend production build: passed; the existing large-chunk warning remains.

Mock-provider tests cover actual request bodies, concurrent dispatch, deduplication,
question-specific extraction, optional failures, selective escalation, receipt
recovery and model separation. Existing portfolio tests exercise information
boundaries, arithmetic, checkpoint reuse and partial-output retention.

These tests establish integration behaviour, not superior investment conclusions.
A paid end-to-end run and source audit are still required to measure financial
quality, actual elapsed time and total provider charges. Do not describe this
local change as deployed or as an improvement already demonstrated by a memo.

References: [Search](https://docs.parallel.ai/search/best-practices),
[Extract](https://docs.parallel.ai/extract/best-practices),
[API selection](https://docs.parallel.ai/getting-started/choose-an-api),
[pricing](https://docs.parallel.ai/getting-started/pricing).
