# Announcement Router Signal API

This is the minimal machine contract for Trading Terminal / Alpha Edge.

The announcement router remains the source of truth for thesis-evidence scoring. Trading Terminal should not ingest router event rows, replay the router, or reimplement thesis matching. It should request the current Router Score and use that as one input into its existing allocation and momentum logic.

## Endpoint

```text
GET /api/announcement-router/signals
GET /api/announcement-router/signals?ticker=ASX:VMM
```

Legacy alias:

```text
GET /api/scenario-router/signals
```

Singular aliases are also available:

```text
GET /api/announcement-router/signal?ticker=ASX:VMM
GET /api/scenario-router/signal?ticker=ASX:VMM
```

## Response

The response is deliberately just a ticker-to-score map:

```json
{
  "ASX:VMM": 3,
  "ASX:WWI": -1.5,
  "ASX:BRK": 0
}
```

When a specific ticker is requested and the router has no stored event for it, the endpoint returns zero:

```json
{
  "ASX:XYZ": 0
}
```

## Score Definition

The exported score is the latest counted Router Score for that ticker from the announcement router event store.

Internally this is `trajectory_score.current_balance.delta`, with a legacy fallback to `cumulative_delta`. It excludes the saved baseline and combines:

- Normalised primary catalyst evidence at 70% weight.
- Normalised secondary catalyst evidence at 30% weight.

The combined evidence scale is +/-5.5. Full catalyst states are aggregated before applying caps, so repeated announcements cannot refill a cap. See `scenario-router-trajectory-scoring-rubric.md` for the formula, expiry rules and baseline reconciliation.

That means:

- positive values indicate routed evidence has moved in a favourable direction
- negative values indicate routed evidence has moved in an unfavourable direction
- zero means no counted router movement is available

Primary Thesis Analysis means evidence matched to the saved thesis map, monitoring watchlist, or verification queue. Secondary Analysis means directional model assessment outside the saved thesis evidence set; it is lower quality and therefore contributes at reduced weight.

Raw secondary model assessments are not exported directly. They remain available in the full router events endpoint for audit inspection.

## Trading Terminal Usage

Trading Terminal should treat this score as a small conviction input, not as a standalone buy/sell decision.

Recommended first use:

```text
router_score = signals[ticker] or 0
```

Then use `router_score` only inside existing allocation, ranking, or breakout-sensitivity logic.

Do not use this endpoint for:

- filing titles
- run IDs
- confidence breakdowns
- source links
- event-level audit trails
- explanation UI

For those, call:

```text
GET /api/announcement-router/events?ticker=ASX:VMM
```

## Ownership Boundary

### Assessment Failures and Queue Classification

An announcement's assessment, score contribution, and review status are separate.
A valid positive assessment must not become "needs assessment" simply because its
score contribution is zero. An analyst-assigned neutral verdict takes precedence
over a retained thesis-map relationship when filtering the queue.

The thesis judge uses `SCENARIO_ROUTER_THESIS_JUDGE_MAX_OUTPUT_TOKENS` (default
6,000). If the provider reports `finish_reason=length` or `max_tokens`, the router
retries the original request once with twice the output budget, at least 6,000
tokens. It does not treat an incomplete JSON fragment as a finished assessment.
The previous 1,800-token default truncated substantive filings while allowing
short administrative notices to succeed.

New event artifacts retain `announcement_facts.model_judgement.response_attempts`
with the model, output budget, finish reason, usage, and provider error metadata.
Truncation, malformed responses, and provider errors are reported as technical
assessment failures, not as an uncertain investment conclusion.

The AI reassessment endpoint reuses the saved filing, baseline, publication date,
and prior catalyst context. A failed reassessment returns HTTP 502 without
overwriting the saved event or the analyst's review. Deploying a fix does not
rerun failed historical assessments; those require a separate reassessment.

### Responsibilities

LLM Council owns:

- announcement parsing
- thesis/watchlist/verification matching
- router trajectory scoring
- persisted router event artifacts
- this compact signal endpoint

Trading Terminal owns:

- portfolio allocation logic
- momentum gates
- breakout rules
- watchlist and position UX
- any decision to use, cap, ignore, or display the router score
