# Portfolio Model Profile Deployment

Verified 18 September 2026, after the release-350 rollout and explicit application
of the persisted routing profile. This is not an image-only deployment claim.

- App: `llm-council-analysis`; production URL: https://llm-council-analysis.fly.dev
- Fly release: `350`; machine: `683d6eeb612638`; readiness check passing.
- Image: `sha256:71c1d5f243a4578e84557ae9d55ec07db9ac79a5a7eb84688b25949e9a27bedc`.
- Applied command: `python -m scripts.configure_portfolio_models --apply` via the
  script's `configure(apply=True)` function inside the deployed app environment.
- Persistent store: `/data/outputs/model_routing.json`.

| Work | Live assignment |
| --- | --- |
| Macro/news discovery | Parallel `ultra4x` |
| Citation extraction and focused follow-up | Parallel `ultra4x` |
| Evidence processing | `~deepseek/deepseek-flash-latest` |
| Independent ideal | `~deepseek/deepseek-flash-latest` |
| Current-portfolio assessment | `~deepseek/deepseek-flash-latest` |
| Exposure and investment-play review | `inclusionai/ling-3.0-flash-fin:free` |
| Defensive challenge | `anthropic/claude-opus-5` |
| Provisional reconciliation, details, synthesis and commentary | `~deepseek/deepseek-flash-latest` |
| Independent Perplexity research, unchanged | `openai/gpt-5.6-sol` |

Three persisted assignments changed: portfolio-aware Gemini to DeepSeek,
exposure-review Grok to Ling, and defensive-review DeepSeek to Opus.

Verification completed:

- Authenticated GET of the public `/api/model-routing` endpoint matched all ten
  entries in `PORTFOLIO_MODEL_PROFILE`.
- `_build_analysis_job_env("portfolio_positioning")` matched the same profile.
- Non-portfolio route rows were identical before and after configuration.
- Reapplying the profile would make no changes.
- 93 focused model-routing, profile, allocator, Ultra4x and workload tests passed.
- Remote frontend build and Fly smoke/readiness checks passed.

There were no active analysis jobs before deployment. No paid model request or
new portfolio analysis was launched to verify this release. Existing memos and
checkpoints remain unchanged. No Trading Terminal app was redeployed in this
operation; this updates the Intelligence backend's portfolio model assignments.
