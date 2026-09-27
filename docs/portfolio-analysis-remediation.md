# Portfolio Analysis Remediation

Branch: `codex/portfolio-analysis-integrity`

Scope: the 11 August 2026 audit. Preserve useful partial analysis, retain every configured role, and never translate missing research into negative investment evidence.

## Checklist

- [x] Stage receipts distinguish provider, transport, parse and semantic failures.
- [x] Successful stages can be reused while failed stages are repaired.
- [x] Missing source-review and investment-detail fields stay local; usable outputs and memo generation survive.
- [x] Job and saved-run health reflect incomplete analysis.
- [x] Macro retrieval has its own research profile and dated evidence contract.
- [x] All research lanes survive fallback; audit prompts stay out of model inputs.
- [x] Coverage distinguishes unassessed from irrelevant; conviction is evidence-based.
- [x] Macro prior is blinded by construction; keyword regime overrides are removed.
- [x] Synthesis failure retains disagreement without selecting a pretend winner.
- [x] Allocations have one funded current-to-target ledger; unresolved values stay null.
- [x] Mandate, instrument attributes and uncertainty accompany allocation decisions.
- [x] Trade comparisons and scenario sensitivities are calculated from explicit inputs.
- [x] Company/announcement evidence links into portfolio risk without converting scores into returns.
- [x] Typed review conditions and shadow-portfolio evaluation have API consumers.
- [x] UI has one decision view, inspectable health/evidence, and no repeated full memo by default.
- [x] Offline historical regression, failure/recovery, API and frontend checks pass.

External limitations: no implementation can reconstruct unavailable historical raw responses, buy provider credits, infer the user's mandate, or produce measured investment returns without instrument prices. These must be reported as missing inputs, never silently invented.

## Implemented Flow

New runs use workflow version two. Historical checkpoint recovery retains version
one and its original request shape; it is not silently migrated to a different
analysis. The September 17 workload update below is deployed in Fly release 344.

1. Freeze the research cutoff and snapshot. Resolve explicitly attached company council runs and their dated announcement evidence.
2. Collect the configured Grok, Perplexity and Tavily research lanes using macro-specific prompts. Keep original narratives and retained source excerpts, including incomplete retrievals. Check all required retrievals before starting extraction or reconciliation; one failed retrieval stops downstream model work while successful retrievals remain reusable.
3. Extract source-linked facts in batches of at most four source excerpts and 18,000 source characters. Long documents are split with 200-character overlap, retaining source identities and every character. Write each lane's overview separately. Check source support in batches of eight facts, then reconcile the reviewed ledger without requiring the model to re-emit all facts and checks. Preserve observation/publication dates, benchmark, unit, currency and vintage. An excerpt match alone cannot support conviction; macro observations cannot masquerade as market prices. These are model-based checks against retained text, not independent verification that a publisher or investment thesis is correct. Unsupported values and derived numbers remain available with review issues.
4. Run the macro prior once, without holdings, weights, values or exposure baskets. Freeze it before portfolio-aware allocation, exposure-equivalence review and defensive review. All configured roles remain mandatory.
5. Run each of the three portfolio-aware roles once and compare their proposals once, alongside the macro prior. After optional follow-up, the configured synthesis model resolves the final funded portfolio. Only that selected proposal receives instrument, market-pricing, investment-case and alternative details, four sleeves per request. Detail responses cannot add sleeves or change weights/actions. Missing enrichment stays unknown, with warnings; it does not reject an otherwise usable funded proposal. Omitted current holdings require explicit final weights or HOLD/EXIT instructions. Missing treatment stays null. Failed synthesis selects no winner. Allocators receive every fact, interpretation, disagreement and source reference, with redundant review metadata removed. Legacy resumes retain their original per-proposal enrichment.
6. Investigate up to three largest unresolved proposed changes in one additional research round, then reconsider the proposal. This reuses existing research/compressor/judge assignments; it does not add another model role. Transport failures suppress this optional expansion.
7. Write the decision, research, model receipts, prompts, settings and code manifest. Job success requires completed processing and coherent funding. Complete processing is distinct from an allocation whose assumptions still require review.
8. Evaluate supplied scenario exposures and dated review observations. Save subsequent reviews separately; never rewrite the frozen memo.

## Recovery

Native Grok research streams the xAI Responses API with both `web_search` and `x_search` available. Its defaults are independent of the company prepass: 600 seconds per attempt, 180 seconds without incoming data, and 12,000 output tokens. At most two attempts are made by default. Transient HTTP, timeout and disconnect failures may retry; output truncation retries with twice the token budget, up to 64,000. Permanent HTTP rejections do not retry. The old `PORTFOLIO_POSITIONING_MACRO_NEWS_MAX_TOOL_ITERATIONS` loop is retired: xAI performs server-side search calls inside one response, not through repeated submissions of the original prompt. The replacement setting is `PORTFOLIO_POSITIONING_MACRO_NEWS_MAX_ATTEMPTS`.

Only a completed response with assistant output is usable. Partial text and reasoning are not accepted as completed research. Response IDs, terminal state, typed errors, usage, timeout settings and individual attempts are retained; periodic progress is checkpointed. Full attempts remain under retained research, while stage receipts contain compact attempt metadata. Citation-only URLs carry no invented excerpts; uncited search results stay in the raw response rather than inflating the citation list. Streaming follows [xAI's agentic-search guidance](https://docs.x.ai/developers/tools/streaming-and-sync).

New runs create an adjacent `.checkpoint.json`. Structured-analysis cache keys include model, exact business inputs, request settings and a code manifest; the research cutoff remains frozen in the run and its inputs. On explicit resume, an identical saved request from the previous code manifest can be reused after passing current validation. Changed model, business input, settings or contract requires fresh work. Invalid cached output is not blindly reused. Retrieval has a separate versioned cache keyed by provider stage, exact query/settings/model and frozen cutoff, so changing analysis code does not rerun successful searches. A changed research query, model or retrieval contract does invalidate retrieval. Legacy version-one checkpoints can recover their original manifest from the adjacent artifact and migrate matching successful research entries. This is a resume of historical research, not a claim that old data is current.

Each structured call has at most three attempts, with at most four model requests in flight per run. Extraction, source review, lane overviews and investment-detail batches start with 12,000 output tokens; reconciliations and core allocation proposals start with 16,000. Commentary retains its 5,000-token initial budget. Output truncation is classified as `output_truncated`, including when the visible fragment happens to parse as JSON. Retries double the output budget up to a hard 64,000-token spending limit and request low reasoning effort. They regenerate from the original inputs rather than append a large cut-off answer. Exhaustion remains recorded as a failed model attempt; review/enrichment recovery can still finish the stage with explicit limitations. Models/providers can impose lower limits; these budgets are not a guarantee that every configurable model supports them.

HTTP 402/authentication/permanent model failures are retained without blind retries. Invalid JSON/schema or funding can receive a repair request; unsupported JSON response-format requests can retry without that parameter. No arithmetic normalization disguises an underfunded allocation. Cached results are copied before downstream enrichment, and each new run resets its lane context, keeping recovery keys stable.

Source reviews are recovered field by field. Valid verdicts and explanations remain unchanged; repair requests name only the affected fact IDs and fields and include their original sources. After bounded repair, missing verdicts become `unresolved`, never `supported`. A missing explanation leaves that fact's verdicts unresolved. Missing or unavailable review batches retain every original fact. Optional investment details and supporting proposal sections use unknown values or empty collections, with warnings; they cannot create assets or change funded weights. Resume retries unfinished stages and preserves already accepted outputs, including their warnings. Completion is not verification: caching an unresolved review never makes the fact supported. Older checkpoints can recover accepted-with-limitations output from its normalized receipt when no cache entry was recorded. This keeps the frozen macro prior stable and prevents optional enrichment retries from invalidating completed downstream analysis.

Missing required research, failed extraction/reconciliation, no usable required allocator or synthesis, and invalid funding still block dependent proposals. All raw responses and usable partial proposals remain available even then. Those failures are distinct from absent review/enrichment fields: recoverable gaps produce `Analysis complete with limitations`, not a failed job. The affected claims or allocations remain unassessed rather than being relabelled as verified. Failed attempts stay in receipts, alongside a terminal recovery receipt and its normalized retained output. Health reporting uses the latest result for each exact input. Missing investment data or mandate inputs remain explicitly unassessed; that is separate from a processing failure.

Partial artifacts are written atomically alongside checkpoints throughout execution, including the original input context and retrieved research. Unexpected exceptions produce an inspectable failed artifact and a nonzero exit. Recovery therefore does not depend on final memo generation succeeding. A process interruption leaves the last partial artifact available. Existing partial artifacts are not deleted when a recovery is started.

Stage details are inspectable on demand through `GET /api/portfolio-positioning-runs/{run_id}/stages/{stage_index}`. The normal run response contains compact receipts; requests, raw provider responses and normalized retained output are loaded only when opened. Raw responses are never rewritten to conceal a recovery. Legacy prompt-audit fields now contain the actual submitted contract, and are excluded from downstream model inputs.

`POST /api/analysis-jobs` accepts `job_type: portfolio_positioning` and `resume_portfolio_run_id`. The API reloads that run's frozen snapshot. A failed job with a saved portfolio artifact remains accessible through its result endpoint. Historical runs without checkpoints cannot claim stage-level recovery. Existing historical job statuses are not rewritten on application startup; their displayed analysis health is audited at read time.

## Review Inputs

`POST /api/portfolio-positioning-runs/{run_id}/review` accepts:

- `mandate`: base currency, benchmark, horizon, drawdown tolerance, minimum cash, tax/cost constraints, hedging policy.
- `exposures`: per-asset sensitivities, annual carry, transaction costs in basis points, currency, source and assumption basis. A sensitivity is percentage-point return per one unit of the named shock. Rate shocks are percentage points, equity/commodity/FX shocks are percent. A zero sensitivity must be explicit, not inferred.
- `scenarios`: name, horizon in months and named factor shocks. Results compare holding with proposed weights and supplied alternative allocations, after costs. The UI includes a cash alternative. This is a linear sensitivity exercise, not a probability-weighted return forecast.
- `observations`: metric, benchmark, unit, value, observation/publication dates and source URL. Typed conditions use these exact identities, freshness, threshold and direction. Wrong benchmarks or unavailable observations remain unassessed.
- `total_returns`: per-asset cumulative total return, base currency, aligned start/end dates, costs and provenance. Optional aligned `cumulative_total_returns` points support buy-and-hold drawdown calculations. Price changes alone must not be labelled total returns.
- `risk_assessment`: an externally supplied estimate for the exact proposed book: `allocation_hash` (returned with the decision), `estimated_max_drawdown_pct`, `as_of`, `method`, and `source_url`. Changes to allocations, instruments, base currency or horizon invalidate the binding. An estimate within tolerance is conditional on its method, never a guarantee against future losses. Model prose and terminal scenario returns are not treated as measured maximum drawdown.
- `alternatives`: explicit, funded allocations for scenario and shadow-return comparisons. The unchanged portfolio is always the baseline.

Forecasts store a probability, deadline and typed observation predicate. Matured forecasts can be scored using the Brier score; missing or premature outcomes are not scored. Reviews persist inputs, source-run hash and decision hash under `portfolio_reviews`. `GET .../{run_id}/reviews` returns saved reviews.

The page offers Evidence, Mandate, Scenarios, Conditions and Performance tabs. Unknown numeric values display as unresolved rather than zero. Historical strong-conviction labels are not presented as verified when processing was incomplete. The original memo remains available in a collapsed section.

Mandate fields are validated, proposed cash and investment horizons are checked, and the existing allocator/judge records its assessment against the exact supplied tax and hedging policies. Missing assessments stay visible. Merely populating a mandate does not establish compliance. A dated portfolio risk estimate can be supplied from the Mandate tab. Reviews do not silently rerun models or revalidate old policy assessments against new wording.

Performance starts no earlier than the memo's decision-availability timestamp and ends no later than the review timestamp. All series must cover the same period. Drawdown requires a zero starting point, matching period endpoints and a terminal value consistent with the declared total return. The named mandate benchmark is calculated separately without adding it to portfolio weights; absent benchmark data remains unassessed. Revised observations are selected by observation date and then latest available publication date; conflicting values for the same vintage remain unassessed.

## Data Connections And Limits

Company links preserve every supplied position and respect explicit `positions[].council_run_id` references. Otherwise, an exact exchange-qualified ticker selects the most recent dated council run available before the research cutoff. A bare or ambiguous ticker is not guessed. Selected references are frozen into the snapshot, and missing links are explicit. Announcement ingestion combines the ticker history and selected-run index, including filings saved against older baselines and processing-error filings. Versions are deduplicated by event ID and limited to information saved before the research cutoff. Processing failures and unreadable records are explicit coverage issues, including when company research is unavailable. The analyst receives facts and thesis context with instructions not to treat repeated catalyst announcements as independent confirmation; router scores are never converted to returns or automatic weights.

Input weights are never guessed from the size of a percentage or silently changed to zero. Explicit percentage fields retain their units. Position-derived asset-class totals require supplied weights, or known position values and the whole-portfolio value; missing inputs retain an unresolved row. Fact identifiers remain stable when source-support reviews change, preserving references across follow-up research.

## Second-Pass Regression Checks

The nine findings from the follow-up review have regression coverage in `tests/unit/test_portfolio_integrity.py`: relabelled facts and unsupported conviction; missing holdings; evidence-lane post-processing failures; crashed-run API recovery; invalid performance periods and inconsistent drawdowns; invalid mandates and allocation-bound risk assessments; missing/error announcement coverage; superseded observations; and trade-specific follow-up context. Tests also cover custom benchmarks, stable fact identifiers and zero-additional-call checkpoint reuse.

The follow-up query includes the instrument, current and proposed weights, rationale, pricing premise, contrary evidence and alternatives. The saved final consensus is updated after that comparison, retaining the earlier consensus separately.

`tests/browser/portfolio-live-api.mjs` exercises the actual backend through the Vite proxy, without mocking HTTP responses. It checks saved reviews, invalid input responses, dated performance, benchmark comparisons, unsaved changes and responsive themes. The preview backend uses an isolated copy of the August memo with provider credentials blanked; no production data or paid model calls are used. The existing browser suite separately covers the recovery interaction with mocked job responses, while API and runtime recovery are covered by backend tests.

Follow-up verification on 15 September 2026: **130 unit/integration checks passed**, using the same two explicitly documented exclusions below. Both browser suites, the frontend build, targeted ESLint, runner-copy comparison and `git diff --check` passed. No deployment or commit was performed. Model-based source checks can still make mistakes; retained excerpts, field-level reasons and request receipts remain inspectable.

**No background market-data subscription or unattended alert scheduler has been enabled.** Typed conditions have working consumers at run creation and review time, but their observations must come from supplied portfolio context or the review API/UI. Drawdowns and realized performance require sourced total-return series and instrument mappings. The August asset-class-only snapshot cannot supply those retrospectively. Automatic feed mapping and ongoing scheduled reviews need those external data contracts before activation.

The implementation does not execute trades. It does not infer user risk limits, invent factor estimates, assign arbitrary price bounds, or make a missing research result economically negative.

## Verification

### 17 September Credit Recovery

#### Workload Remediation Completed

The later workload changes are deployed in production release 344. Full findings,
before/after measurements and deployment verification are in
[the workload audit](portfolio-workload-audit-20260917.md#implementation-update).

- New runs keep all four roles and configured models, remove identical memo
  replication, enrich only the final allocation and write commentary once.
- Unchanged fact/source checks survive follow-up. Citation-only research sources
  are hydrated through the existing Tavily extraction service when available;
  missing dates and failed retrievals remain explicit unknowns.
- Raw execution data is stored in immutable `.portfolio-records` blobs beside
  artifacts, with compact checkpoint references. Back up that directory with the
  artifacts. Legacy checkpoints remain readable and retain their original flow.
- Portfolio submission and worker startup check OpenRouter account/key funding
  against a conservative estimate. Per-request checks preserve completed work
  when credit is insufficient. Recovery remains explicit; no automatic purchase
  or model substitution occurs. Separate research-provider balances are not
  verified by this check.
- Progress distinguishes business phase, reused tasks, new requests, retries and
  reported cost. Portfolio progress no longer invents a percentage before success.
  These details remain below the existing memo, in its existing diagnostics.

Verification: 262 scoped tests; actual 131-task checkpoint replay with zero model
calls (122 structured tasks plus nine saved retrievals); browser checks for the
original memo structure and responsive light/dark themes. On the same offline
fixture, model requests dropped from 47 to 19 while all 12 research requests
remained. This is not a live-run cost guarantee. Neither saved recovery was
restarted for this work; no volume resize or commit was performed. Production
runtime hashes, record-store smoke tests, credit preflight and saved-memo loading
pass. Partial and credit-paused artifacts preserve their workflow version so
recovery funding estimates use the correct workflow.

#### Earlier Recovery And Deployment History

The 16 September 12:26:27 UTC run stopped in allocation after OpenRouter credit and in-flight-budget rejections. Recovery on 17 September reused 79 stages and saved 112 completed stages before one defensive allocator encountered a transient `ConnectError`. OpenRouter transport exceptions were incorrectly marked non-retryable except for timeouts. Connection, read, write and remote-protocol failures now use the existing bounded retry policy; invalid protocols and permanent HTTP errors remain non-retryable. The transport fix passed 223 scoped tests and was deployed as `deployment-01M2PDE47PHKV4DDD1Y64XCPWC`.

A subsequent recovery exposed an input-stability bug: accepted-with-limitations detail batches were not cached. Re-generating an optional detail changed the frozen macro prior and invalidated otherwise completed allocator requests. That attempt was stopped. Accepted outputs now remain stable on resume, with warnings intact; only unfinished requests are retried. The updated suite passes 224 scoped tests. The full mocked pipeline makes zero extra calls on resume even with missing review or investment-case fields.

`scripts/audit_portfolio_checkpoint_reuse.py` verified the actual saved recovery checkpoint entirely offline: all 103 completed structured stages, including six with limitations, were reused without any model calls and with identical retained output and warnings. Together with nine separately cached retrieval stages, this preserves the 112 completed stages. Original runs and interrupted recovery artifacts are retained. Completion outcomes for the two requested recoveries are recorded separately when verified.

The stable-resume fix is deployed as `deployment-01M2PEFBCTNHFZ74RGH05X49EJ` (digest `sha256:4a03d6ab334db8ee166b0c55b237380846fe7b2e894cefed67cc4cb9d2be9928`). Both changed runtime-file hashes match the tested source in production, readiness returns 200, and Fly smoke/health checks passed. Recovery `a1424e6d-167a-4705-b2bf-8e3b3d672862` resumes the 00:30:09 checkpoint, preserving its original research cutoff and accepted outputs, rather than the intentionally stopped retry whose optional enrichment had changed.

That recovery reused all 112 completed stages and completed seven additional stages, including the previously failed defensive allocator. At 01:30:37 UTC the Fly kernel killed the worker for running out of memory (`SIGKILL`, return code -9); the checkpoint retained 119 completed stages. The old writer built a whole-document Unicode string and UTF-8 copy. Replaying serialization of the actual 147 MB checkpoint locally measured 1,122.83 MiB peak allocation. Streaming the same JSON with lossless ASCII escapes reduced that peak to 1.52 MiB; decoded data was identical. Checkpoint and final-artifact writes now share this atomic streaming writer, and completed receipts and cache entries are saved together. A valid completed receipt can also recover an interrupted cache commit after current validation. No source text, prompts, model output, or warnings are removed.

Process signals now take precedence over an earlier model warning in the job failure message. SIGKILL is identified as worker termination with a direction to inspect server memory/termination logs, not asserted to be OOM without those logs. Verification: 229 scoped tests passed; the memory-interrupted checkpoint reused all 110 completed structured stages plus nine retrieval stages offline with zero model calls. Seven completed-with-limitations results retained their warnings. The newer recovery remains incomplete pending continuation; the earlier original run has not yet been restarted.

The memory fix is live in Fly release **341**, image `deployment-01M2PG30NSE03XXHFR9JFRDN49` (digest `sha256:f27fd3906181061a69e76f258a712d2fe261ee8ea815e41517934982f9b762de`). Production hashes for the runtime, job executor, and both runner copies match tested source; readiness and Fly checks pass. Job `a07cf25c-e0af-44b0-b8ca-12a5ea6cd462` resumes the memory-interrupted checkpoint. No model assignments, UI, or original artifacts were changed.

The workload audit is in `docs/portfolio-workload-audit-20260917.md`. A follow-up cache patch, pending deployment after the active worker exits, defers writes for already-durable cache hits and retains manifest ancestry across interrupted upgrades. New model results still checkpoint immediately. The interrupted-upgrade regression, cache-write regression, full mocked pipelines and actual historical reuse audit pass: **231 scoped tests** and 119 historical completed tasks reused with zero model calls. Analytical simplification is documented separately and has not been applied to these recovery runs.

Further runtime verification passes **234 scoped tests**. Active-request checkpoint writes now run through an ordered background writer; snapshots preserve partial analysis, and version ordering prevents a stale write replacing a newer one. New results await persistence before returning. Research stream progress is logged rather than rewriting the complete artifact on every tick; terminal results still checkpoint. OpenRouter transport errors retain their exception-cause chain. This addresses confirmed event-loop blocking, but does not retrospectively prove the cause of every blank connection error in the active recovery. A 106,541,056-byte abandoned temporary checkpoint from the terminal 00:30:09 recovery was backed up locally and hash-verified before removal; its valid main checkpoint and artifact were untouched. No saved run was deleted.

These runtime corrections are now deployed in Fly release **342**, image `deployment-01M2PKNFGTDGJ22B1N441QHXDY` (digest `sha256:5b2f53a48b4de32d915246d10f92591a372c10c6b6107c14ac2d599a7c2a7ba6`). All five deployed runtime-file hashes match tested source; readiness and Fly smoke/health checks pass. The agent-launched 01:38:47 recovery was stopped at 02:37:30 UTC after checkpoint writers closed, retaining 131 completed tasks and the two latest failed judge attempts. Its checkpoint is backed up locally. Offline replay reused all 122 structured tasks without calls; nine retrieval tasks remain cached, and 13 completed-with-limitations results retain their warnings. No paid recovery is active: the attached 3 GB volume has about 656 MB free, and a 5 GB extension has been requested before generating another growing checkpoint. Both original runs remain preserved, the earlier run has not yet been resumed live, and Brightstar remains cancelled. Analytical simplification is still a separate proposed change, not silently applied to saved runs.

### 16 September Review-Failure Containment

Audited run: `portfolio_positioning_job_portfolio_positioning_20260916_110523.json`, 21:05:23 to 21:44:46 AEST. All nine retrieval stages completed, including all three native Grok searches. The run retained 296 facts and 79 sources. Of 37 source-review batches, 36 completed. Batch 17 first exhausted its output budget, then twice returned eight reviews with one missing `checks.currency` verdict for `fact_57346a878bf6a0055807` (USD/INR). The old generic repair request did not identify the field. The portfolio-integrity uplift's all-or-nothing validator then prevented allocation and memo generation. The failure was in our review policy, not a new Grok failure or absent research.

The new recovery policy preserves the seven complete reviews and the affected fact's other verdicts. It requests only that currency check. If the repair still does not provide it, the currency check remains unresolved and memo generation continues. The same failure containment applies to missing investment-detail fields, without weakening allocation arithmetic or inventing data. No model assignments or UI layout were changed.

`scripts/audit_portfolio_review_recovery.py` replays the saved artifact and checkpoint entirely offline. It reused all 63 completed structured-processing stages after current validation and simulated only the one-field repair, deliberately returning no verdict. Result: 64 processing stages completed, all 296 facts and 79 sources retained, and one unresolved currency warning. The original artifact hash stayed `d0e47b60e2ed8bf79817565e336aa6928485c4636db05c68d53af5ebc33fb41c`. The report is at `outputs/audits/portfolio-20260916-review/recovery-audit.json`. This replay does not generate a new live investment memo or contact providers.

Regression coverage includes truncated responses, targeted repair, preserving accepted verdicts, malformed/duplicate/missing reviews, unavailable reviewers, missing enrichment, unchanged weights, invalid funding, current-rule checkpoint validation, malformed cached results, and repeated recovery of only missing work. Full mocked pipelines generate memos with both omitted source-review fields and omitted investment-case details. The executor accepts those outputs as complete with limitations rather than failed. Final scoped verification: **217 tests passed**, excluding only the two previously documented unrelated failing modules below. Runner copies match, Python compilation and `git diff --check` pass. No paid calls were made for this verification.

Deployment: failure containment is live in Fly release **338**, image `deployment-01M2N2MXRN8A65VRD12S4R4CE3` (digest `sha256:b9e767bd1089901111fe46ce83cc053eb5abb019fd3d70ecfc609e9dac073f8f`), verified 16 September 2026 at 12:23 UTC. All seven changed runtime-file hashes match the tested source. The production-container smoke test retains an omitted currency review as unresolved and reports `Analysis complete with limitations`, with zero provider calls. Fly readiness, the portfolio page and authenticated saved-run APIs pass. The frontend assets remain `index-BjVH35BX.css` and `index-g62bS1Ex.js`. The 217-test scoped suite passed again before rollout. No active jobs were interrupted; the original failed run and its resumable checkpoint remain available. It has not been rerun, and no commit was made. The earlier native-Grok streaming fix was already deployed as `deployment-01M2MX5ZKH1XP5XC5XHGNPXFFR` before this audited run.

### 16 September Native Grok Failure

Audited run: `portfolio_positioning_job_portfolio_positioning_20260916_091551.json`, started 19:15:52 AEST and finished 19:48:20 AEST. All three `grok-4.6` research calls failed at approximately 90 seconds, without a recorded HTTP response. The deployed native client used a 90-second timeout and 900-token output budget. Empty exception messages were saved as empty errors, causing the UI's unhelpful `Stage incomplete` fallback. The exception class was not retained, so an exact original `ReadTimeout` cannot be proven retrospectively; timings and the targeted replay strongly support timeout as the cause.

This was not another unresolved structured-JSON failure. The run made 72 structured model attempts, completed 64 distinct stages, and recovered all eight output-truncated attempts. It retained 329 facts and 67 sources before the late research dependency check stopped allocation. That allowed roughly another 31 minutes of processing after the Grok failures were known. The retrieval barrier now prevents this expenditure.

Targeted paid verification replayed only the three original Grok prompts from the Fly machine, with its existing credentials, unchanged `grok-4.6` model and both native search tools enabled. Production code and the saved failed artifact were not overwritten. Each request completed on its first attempt:

| Lane | Duration | Web searches | Output tokens including reasoning | Cited URLs |
| --- | ---: | ---: | ---: | ---: |
| Macro regime | 126.88 s | 16 | 7,045 | 8 |
| Sector leadership | 141.60 s | 23 | 7,757 | 10 |
| Coverage audit | 161.84 s | 23 | 8,955 | 17 |

The model chose web searches in these tests; no X searches were reported. Assistant summaries contained 7,468, 8,337 and 10,466 characters respectively. These results verify retrieval and completion, not the truth of every financial claim or the success of a full portfolio run. Allocator and memo calls were not replayed.

Receipts and the failed artifact are retained locally under `outputs/audits/portfolio-20260916-grok/`. The diagnostic's initial `summary.json` counted all returned search URLs as citations; the final extractor counts only assistant citation annotations, as shown in the table. All original raw responses were replayed offline through the final parser, retaining identical assistant summaries, usage and response IDs. `scripts/verify_portfolio_grok.py` provides an explicit paid diagnostic for future reproductions; it never launches downstream analysis.

Final scoped verification at that point: **197 tests passed** with the two documented existing exclusions below. The unfiltered suite also reproduced the same seven unrelated failures: five cross-event-loop service-surface failures and two outdated Stage-2 model-call mocks. New tests cover streaming and native tools, timeout recovery with empty exception messages, absolute deadlines, truncation, interrupted streams, malformed/empty/provider errors, permanent HTTP errors, missing credentials, compact receipts, progress checkpoints and the global retrieval barrier. Runner copies match and `git diff --check` passes. No UI or model assignment changes were made. The native-Grok fix was subsequently deployed; see the newer review-failure audit above.

### 16 September Output-Failure Regression

The previous saved failed run contained 29 length-terminated responses among 34 model attempts. Its three evidence packets contain 24 sources each. The new splitter covers each packet in six batches; the largest source-text batch is 13,636 characters. This measurement uses the retained historical artifact without contacting providers; it is not a successful live rerun.

`tests/unit/test_portfolio_runtime_recovery.py` covers length-terminated valid-looking JSON, reasoning-only exhaustion, bounded escalation, permanent provider errors, unsupported JSON-mode fallback, semantic repair, source preservation, frozen-research reuse across code changes, legacy checkpoint migration, cache isolation, early dependency stops, actionable error banners, funded-weight preservation and recovering only a failed detail batch. The full offline pipeline also exercises all configured roles and resumes with zero additional model calls. No model assignments or memo layout are changed by this remediation.

Verification: the unfiltered unit suite plus portfolio integration tests returned **178 passed, 7 failed**. All seven failures are the previously documented service-surface event-loop and Stage-2 mock-import tests, outside this change. The frontend production build passed and produced the same asset hashes as before this remediation. The two runner copies match and `git diff --check` passes. Provider-error tests use mock HTTP transports; no paid live rerun or production deployment was performed. Nonzero portfolio subprocess exits now retain the detailed saved-artifact error instead of replacing it with a generic return-code message.

Initial verification on 15 September 2026, before the second-pass findings above:

- 111 unit/integration checks passed with `PYTHONPATH=.:tests/integration .venv/bin/pytest -q tests/unit --ignore=tests/unit/test_service_surface.py --ignore=tests/unit/test_source_fact_context.py tests/integration/test_portfolio_positioning_memo.py`.
- A complete mocked pipeline exercised all research lanes, the frozen prior, required allocator roles, targeted research, final synthesis and recovery. The second pass made zero additional model calls. Numeric, point-in-time, source-reference, semantic, failure and API cases are covered.
- The complete unfiltered unit suite was also attempted. Two existing modules remain failing outside this portfolio change: five service-surface tests reuse an asyncio queue across TestClient loops; two Stage-2 source-context tests patch an outdated model-call import. The initial collection also requires `tests/integration` on PYTHONPATH. Those are not reported as passing.
- Initial legacy tests unexpectedly attempted provider calls because their mocks did not cover the separated prior and existing Stage-2 imports. Billing for accepted requests was not verified. A new unit-test HTTP guard now prevents external requests; final verification was isolated from providers.
- Playwright passed with the historical August artifact: invalid funding is visible, targets are not normalized into a misleading 100% bar, only one allocation table exists, the original memo starts collapsed, light/dark themes work, and Evidence/Mandate/Scenarios/Conditions/Performance fit 390px, 768px and desktop widths. Review and recovery actions used mocked HTTP responses; backend behavior is independently tested.
- `npm run build`, targeted ESLint and `git diff --check` passed. Vite still warns about the existing large application chunk; npm reports dependency advisories that were not automatically upgraded in this scoped change.
- Root and `scripts/` portfolio runners are byte-identical. No Fly deployment or commit was performed.

Browser reproduction: run Vite on port 5184, then `PLAYWRIGHT_MODULE=/path/to/playwright node tests/browser/portfolio-integrity.mjs`. This uses the saved ignored audit artifact at `outputs/audits/portfolio-20260811/run.json`; it does not fetch production or invoke a model. Screenshots are under `outputs/audits/portfolio-remediation/browser`.

### 17 September Local Visibility Follow-Up

The local-only progress/checkpoint pass is documented in
[`portfolio-workload-audit-20260917.md`](portfolio-workload-audit-20260917.md#local-progress-and-checkpoint-pass-not-deployed).
It distinguishes queued work, active model calls, retries, saved results and
worker heartbeats, while preserving the memo presentation and request contracts.
It has not been deployed and does not interrupt or modify an already-running
production analysis.
