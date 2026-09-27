# Scenario Router Trajectory Scoring Rubric

The announcement router assesses filings and maintains catalyst evidence states against a saved council baseline. Version 2 calculates the balance from those states, rather than summing announcement scores.

## Evidence Balance (Version 2)

```text
primary = clamp(sum(primary catalyst states) / 4, -1, 1)
secondary = clamp(sum(secondary eligible catalyst states) / 1.5, -1, 1)
evidence_delta = 5.5 * (0.70 * primary + 0.30 * secondary)
current_balance = clamp(baseline + evidence_delta, -8, 8)
```

Secondary eligible states use the existing half-weight raw assessment described below. The normalisation denominators define full-scale evidence in each track; the fixed weights then allocate 70% and 30% of the 5.5-point evidence scale. These percentages are weights, not a guarantee about the ratio of two realised contributions when one track is empty or they oppose each other.

Store full catalyst states before applying caps. A repeated filing cannot refill a cap after opposing evidence arrives. Independent catalyst order does not affect the final balance. A model-confirmed progression or reversal replaces the catalyst state.

The existing thesis judge receives up to 80 recent distinct catalyst summaries from up to 5,000 company events, including prior runs. It returns `evidence_update` with a stable asset/catalyst ID, change classification, source quote, reason, and durability. Unknown repeat IDs are not accepted as grounds for suppression. There is no extra model call.

Each saved run remains a separate baseline. `baseline_included` requires a quote found in the saved thesis packet and contributes zero. A repeat from an earlier run can carry its state once into the new run when the judge does not find it in the baseline; it retains its original evidence date. This is filing-driven reconciliation, not an automatic re-evaluation of every catalyst when a council run completes.

Publication date controls the 180-day window, followed by receipt date and storage date when unavailable. Explicitly durable model-assessed facts survive that window until superseded or incorporated into a baseline. Legacy records without this assessment retain their existing expiry behaviour and deterministic grouping; their durability and catalyst identity are not inferred retrospectively.

The ledger is a read projection of stored assessments. It does not cancel upstream review decisions: a zero contribution can still require review. `current_balance` on each score contains the final primary, secondary, delta, total, and label for its run, independent of which event is displayed. Contributions describe changes within the current window, not immutable historical balances.

## Naming Contract

Use these names consistently:

| Name | Meaning |
| --- | --- |
| Validated Thesis Evidence | Evidence matched to the saved thesis map, monitoring watchlist, or verification queue; 70% track weight. |
| Unmapped Material Evidence | Directional assessment outside the saved thesis evidence set; 30% track weight. |
| Raw secondary assessment | The model's unweighted directional assessment of an outside-map filing. This is audit context, not the displayed contribution. |
| Thesis Evidence Balance | Baseline plus weighted catalyst evidence. The compact signal API exports only the evidence delta, excluding baseline. |
| Thesis Path | The visible Bull/Base/Bear band implied by the Router Score plus the saved run baseline. |

Avoid these phrases in UI and handoff docs:

- "company path" or "ticker path" because they blur score state, thesis path, and export signal.
- "cumulative" because it is an implementation detail, not user-facing language.
- "signal +2" when the displayed value is meant to be a counted contribution.

## Output Fields

Each routed filing may carry a `trajectory_score` object:

- `direction`: `positive`, `negative`, `neutral`, or `mixed`.
- `intensity`: `none`, `low`, `medium`, `high`, or `critical`.
- `event_delta`: the marginal change to the weighted evidence balance in the read projection; the stored comparator assessment precedes ledger processing.
- `raw_event_delta`: the original eligible assessment, retained across projection.
- `primary_event_delta`: the marginal primary contribution.
- `secondary_event_delta`: the marginal secondary contribution.
- `raw_secondary_delta`: the unweighted model assessment for Secondary Analysis.
- `unvalidated_event_delta`: legacy name for the unweighted secondary assessment.
- `cumulative_delta`: the running score movement for the ticker and saved run.
- `cumulative_primary_delta`: the running Primary Thesis Analysis contribution.
- `cumulative_secondary_delta`: the running Secondary Analysis contribution.
- `baseline_score`: the starting score implied by the saved thesis path.
- `score_after_event`: compatibility alias for baseline plus the running weighted balance after this filing.
- `score_after_cumulative`: baseline plus all routed filings for the saved run.
- `position_band`: the event-level band after this filing.
- `cumulative_position_band`: the rolling band after all filings.
- `position_label`: human label for the current path.
- `validation_type`: why this score received its weight.
- `validation_weight`: the score floor created by the validation type.
- `mapped_condition`: whether the filing engaged a saved thesis, watchlist, or verification condition.
- `confidence`: max of parser confidence and thesis-match confidence where a condition was engaged.

## Baseline Path

The saved council run starts on a simple score axis:

| Saved path | Score |
| --- | ---: |
| Bear | -4.0 |
| Base | 0.0 |
| Bull | 4.0 |
| Mixed / unknown | 0.0 |

## Position Bands

| Score | Band |
| ---: | --- |
| `<= -4` | Bear |
| `> -4` and `<= -2` | Bear-leaning |
| `> -2` and `< 2` | Base |
| `>= 2` and `< 4` | Bull-leaning |
| `>= 4` | Bull |

This is deliberately not a hard flip from base to bull or bear on one ordinary filing. The router can say a filing is bull-leaning without claiming the saved bull case is proven.

## Base Intensity Scale

If a filing has no stronger validation source, event magnitude comes from intensity:

| Intensity | Magnitude |
| --- | ---: |
| None | 0.0 |
| Low | 0.5 |
| Medium | 2.0 |
| High | 3.0 |
| Critical | 3.0 |

The sign is set by `direction`. Positive filings add the magnitude. Negative filings subtract it. Neutral and mixed filings score `0.0`.

## Validation Weighting

Some evidence is more important because it validates something the saved council run explicitly told us to monitor. The router therefore applies a validation weight floor. The final event magnitude is:

```text
max(base intensity magnitude, validation weight)
```

Positive validation:

| Validation type | Meaning | Weight |
| --- | --- | ---: |
| `saved_thesis_condition` | Announcement fully satisfies a saved bull/base/bear required condition. | +3.0 |
| `watchlist_confirmatory_full` | Announcement fully satisfies a confirmatory watchlist item. | +2.5 |
| `watchlist_confirmatory_partial` | Announcement is a real precursor or partial match to a confirmatory watchlist item. | +2.0 |
| `verification_queue` | Announcement resolves or supplies a verification-queue item. | +1.5 |

Negative validation:

| Validation type | Meaning | Weight |
| --- | --- | ---: |
| `saved_thesis_failure` | Announcement fully satisfies a saved failure condition. | -4.0 |
| `watchlist_red_flag_full` | Announcement fully satisfies a red-flag watchlist item. | -3.0 |
| `watchlist_red_flag_partial` | Announcement is a real precursor or partial match to a red-flag item. | -2.0 |

Secondary Analysis:

| Validation type | Meaning | Weight |
| --- | --- | ---: |
| `related_unmapped` | Filing appears related and directional, but no saved thesis, watchlist, or verification condition covers it. | 50% of raw assessment, capped at +/-1.5 |
| `material_unmapped` | Legacy equivalent for related unmapped filings. | 50% of raw assessment, capped at +/-1.5 |

Secondary Analysis is deliberately lower quality than Primary Thesis Analysis because it is a model judgement outside the saved evidence map. It now receives a reduced counted contribution instead of being displayed as a score while contributing nothing. The raw model assessment is retained as `raw_secondary_delta` / `unvalidated_event_delta` for audit context.

## Guardrails

- Saved thesis conditions outrank generic materiality.
- Confirmatory watchlist hits outrank unmapped positive filings.
- Partial watchlist hits are scored, but below full watchlist hits.
- Saved failure conditions are the strongest negative signal.
- Red flags are stronger than generic negative filings.
- Verification-queue hits support evidence refresh, but should not be treated as strongly as a thesis condition or watchlist catalyst.
- Fatalities, serious safety incidents, formal investigations, and safety-related shutdowns are risk events even when the company says no immediate production impact is expected. A non-triggered production-delay watchlist item can be shown as checked, but it must not neutralize the risk verdict.
- A saved or replayed model judgement must be normalized through the same contract as a fresh model response. Stored artifacts are not allowed to bypass safety and scoring invariants.
- Do not label a filing as "Bull case" solely because it is positive and material. Use "Bull-leaning" unless the Router Score reaches the bull band or the saved bull condition is actually satisfied.
- Review state must not erase case type. A reviewed unmapped material filing remains an unmapped material filing in history.

## Eligible Assessment Examples (Before Ledger Aggregation)

| Filing | Saved condition context | Expected score |
| --- | --- | --- |
| Power infrastructure contract; no saved condition covers it | Secondary Analysis | raw secondary `+2.0`, counted `event_delta=+1.0` |
| Binding offtake agreement where watchlist asks for binding offtake | Full confirmatory watchlist hit | `+2.5` |
| Non-binding offtake LoI where watchlist asks for binding offtake | Partial confirmatory watchlist hit | `+2.0` |
| Announcement satisfies a saved bull required condition | Saved thesis condition | `+3.0` |
| Permit revocation satisfies a saved bull failure condition | Saved thesis failure | `-4.0` |
| Fatal safety incident with no expected production delay | Secondary Analysis risk event; production-delay red flag checked but not triggered | raw secondary `-2.0`, counted `event_delta=-1.0` |

## Implementation

The rubric is implemented in `backend/scenario_router/trajectory_scoring.py`.

`backend/scenario_router/thesis_comparator.py` supplies the scorer with:

- required thesis hits
- failure thesis hits
- full red-flag hits
- partial red-flag hits
- full confirmatory watchlist hits
- partial confirmatory watchlist hits
- verification-queue hits

Regression coverage is in `tests/scenario_router/test_scenario_router_trajectory.py`, `test_evidence_ledger.py`, and `test_catalyst_judge_context.py`.

## External Signal API

Trading Terminal should consume the compact router signal API rather than the full event rows:

```text
GET /api/announcement-router/signals
```

The contract is documented in `docs/announcement-router-signal-api.md`.
