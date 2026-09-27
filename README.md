# Alpha Edge Intelligence

Investment research and portfolio analysis with source-linked evidence,
multi-model review and configurable model routing.

## Applications

- **Analyst Council:** company research, independent analysis, peer review and
  a consolidated investment assessment.
- **Portfolio Analysis:** independent portfolio construction, assessment of
  current exposures and a final allocation informed by the investor mandate.
- **Announcement Router:** filing ingestion, thesis-impact assessment and an
  announcement review queue.
- **Model Routing:** provider and model assignments across the research and
  analysis workflows.

## Local Development

Requires Python 3.10 or later, Node.js 22 and uv.

```sh
uv sync --extra dev
npm --prefix frontend ci
cp .env.example .env
```

Configure the provider credentials required by the selected model routes in
`.env`. Set `API_TOKEN` for authenticated API access. For local development only,
`AUTH_DISABLED=true` can be used instead. Do not disable authentication on a
publicly accessible instance.

Start the backend and frontend in separate terminals:

```sh
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

```sh
npm --prefix frontend run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to port
8001. Model assignments are managed through Model Routing; environment settings
and runtime overrides are documented in [the routing guide](docs/model-routing.md).

## Architecture

| Area | Location |
| --- | --- |
| API and background jobs | `backend/routers/`, `backend/jobs/` |
| Council analysis | `backend/council/` |
| Research and document processing | `backend/research/`, `backend/document_pipeline/` |
| Portfolio workflows | `backend/portfolio_*.py` |
| Announcement assessment | `backend/scenario_router/` |
| Model assignments | `backend/model_routing.py` |
| Web application | `frontend/src/` |

Research outputs, checkpoints and credentials are runtime data and are not
included in this repository. Historical run results are not required to build
the application.

## Verification

```sh
npm --prefix frontend run build
uv run python -m compileall -q backend scripts portfolio_positioning_memo.py
uv run pytest tests/unit/ -q
```

Integration tests can contact paid providers and require credentials. Run them
only with the appropriate scope and budget. Known validation findings for the
initial snapshot are recorded in [release notes](RELEASE_SNAPSHOT.md).

## Deployment

`Dockerfile.analysis` builds the frontend and Python service. `fly.toml` describes
the existing Fly application, persistent storage and `/readyz` health check.
Before deploying a separate instance, change its application and volume settings
and configure provider credentials as secrets. GitHub CI does not deploy.

## Documentation

- [System architecture](docs/alpha-edge-intelligence-architecture.md)
- [Portfolio workflow and data contracts](docs/portfolio-analysis-remediation.md)
- [Research retrieval and recovery](docs/portfolio-source-retrieval.md)
- [Submission identity and recovery](docs/submission-recovery.md)
- [Model routing](docs/model-routing.md)

This repository is a public release snapshot of an existing project. See
[release notes](RELEASE_SNAPSHOT.md) and [attribution](ATTRIBUTION.md).
