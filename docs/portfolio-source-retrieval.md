# Portfolio source retrieval

Implementation updated 23 September 2026; not a deployment record. Existing
running processes retain their startup settings. Configure `PARALLEL_API_KEY`.

Fresh discovery uses Parallel Search (`POST /v1/search`, `advanced`), starting
with five results. Known URLs use selective Extract. Task `ultra2x` is reserved
for justified, high-impact questions still unresolved after ordinary retrieval.
Search has no `ultra2x` processor: that setting controls deep research only.
Model Routing's Research group controls two internal assignments under Portfolio Analysis:

- Macro and news retrieval: `PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR`.
  Preserves the processor identity for already-paid initial tasks on recovery.
- Focused source research: `PORTFOLIO_POSITIONING_SOURCE_PROCESSOR`.
  Selects the deep-research escalation processor, not Search or Extract.

The existing Decision & Memo model plans focused questions (approved profile:
Opus 5.5). Evidence Processing remains separate (Luna Pro), handling observations
and coverage. Allocation & Review remains Sol. No extra planning stage or routing
group is added; the old planning calls change model. Initial orientation remains
three application-defined, holdings-blind subjects, not an extra paid planner.

Fresh portfolio research calls only Parallel, not xAI/Grok, Tavily or Perplexity.
The three initial subjects (macro outlook, sector leadership and structural
changes) dispatch three provider requests concurrently, one per subject. Removing
the overlapping Perplexity pass does not add replacement Parallel calls or change
the downstream analysis models. There is no extra
DeepSeek rewrite between Parallel and the existing evidence-processing stages.
Analyst Council's Perplexity lane and other applications' research integrations
are unchanged. This removes a second retrieval perspective, not a research subject;
quality and source coverage still need assessment in completed memos.

## Request flow

1. Initial discovery uses each lane's objective and complementary keyword queries.
   Focused questions receive planner-written queries. Send the consuming evidence
   model as `client_model` and a stable, question-specific `session_id`. This hint
   tunes returned context; it does not select Parallel's internal models.
2. Citation-only URLs are deduplicated and extracted in batches of up to twenty.
   The question's objective, queries, client model and session follow the URLs.
   Existing source excerpts are reused. Independent batches run concurrently via
   `POST /v1/extract`, not new Task research jobs. Accepted legacy Task extractions
   finish using their saved task IDs, including when the configured processor changes.
3. Workflow version 4 plans material research before the independent allocation
   and again after introducing current holdings. New runs use the checkpointed
   `play_assessment_mode: brief`: plays enter only final synthesis, using existing
   evidence, with no separate discovery, component inventory or reviewer work.
   Older checkpoints retain their original separate play-research phase.
   Holdings and plays remain absent from the independent phase; the ideal's weights
   are absent from the current-portfolio phase. The existing decision model
   plans core portfolio questions. Canonical economic keys
   combine paraphrases while preserving geography, period and horizon differences.
4. Reuse dimension-specific saved answers first. Each unanswered material question
   becomes a focused Search request with cutoff, geography, period, horizon and
   missing dimensions. Known observations stay with the planner and checkpoint,
   rather than being replayed into Search. Do not send portfolio weights, holdings JSON
   or a diagnostic checklist. Independent tasks run concurrently and save separately.
   There is no fixed three-question rule; selection uses a shared discovery allowance.
5. The existing coverage response may identify specific retrieved URLs to inspect.
   Extract those passages before deciding on further discovery. It may propose one
   focused follow-up for missing dimensions, with complementary queries; it cannot
   introduce a new research subject. Only an explicit planner justification plus a
   high-impact/critical unresolved premise can escalate successful Search to Task.
   Provider or processing failures are not permission to buy deep research.
   Successful earlier evidence survives any supplementary failure.
6. Reviewers and reconciliation use this research. A material portfolio challenge can
   receive focused research within the remaining allowance. Missing evidence
   qualifies the dependent recommendation, not the entire memo. Brief supplementary
   plays do not add follow-up questions or source-check obligations; an actual adopted
   allocation still receives the ordinary investment-case and source checks.

New runs use this ordering. Saved pre-v4 checkpoints keep their recorded workflow
version and legacy ordering; they are not silently relabelled as research-led runs.

Five is the initial Search result count, not proof of sufficient evidence.
New deep tasks can return additional necessary sources; the normalizer retains
them instead of slicing every deep packet to five. Historical Task result
normalization is preserved. URLs and excerpts are deduplicated without replacing
source text with generated summaries.
Known-URL extraction follows the [Parallel Extract contract](https://docs.parallel.ai/extract/extract-quickstart).
No live latency, cost or source-recall improvement has been established by the
offline adapter tests alone.

## Evidence and failure handling

For Task results, only excerpts in the returned citation `basis` become evidence.
For Extract, only returned `excerpts` for requested URLs become evidence. Per-URL
errors and usage remain in the receipt; successful excerpts survive partial failure.
Generated summaries and proposed quotations are not substituted for source text.
The original response, citation URLs, reported dates and processor are retained.
Reported dates remain subject to the existing source-support checks; a citation
is not independent verification of a claim.

Successful provider research is processed even when a peer retrieval fails.
Supplementary failures do not replace the reconciled baseline or discard the
memo. Failed questions and affected asset classes remain explicit. Final
analysis must qualify or defer dependent recommendations; the decision retains
unanswered questions with unverified conviction. An entirely absent core evidence
base still cannot support an allocation.

Unverified asset-class coverage metadata is also a visible limitation, not a
failed execution. Coverage remains unassessed; no source links or verification
are inferred to make the run pass. Job failure messages include blocking errors
only, not supplementary research or coverage warnings.

## Recovery and visibility

The checkpoint records submission intent before a paid POST, then the Parallel
task ID immediately after acceptance. Resuming polls that ID, without submitting
another paid task. An ambiguous submission is retained for reconciliation and
is never blindly retried. Transient status/result GET failures can be retried.
Outstanding tasks have a 90-minute local polling window and remain resumable.
Search and Extract requests have no task polling loop. Ambiguous paid POSTs are
likewise preserved, not blindly repeated; successful responses are durably saved
before shared-cache insertion.

Focused attempts are matched by question identity, actual query and dimensions,
within their original information boundary. A pending expansion resumes its exact
saved context, query options, model hint, session and API choice. A change to the
consuming model alone does not invalidate paid Search/Extract evidence. New relevant document versions can be inspected for old unanswered
dimensions; unchanged inspections are reused. Inspection does not grant another
discovery reservation. Results use incremental records and one full phase boundary,
not full-checkpoint writes around each result.

Progress records include provider task ID and status. Raw responses and each
question's evidence are checkpointed separately. Completed Tavily discovery and
extraction from older checkpoints may be reused, with original provenance;
there are no new portfolio Tavily calls.
Previously completed Grok packets are also retained on matching recovery, with
their original provenance. They are not relabelled as Parallel research. Legacy
Grok model settings are not passed to the Parallel API: the new market-context
processor uses its own configuration key.
Completed Perplexity responses may likewise be read from an exact matching
checkpoint, preserving their original model and provider. Missing or failed
Perplexity requests are not retried. New runs have no Perplexity requests, progress
slots or credential dependency; historical artifacts remain readable.

Apply only these two retrieval substitutions in the target app environment:

```sh
python -m scripts.configure_portfolio_models --retrieval-only --apply
```

This leaves every saved analysis-model assignment unchanged. Fly deployment
alone does not replace persisted processor overrides, so verify both effective
routes after applying the configuration. At published pricing checked on 23 September
2026, advanced Search costs $0.005 per request including up to ten results;
Ultra2x costs $0.60 per successful task. Extract costs $0.001 per URL. Model
processing is separate. Estimates do not establish actual run cost or latency.
[Parallel pricing](https://docs.parallel.ai/getting-started/pricing).

The OpenRouter funding check does not verify Parallel credit. Parallel remains
listed as an unchecked provider; missing credentials or depleted credit are
reported as research limitations, never represented as a successful search.

### Shared discovery allowance (version 4)

`PORTFOLIO_RESEARCH_BUDGET_USD` controls one run-level discovery estimate. Without
an override it equals the previous orientation estimate plus
`PORTFOLIO_FOLLOWUP_BUDGET_USD` (default $7.20): $9.00 with three lanes and Ultra2x.
The envelope is retained, but fresh orientation now reserves Search prices, not
Task prices. This does not increase the envelope. Citation
extraction and reasoning-model charges remain separate. Estimates are
not account balances or final invoices. No new output-token limit is imposed.

The independent and current phases may each use half the then-remaining allowance.
Within a phase, first searches take priority over expansion. Remaining phase funds
can cover one justified follow-up per question, at Search or Task cost as appropriate.
Deferred questions are retained with their reason.
Paid-task reservations persist across restart, and cached or already-submitted
tasks remain reusable even when no fresh-task allowance remains.

On Parallel HTTP 402, subsequent unsent requests stop without another paid POST;
already-submitted tasks remain pollable. A fresh resume can retry after funding.
Failed requests remain failed in progress, separately from answer coverage and
successful partial memo production. The UI shows answered/open questions and a
funding warning. Parallel's documented Account API requires separate user OAuth;
this API-key integration does not guess a balance or initiate an OAuth flow.
[Account authentication](https://docs.parallel.ai/integrations/account-api).

API references: [Task creation](https://docs.parallel.ai/api-reference/tasks/create-task-run),
[task results](https://docs.parallel.ai/api-reference/tasks/retrieve-task-run-result),
[research basis](https://docs.parallel.ai/task-api/guides/access-research-basis).

### Decision source checks (local update, September 23)

After retrieval, source-support checks target cited decisions, explicit factual
challenges and exact-scope comparators, not every observation in a research topic.
Checks are grouped by source and reused across checker-model changes when the
observation, source and rule contract are unchanged. Unavailable source text
remains unresolved without a model request. These are support checks, not new
searches or independent proof of source truth. See the
[implementation and measured trade-offs](portfolio-source-check-streamlining-20260923.md).
