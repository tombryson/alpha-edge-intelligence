# Portfolio Failure Audit: 17 September 2026

## Conclusion

This run failed because the application sent a 4,526-character analysis prompt
to Tavily's search endpoint, exceeding its 1,500-character limit. A single failed
supplementary search then prevented the final synthesis, investment-detail pass
and memo, despite completed initial research, all four allocator proposals, an
allocator comparison, and successful Grok and Perplexity follow-up research.

This is a request-construction defect compounded by overly broad failure
propagation. The recorded terminal cause is not insufficient credits, a JSON
parse error, a deployment interruption or an out-of-memory termination.

No application code was changed, deployed or restarted during this investigation.
One diagnostic Tavily request repeated the rejected query to capture the error
body the application had discarded. No analysis pipeline was restarted and no
model analysis was purchased during the audit.

## Evidence

- Job: `21aa8b35-af76-4c81-acd0-d7b28d8135f4`.
- Artifact: `portfolio_positioning_job_portfolio_positioning_20260917_044730.json`.
- Fly release 344; image `deployment-01M2PQEQEWQMTQW0S4PB5387ZM`.
- Started **14:47:30 AEST**; failed **16:18:36 AEST**, 17 September 2026.
- Elapsed **91 minutes 6 seconds**; subprocess exit 1.
- The separately developed progress/checkpoint pass remains local and was not
  present in this production worker.
- Downloaded artifact, checkpoint, job record, deployed search/provider/runner
  source and referenced immutable records to
  `outputs/audits/portfolio-20260917-tavily/`.
- SHA-256 integrity checks passed for all 147 receipt records and the records
  referenced by 121 successful cache entries.

The single-request replay returned HTTP 400 with:

```json
{"detail":{"error":"Query is too long. Max query length is 1500 characters."}}
```

Current [Tavily search guidance](https://docs.tavily.com/documentation/best-practices/best-practices-search)
also specifies queries under 1,500 characters and separate focused subqueries
for complex research. An older help article still mentions 400; the live response
and current documentation resolve that discrepancy. Initial requests of 820,
862 and 873 characters succeeded in this run.

## Failure Chain

1. The initial three research lanes completed successfully. Source processing,
   review and reconciliation completed; 529 facts were retained.
2. The macro prior and three complementary allocators completed, followed by a
   comparison containing 25 target allocations.
3. The follow-up planner selected Energy Producers, Bonds and Gold Miners based
   on the largest proposed portfolio changes.
4. `_trade_research_questions()` copied full trade objects, rationales, contrary
   evidence, fact identifiers and diagnostic messages into a JSON array.
5. The runner concatenated that array with the original broad analysis request,
   follow-up instructions and research-cutoff instructions.
6. `TavilyResearchProvider.gather()` bypassed search-query reformulation for
   `research_profile="macro"` and passed the entire string to `perform_search()`.
7. Tavily rejected it in **0.80 seconds**, at 16:14:17 AEST.
8. Concurrent follow-up calls nevertheless finished and were saved: Grok in
   approximately 220 seconds and Perplexity in 243 seconds. Citation extraction
   also ran and completed.
9. `_research_failure()` treated the one provider error as failure of the whole
   follow-up lane. Its evidence brief therefore contained no extracted facts.
10. Reconciliation combined the previous evidence with the incomplete follow-up
    and set the aggregate evidence status to incomplete. The explicit
    `runtime.require()` before final reconsideration then stopped the pipeline.

The original facts and proposals were not deleted. The application nevertheless
produced **no final memo** and presented the run as failed.

## Findings

### P1: Analysis Instructions Used As A Search Query

`backend/research/providers/tavily.py:35` passes the macro prompt through unchanged.
The deployed runner assembles the follow-up from full structured trade objects
at `portfolio_positioning_memo.py:2774`. There is no provider-specific query
planner or request-length check before dispatch.

The non-macro path previously used `reformulate_query_for_search()`. The macro
bypass is visible in the current diff against HEAD. This demonstrates the changed
behavior, but the uncommitted worktree does not provide a reliable commit date
for its first production introduction.

**Correction:** keep the full analytical brief for reasoning agents, but produce
short, explicit search queries per material evidence question for Tavily. Check
the provider's request contract locally. Do not blindly truncate the first 1,500
characters: that would discard later trades and their research questions.

### P1: Deferred Work Is Mistaken For Missing Research

Workflow two deliberately removes `implementation`, `market_pricing`,
`investment_case` and `alternatives` from allocator response schemas and requests
them later, once, for the final allocation. The model is explicitly instructed
not to emit those fields in its provisional proposal.

However, `build_decision()` immediately evaluates those provisional proposals
using the final-detail requirements, and its diagnostic strings become follow-up
research priorities. All three selected trades had the four deferred fields set
to null and the same 11 diagnostic messages, including missing holding periods,
cost assumptions, instrument currency and alternatives.

This creates predictable extra research from fields absent by design. Some items
are analytical work not yet performed, some require investor inputs, and some
are genuine external evidence gaps. They should not share one search queue.

**Correction:** distinguish pending analysis, missing mandate/implementation
inputs and researchable evidence gaps. Generate specific market questions from
the proposed trade and the evidence, not from a generic missing-field checklist.
Only genuine material gaps should trigger the conditional research round.

### P1: Supplementary Provider Failure Stops The Entire Memo

The follow-up lane uses the same all-providers-required test as the initial
research barrier. The initial barrier was added to avoid spending on downstream
analysis after required retrieval failed. Reusing that policy here makes one
supplementary search a fatal dependency of already-completed work.

The failed follow-up also overwrites the main evidence status with an incomplete
merged view. The prior successful evidence and allocator comparison remain in
the checkpoint, but are no longer the active completed analytical state.

**Correction:** retain the completed baseline evidence and provisional decision
separately. Process usable supplemental sources, record the failed provider and
any unresolved questions, and allow a memo with explicit limitations. Where a
material proposed change lacks support, defer or qualify that change; do not
invent verification or present a provisional allocation as final. A total lack
of usable core evidence remains a distinct failure condition.

### P2: Error Detail Was Discarded

`backend/search.py:79` returns only `Tavily API error: 400`. It discards the
response body and structured provider reason. The runtime subsequently labels
the research failure `empty_research`, despite the specific request rejection.

**Correction:** retain sanitized provider error detail, HTTP status, query
length and request identity. Distinguish invalid input from quota, transport and
empty-result failures. A malformed request needs correction, not repeated
unchanged retries or a model substitution.

### P2: Long Runtime And Prompt Volume Remain Significant

| Work | Completed tasks | Model attempts | Observed wall time |
| --- | ---: | ---: | --- |
| Initial retrieval and citation text | 10 | Not model-stage calls | 3m 29s |
| Fact extraction | 32 | 40 | 15m 24s |
| Three evidence briefs | 3 | 6 | 18m 37s, overlapping extraction |
| Source review | 67 | 77 | 28m 03s |
| Evidence reconciliation | 1 | 2 | 2m 51s |
| Independent macro prior | 1 | 1 | 1m 05s |
| Portfolio-aware allocator | 1 | 1 | 1m 26s |
| Exposure-equivalence reviewer | 1 | 1 | 4m 24s |
| Defensive-regime reviewer | 1 | 3 | 19m 43s |
| Allocator comparison | 1 | 1 | 2m 08s |
| Follow-up retrieval and citation text | 3 successful, 1 failed | Not model-stage calls | 4m 10s |

These are stage-group wall spans, including queue time in this deployed receipt
format; concurrent spans must not be summed. Extraction plus briefs occupied
approximately 29 minutes overall. The run made **132 structured model attempts**:
108 distinct completed tasks plus 24 retries. Retry causes were 18 output
truncations, five semantic-validation failures and one upstream provider error.
There were 14 retrieval/citation tasks, of which 13 succeeded.

The defensive allocator's first request contained **211,937 input tokens**. Its
evidence payload alone was about 698,000 JSON characters, of which approximately
628,000 represented the full 529-fact ledger. This is not a compact decision brief.
Its second response produced a 126% allocation; the third repaired the funding
total successfully. The arithmetic repair was appropriate, unlike treating a
missing optional research provider as loss of the entire memo.

That second request lasted **17m 45s** with `timeout=360`. The client supplies the
value to `httpx.AsyncClient`, which implements network-operation/inactivity
timeouts, not a total elapsed deadline. See [HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/).
The saved receipt proves the long request, but does not record network chunks or
provider-internal activity, so the exact reason it stayed active is not proven.

**Correction:** retain the canonical full ledger for provenance, but send
decision agents a focused, source-linked evidence brief with access to relevant
detail. Keep contrary evidence explicit. Separate queue, dispatch, provider
activity and elapsed time in telemetry; do not describe an inactivity timeout as
a six-minute total deadline. Avoid introducing a short hard deadline that simply
creates another output-loss problem.

Reported OpenRouter cost was **US$3.169661**, excluding xAI, Perplexity and Tavily
charges. This is not the total multi-provider bill.

### P2: Evidence Diagnostics Are Too Coarse

All 529 retained facts had source-review records: 83 were fully supported under
the current nine-field rule, 379 unresolved and 67 unsupported. Review hashes
still matched their facts, so this was not lost review metadata.

Nevertheless, the three selected trade diagnostics said their facts had not been
checked. That confuses "checked but not fully supported" with "not checked".
Their cited facts included no fully supported references under that rule. Two
comparison references, for Long Government Bonds and Gold Miners, were absent
from the judge's supplied fact ledger entirely.

**Correction:** distinguish not reviewed, reviewed with unresolved fields,
contradicted and invalid reference. Treat invalid citations as repairable
provenance defects, preserve usable analysis, and tie each material claim to the
fields that actually support it. Completion of the run is not proof of financial
correctness or investment merit.

### P2: Existing Tests Missed This Combination

The portfolio integration tests mock provider `gather()` calls, so they do not
exercise the generated follow-up text against Tavily's request contract. There
is an explicit test expecting any required initial retrieval failure to stop
downstream work, but no corresponding separation of a late supplementary failure
from successful core research. Deferred-detail omissions were also not tested
as inputs to the follow-up planner.

Required regressions should cover an actual oversized saved follow-up, each
search query's length and trade coverage, missing-by-design detail fields,
sanitized error bodies, successful supplemental providers alongside a failed
provider, retention of completed baseline evidence, invalid citations and
resumption without replaying successful requests.

## Recovery

The checkpoint contains **121 successful cache entries**: 108 structured model
tasks and 13 retrieval/citation tasks. The four allocator proposals and the
comparison are saved. There is no completed final synthesis or memo to recover.

Offline replay of all 108 structured requests passed against current validation
with **zero model calls**. All cache and receipt references passed integrity
checks. This establishes reusability of those exact saved requests, not a claim
that a future run with different models or changed prompts will reuse everything.

Do not restart from scratch. Correct the Tavily query construction and late-stage
failure handling first, then resume from this checkpoint with the original
research cutoff and unchanged completed request contracts. Blindly clicking
recovery on the deployed code would resend the same oversized query.

Audit reproductions:

```bash
PYTHONPATH=. .venv/bin/python outputs/audits/portfolio-20260917-tavily/audit.py
PYTHONPATH=. .venv/bin/python scripts/audit_portfolio_checkpoint_reuse.py outputs/audits/portfolio-20260917-tavily/run.checkpoint.json
```

Both commands are offline and read-only. Keep `.portfolio-records` with the
checkpoint. Original production artifacts were not modified.
