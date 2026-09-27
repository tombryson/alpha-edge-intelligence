# Independent Portfolio Memo: Build And Verification

18 September 2026. Branch: `codex/portfolio-independent-memo`. The initial build used offline tests only. A subsequently authorized paid live exercise found release-blocking defects; see [the live comparison](portfolio-independent-live-comparison-20260918.md). No deployment has been made. Existing uncommitted work was retained.

## Supplementary Plays (September 23)

New runs use `play_assessment_mode: brief`, persisted in the checkpoint. Plays are optional ideas, not a parallel research programme:

- Independent and current-aware research, proposals and portfolio reviews do not receive plays or reserve discovery allowance for them.
- Plays enter only in final synthesis, after core research, baseline proposals, reviews and investment-case work. This existing call assesses each idea once from available evidence: score or unassessed, verdict, a short rationale, and portfolio action. Aim for about 60 words per play; this is a writing instruction, not output truncation.
- No play decomposition, inventory repair, per-component reviewer jobs, or play-only discovery/source-check work. A missing play assessment does not discard the main output or trigger another call.
- Any actual allocation adopted from a play receives the normal investment-case and source checks. Unresearched ideas remain explicitly unassessed; absence of research is not a negative investment judgment.
- Plays appear together near the end, before supporting research. The saved play library and submitted ideas are unchanged.
- Checkpoints created before this change retain the component-based contract. Historical memos are not rewritten on load. No production deployment or paid rerun is part of this change.

Verification: focused tests cover missing assessments, retained scores, final-delta handling, actual-allocation source checks, funding estimates and checkpoint policy. An end-to-end replay expands one idea to six and confirms that new model work starts at final synthesis, reusing upstream research, proposals and reviews. An unpaid preview using the September 23 saved parent assessments reduces the play section from 1,907 to 226 words; desktop/mobile light and dark rendering pass without horizontal overflow. This is presentation and orchestration verification, not a measured improvement in live model quality or runtime. Preview evidence: `outputs/audits/portfolio-finish-comparison-20260923/brief-plays/`.

## Original Flow (September 18)

1. Neutral market research using only the research cutoff and explicitly supplied investment constraints. Holdings-derived categories, company evidence, portfolio free text and plays are absent.
2. The macro-first role saves its independent ideal and request/output hashes.
3. The portfolio-aware role assesses the current book without seeing the ideal's weights or plays.
4. The existing exposure and defensive roles critique both views and assess every submitted play. They no longer each produce another compulsory full allocation map.
5. A provisional comparison identifies material questions. Existing evidence is reused; at most three focused Parallel Ultra2x follow-ups use five initial results.
6. Review source support for allocation-linked claims. Batch investment-case work for new exposures, proposed positioning changes and challenged exposures.
7. Final reconciliation can revise or reject the provisional idea after considering those findings. The two original views remain separate and unchanged.
8. Financial commentary and the complete sectioned memo are rendered, with sources collapsed and implementation/provenance checks in the existing appendix.

New runs use workflow version 3 and the `independent-portfolio-v1` contract. Existing checkpoints keep their original workflow version. The root runner and mirrored `scripts/` entry point are identical.

## Reader And Inputs

- Existing historical memo text and recorded rows are not rewritten on load. Model thesis conviction is distinct from implementation readiness. Missing historical receipts qualify provenance rather than erase the investment judgment.
- A 37.58% holding in a 30-42% range can remain HOLD with a 35% reference. Point-reference arithmetic remains separately available in the funding ledger.
- The new memo shows an independent ideal table, a separate current-book assessment and its proposed alternative, and the practical recommended portfolio table. Older memos keep their established reading layout and both themes.
- Investment plays are entered in the Trading Terminal: Portfolio > Run portfolio analysis > Investment plays. Optional title/thesis rows accompany the original job in `portfolio_context.investment_plays`. Start analysis explicitly submits the job; opening or cancelling does not. The saved-memo reader has no plays editor. Submitted hypotheses enter the analysis only after both initial views are saved.
- The Terminal maintains a reusable library in its existing SQLite settings store, one `portfolio_investment_play:<uuid>` record per play. Drafts autosave; each analysis receives only explicitly selected plays, copied as title/thesis inputs. Library edits and deletion do not mutate previous runs. Saving individual records preserves other plays added from another browser; concurrent edits of the same play use the existing settings API's last-write-wins semantics. No database migration or provider call is required to save a play.
- Plays receive an explained integer investment-case score or an explicit unassessed result, plus include/watch/reject/needs-research. Scores do not determine weights. Differing reviewer scores/verdicts remain visible.
- User alternatives are stored separately through the review API, labelled unreviewed, with total weight and funding consequences. They do not modify model outputs or holdings. Saved alternatives remain inspectable.
- Supporting data is still lazy-loaded. No large research artifact is needed to initially read a memo.

## API Contract

### Optional Profile Inputs (September 21, 2026)

The Terminal launch dialog now offers `risk_tolerance` (`low`, `medium`, `high`)
and `time_horizon` (`1-2 years`, `3-5 years`, `5+ years`). Both start unspecified,
autosave in the existing `portfolio_investment_brief` settings record and enter
each new job through `portfolio_context.mandate`. Existing exact `horizon_months`
values remain visible and unchanged unless the user selects or clears a range.
A selected range replaces the exact-month value, never an invented midpoint.

Both independent and portfolio-aware allocations receive these explicit
preferences; the independent view still cannot see holdings or plays. Risk
tolerance is willingness, not financial capacity or a numeric drawdown promise.
The range can qualify an investment with a longer required holding period;
`5+ years` supplies no upper bound. Neither missing preferences nor a timing
mismatch discards the memo. This addition does not change models, research
budgets, output limits or existing saved memos. Deployed to UAT and production
on September 21, 2026.

Verification: 503 portfolio backend tests, five brief unit tests and 12 isolated
Terminal browser tests pass. TypeScript checking passes. Browser tests cover
saved settings, selected plays, clearing preferences, old exact horizons and
light/dark layouts at 1440, 390 and 320 pixels. No paid inference was performed.

Deployment record:

| Service | Fly release | Image digest |
| --- | --- | --- |
| `alpha-edge-uat-frontend` | 1234 | `sha256:d25b1ce5f02dc2908a062bf547a103d28374e0c9b0faa40cc04d099527009bbf` |
| `alpha-edge-frontend` | 617 | `sha256:5a9fc41d5c0b6860f96908cba3f008aab95cce194812349f9c7edfa0914b131a` |
| `llm-council-analysis` (shared memo backend) | 357 | `sha256:dd687c321e508dfc8fb6f7734d90bf9d21d686dee776d18f77d3ac8429576991` |

Fly health checks pass. Public frontend bundles match the deployed files and
contain all profile options. Both environments retain their existing API targets
and authentication configuration; unauthenticated Council requests return 401.
The Intelligence source manifest matches all 26 local entries, and remote checks
preserve all nine risk/horizon combinations. Saved memo and model-routing hashes
are unchanged. The terminal backend releases remain production 190 and UAT 196:
their existing settings API supports these inputs without a migration or redeploy.
No analysis was submitted and no storage was resized during this deployment.

The existing job and preflight endpoints accept `investment_plays` either in `portfolio_context` or as a top-level typed list for a new run. Each entry requires `title` and `thesis`; `catalyst`, `horizon` and `expression` are optional. Stable IDs are derived from the normalized hypothesis. Invalid input returns 422 before submission.

`reassess_portfolio_run_id` creates a linked new assessment from a saved snapshot and updated plays. If its checkpoint uses workflow 3, identical independent and current-assessment requests can reuse completed work at the saved research cutoff. Changed plays invalidate the affected reviews/comparison, not the ideal. Historical workflow 1/2 artifacts start a fresh independent workflow, not a silently upgraded recovery.

`resume_portfolio_run_id` retains the original inputs and version. It cannot be combined with reassessment or changed top-level plays. Original artifacts remain untouched.

Review requests with `user_adjustment: true` store personal alternatives distinctly from implementation reviews. Nothing in these endpoints executes a trade.

## Verification

- 301 passing portfolio/model-routing tests, including historical workflow 1/2 recovery, funding preflight, response recovery, source reuse and read projections.
- New independent-workflow tests cover input isolation, unchanged ideal/current outputs after editing plays, preservation of novel universes with 1/7/24 exposures, every-play handling, point versus range semantics and missing-mandate conviction.
- A mocked end-to-end run saves an ideal with a 15% novel exposure, proposes 20%, then reduces the final recommendation to 5% after the investment-case review. The saved ideal stays at 15%. These are test values, not financial advice or a live model result.
- A frozen 40-fact fixture retains all 40 observations while reviewing two cited facts in one batch, versus five batches for exhaustive eight-fact review. Repeating the check issues no new model request. No further summary/planning call is made for this selective check.
- A failed detail batch preserves successful batches and all original proposal rows. Missing implementation fields remain qualified rather than deleting a memo.
- Deterministic reference validation catches a claimed 0% allocation when the saved proposal contains 5%. This validates structured comparison figures, not the truth of every sentence of generated prose.
- Browser tests cover two distinct portfolio tables, thesis conviction, collapsed sources, separate user additions, absence of a misplaced plays editor and no mutations of the original memo. The Trading Terminal tests cover original-job play submission. Light/dark screenshots are checked at 390, 768 and 1440 pixels. Mobile tables scroll within their section rather than breaking header words.
- Legacy browser tests cover delayed lists, independent memo loading, lazy research, failed supporting-data retry, rapid switching and retained unsaved edits.
- Frontend production build, focused ESLint checks, Python compilation and whitespace checks pass. Existing bundle-size warnings remain; this is not a frontend bundling refactor.

Test commands:

```sh
.venv/bin/pytest -q --tb=short --show-capture=no tests/unit/test_portfolio* tests/integration/test_portfolio_positioning_memo.py tests/unit/test_model_routing.py
node tests/browser/portfolio-independent.mjs
node tests/browser/portfolio-reader.mjs
```

Browser tests need a local frontend and `PLAYWRIGHT_MODULE` when Playwright is supplied by the workspace runtime. All write/analysis requests in those tests are intercepted. Preview artifacts and screenshots are under `outputs/audits/portfolio-independent-uplift/`.

## Shared Model Settings

Portfolio Analysis now exposes four editable model groups in Model Routing:

| Group | Existing assignments controlled |
| --- | --- |
| Research | Macro/news retrieval and focused source research (Parallel) |
| Evidence Processing | Research planning, extraction and evidence summaries (OpenRouter) |
| Allocation & Review | Macro-first, portfolio-aware, exposure-equivalence and defensive-regime roles (OpenRouter) |
| Decision & Memo | Allocator judge, final allocation synthesis and commentary (OpenRouter) |

The group heading expands to show its stages. One edit validates and saves every
member atomically, with one audit entry. Reset restores each member's configured
assignment; it need not produce a single shared model. Existing differing models
remain unchanged and are shown as "Multiple models assigned" with the individual
values available in the expanded heading. Individual route APIs remain compatible.
This groups configuration only: it adds no analysis calls and does not merge roles.
Parallel Extract remains separate from the processor used for source research.

Verification: 73 focused backend tests, production frontend build, focused lint,
and isolated browser checks at 1440, 1024 and 390 pixels. The deployment pass also
passed all 761 unit tests and read-only live browser checks at 1440 and 390 pixels.

Deployed September 23, 2026 to `llm-council-analysis`, release **362**, image
`sha256:0fdb426dec111537272728b26471137862ec197e20d4f9bfddefa0480ed1f847`.
This release includes the pending portfolio recovery and lean research fixes.
All 165 backend/script source and dependency-manifest checksums match the local
build. Fly readiness passes; unauthenticated model-routing requests still return
401. The routing-store checksum is unchanged, as are the names, sizes and
modification times of all 29 saved memo files. No analysis was started, no models
were reassigned, and no storage was deleted or resized. Production `/data` has
about 145 MB free (95% used); storage headroom needs attention before a large run.
Deployment verification does not substitute for the outstanding paid financial
acceptance comparison. Screenshots: `outputs/audits/model-routing-groups/production/`.

## Parallel-Only Research (Pending Deployment)

The September 23 follow-up removes portfolio research's overlapping Perplexity
pass: one concurrent Parallel request per initial subject, then focused follow-ups
for material unanswered questions. The initial progress count is three, not six;
no replacement calls, new analysis stages or output limits are added. Exact
matching paid Perplexity evidence from historical checkpoints remains reusable
with its original provenance, but missing or failed requests are never sent.
Analyst Council's Perplexity lane is unchanged.

This is not part of release 362. The active portfolio job
`31905329-7376-41af-ad40-60c0bf8584d5` has not been interrupted, redeployed or
resubmitted. Verification: 218 focused retrieval/recovery/funding tests, followed
by all 705 portfolio/model-routing unit and portfolio integration tests, pass.
Focused correctness lint and whitespace checks pass. Automated coverage does not
establish improved research quality; that needs a memo audit.

## Release Gates

- [x] Offline implementation and automated functional/semantic checks.
- [x] Historical-reader and responsive light/dark presentation checks.
- [ ] User review of the preserved memo presentation and new idea/alternative controls.
- [x] Authorized live exercise using the saved production portfolio and role assignments. Separate initial views were verified, but funding-ledger and citation-integrity checks failed; completion is not release approval.
- [ ] Resolve findings in the live comparison and repeat the affected acceptance checks.
- [ ] Controlled comparison using fixed neutral evidence and identical resolved model settings, assessing actual analytical quality and anchoring tendencies. The live exercise used fresh research and floating model aliases; it does not prove better investment decisions.
- [ ] Explicit deployment approval and production verification.

The old April/August/September research is not retroactively certified as independently gathered. Its provenance limitations remain. The two saved views and structured numerical checks make divergence inspectable; qualitative reconciliation, instrument equivalence and whether an idea is already priced in still require assessment of real model output.
