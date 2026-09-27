# Portfolio Output Policy

## September 20: Remove The Application Ceiling

Portfolio requests no longer send `max_tokens`, `max_completion_tokens` or
`max_output_tokens`. There is no fixed 32k, 64k or 128k application ceiling.
`backend/portfolio_tokens.py` strips legacy output-limit settings at the stage
wrapper, runtime and funding-guard boundaries. All portfolio callers omit their
former fixed budgets, including extraction, source review, research planning,
allocation, specialist reviews, investment details, synthesis and commentary.

The native xAI helper also omits its output cap. Portfolio Perplexity instances
use zero, its existing setting for omitting the parameter; company council
configuration is unchanged. Parallel processor settings are unchanged.

Provider defaults, model output capacity and remaining context still apply.
This is not unlimited model output. OpenRouter documents that omitted
parameters are passed through without inserting a value, leaving the provider
to apply its defaults: [OpenRouter parameters](https://openrouter.ai/docs/api/reference/parameters).

## Retries And Receipts

A provider `length`/`max_tokens` finish reason remains a truncation, not a
JSON parsing error. Its raw response and usage remain saved. The existing
three-attempt policy remains, with lower reasoning effort and a concise complete
JSON request after truncation. Retries never restore or double an application
output cap. Historical receipts retain their actual request limits; new receipts
do not contain an output-limit parameter.

On explicit recovery, completed, non-truncated answers from capped checkpoints
can be reused after current validation. Matching still requires the exact model,
prompt, remaining request settings and a known code manifest. Changed research,
models or reasoning settings cannot qualify merely because the cap was removed.
Existing accepted outputs with documented limitations retain their normal
unchanged-request recovery behavior.

## Funding Is Separate From Generation

The September 21 fix removes full-model-capacity reservations and byte-as-token
costing. Per-request forecasts use the same model's measured billed input tokens
per message byte, and the median output usage for the same work type. If no
matching receipts exist, a text approximation and historical work-type output
estimate are used. A 25% cost margin is included. These are forecasts, not exact
token counts, provider-side reservations, or generation limits.

Low projected balance is recorded with the request, not used as a hard stop.
Confirmed account exhaustion, an unaffordable fixed request charge, unavailable
credit/pricing checks, or an actual provider 402 still stop required paid work.
Account and API-key spending allowances remain enforced. Optional funding
failures are saved as explicit review limitations, never as a completed review
or a reason to discard the memo. Such failures are not cached as successful work.

New-run preflight still estimates the full workflow before submission. Recovery
does not require funding the old approximate whole-workflow plan again: its plan
estimate is advisory, completed requests are revalidated and reused, and missing
requests receive fresh per-call credit checks.

When the revised memo and settled allocation are already saved, recovery resumes
at the final document review. It verifies the original portfolio context, reviewer
and writer models, and that the saved commentary was written against the exact
settled decision. Completed receipts remain attributed to their original calls;
only the pending review is dispatched. Normal and recovered documents use the
same publication and rendering function. An unavailable optional review leaves
an explicit provisional-review warning.

This terminal recovery path does not solve every earlier-phase replay issue.
The September 21 no-spend audit also found that partial per-source caches can
change extraction batches, and restored phase research can change earlier
planning inputs. Do not describe an arbitrary early-stage recovery as guaranteed
to reuse every prior model call. Those cases still require replay verification.

## Verification And Deployment

Tests cover actual OpenRouter HTTP payloads, wrapper/runtime/guard settings,
provider truncation retries, Perplexity and xAI requests, old capped checkpoint
compatibility, refusal to reuse changed inputs, and offline full memo workflows.
These tests make no paid provider requests.

The policy changes only newly started processes after deployment. It cannot
change an already submitted provider request. Do not restart a paid analysis
merely to apply this setting, and do not describe local changes as deployed.

## Historical Limits

The September 19 change raised portfolio starting budgets to at least 32,000
tokens and doubled them on truncation. That reduced, but did not eliminate,
artificial truncation. It is superseded by the September 20 policy above.
`LEGACY_MACRO_NEWS_MAX_TOKENS` remains solely as an old research-cache identity;
it is never used to budget a new provider request.
