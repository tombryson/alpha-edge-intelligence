# Model Routing

The OpenRouter Stage 1 lane and Local Stage 1 / Stage 2 pool share one model list.
Both UI assignments remain visible to show where models run. Editing or resetting
either assignment updates both stored settings:

- `PERPLEXITY_STAGE1_OPENROUTER_MODELS`
- `COUNCIL_MODELS`

Existing divergent overrides resolve to the most recently edited key recorded in
the routing audit. Without an audit entry, the Stage 1 override takes precedence.
Without overrides, the explicit Stage 1 environment list takes precedence over
the council environment list, then the shared code default. Runtime lookups, UI
values, and subprocess environments use the same resolution.

Stage 1 records the shared list as `openrouter_council_models` in run metadata.
Stage 2 uses that snapshot; successful Stage 1 responses determine the evidence
to rank, not membership of the judge pool. Chairman selection remains a separate
assignment. Provider failures can still reduce the responses actually returned.

Identifiers may include a provider variant suffix, such as
`inclusionai/ling-3.0-flash-fin:free`. Saving validates identifier syntax, not
provider availability or entitlement. Save errors remain visible and preserve
the draft for correction.

## Portfolio Allocator Roles

The allocator council uses named assignments, not list positions. Model Routing
shows all four roles under Portfolio Analysis, each with its own Edit control.
Every role runs; none can be switched off. In workflow 3 the independent ideal is
saved before the separately formed current-portfolio assessment. Neither initial
view sees the user's investment plays, and the current assessment does not see
the ideal. The exposure and defensive reviewers then receive both views and the
plays. The judge forms a provisional recommendation, targeted research addresses
material unanswered questions, investment cases are tested, and synthesis resolves
the final proposal before commentary. There is no additional fast/deep mode.
Historical checkpoint recovery retains its recorded workflow.

### Approved Portfolio Roster (18 September 2026)

| Work | Model |
| --- | --- |
| Macro/news retrieval and initial source discovery | Parallel `ultra4x`, one shared task per lane |
| Citation extraction and focused follow-up | Parallel `ultra4x` |
| Evidence processing and summary | `~deepseek/deepseek-flash-latest` |
| Independent ideal and current-aware assessment | DeepSeek, in separate requests |
| Exposure-equivalence review and play assessment | `inclusionai/ling-3.0-flash-fin:free` |
| Defensive/adversarial review | `anthropic/claude-opus-5` |
| Provisional reconciliation, investment details, final synthesis and commentary | DeepSeek |

Opus and Ling each have one analytical role, not another full allocation council.
Provider retries can still create more than one request for a role. Ling replaces
the existing exposure-equivalence assignment; it does not add calls, switches or
a new mode. The DeepSeek alias currently used in the comparison
resolved to V4.1 Flash; an alias may resolve differently later, so preserve the
requested and resolved IDs in run provenance.

The roster is an explicit, audited configuration, not a silent rewrite of saved
operator settings. Preview or apply it in the application's environment:

```sh
python -m scripts.configure_portfolio_models
python -m scripts.configure_portfolio_models --apply
```

The script uses `MODEL_ROUTING_STORE` or the normal outputs directory, applies only
changed Portfolio Analysis assignments, and leaves council/router settings alone.
Reapplying it is idempotent. Named settings in `.env.example` show the same roster
for standalone CLI use. App jobs export saved routing into the analysis subprocess.
Existing saved memos are not regenerated, and an already-running subprocess keeps
its captured model configuration.

**A Fly image deployment alone does not replace production's persisted routing
overrides.** A roster deployment is complete only after applying the command inside
the app environment and verifying both the live Model Routing API and the exported
portfolio job environment against every assignment in the profile. Clearing an
individual override still restores its
previous configured/migrated assignment, as described below.

| Role | Route ID | Responsibility |
| --- | --- | --- |
| Macro-first allocator | `portfolio.allocator-macro-prior` | Macro-led allocation without anchoring to existing weights |
| Portfolio-aware allocator | `portfolio.allocator-portfolio-aware` | Allocation informed by current holdings |
| Exposure-equivalence reviewer | `portfolio.allocator-exposure-equivalence` | Related and substitute exposures |
| Defensive-regime reviewer | `portfolio.allocator-defensive-review` | Adverse regimes and a bounded final check of financial claims/corrections |

Saving a role uses `PUT /api/model-routing/{route_id}` with, for example:

```json
{"value":{"model":"provider/model"}}
```

Every role requires a nonempty, syntactically valid model identifier.
The same model can serve multiple roles; each receives its distinct role prompt.
Editing or resetting a role never changes another role's assignment.
Provider availability is not checked by this syntax validation.

On first access, the routing store migrates
`PORTFOLIO_POSITIONING_DEEP_ALLOCATOR_COUNCIL_MODELS`: a saved override takes
precedence over the environment, then the old code default. It preserves the old
runner's de-duplication and maps up to four models in their existing order to the
roles above. Missing positions, including defensive review in a three-model pool,
are assigned the effective portfolio allocator judge model at migration time.
This is a saved initial assignment, not a continuing fallback or link to the judge.
More than four models requires explicit review instead of silently discarding them.
The migration is recorded in the audit and persisted as
`portfolio_allocator_defaults` (store version 3). It runs once, so subsequent
legacy-list changes cannot shift role assignments. Reset restores this initial
assignment, unless an explicit named environment assignment has been configured.
The old `portfolio.deep-allocator` write endpoint now returns 422.

Settings from the optional-role preview are migrated by retaining each assigned
model and assigning the judge model to previously disabled, unassigned roles.
The old `enabled` property is removed. New writes with that property return 422
so an outdated client cannot claim to switch a role off.

Runtime role overrides take precedence over named environment assignments, then
the migration snapshot. The four `PORTFOLIO_POSITIONING_ALLOCATOR_*` keys in
`.env.example` accept JSON objects. When using named environment configuration,
supply all four: missing roles are errors, not positional fallbacks. Standalone
CLI runs without named settings retain the legacy seed for compatibility; app
jobs always export the validated named assignments to their subprocess.

Portfolio job submission and subprocess startup both validate the role settings
before research begins. Invalid settings appear in Model Routing and reject a new
portfolio job with 422; they do not block company-analysis jobs. New artifacts
record all four required roles in `allocator_role_assignments`.
Allocator outputs and prompt audits identify their stable role in `council_lane`
and `lane_strategy`, including failed calls. Existing saved memos are unchanged.

Portfolio macro/news and initial source discovery share one task using
`portfolio.macro-news` (`PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR`). Missing
citation text and material follow-ups use `portfolio.source-retrieval`. Both use
the Parallel Task API processor `ultra4x` by default and require `PARALLEL_API_KEY`.
The fields accept a Parallel processor name, not an OpenRouter model identifier.
The retired Grok macro/news setting is retained only for historical recovery.
Use `python -m scripts.configure_portfolio_models --retrieval-only --apply` to
update retrieval without changing saved analysis assignments. See
[portfolio source retrieval](portfolio-source-retrieval.md) for question budgets,
source provenance, failure handling and checkpoint recovery.
