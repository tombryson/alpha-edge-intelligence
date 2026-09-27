# Development Guidelines

## Structure

Alpha Edge Intelligence contains Analyst Council, Portfolio Analysis,
Announcement Router and Model Routing. The backend is FastAPI; the frontend is
React with Vite. Consult `README.md` and the relevant module before making changes.

- API routes: `backend/routers/`.
- Background jobs and persistence: `backend/jobs/`.
- Council analysis: `backend/council/`.
- Portfolio research and analysis: `backend/portfolio_*.py`.
- Announcement assessment: `backend/scenario_router/`.
- Model assignments: `backend/model_routing.py`.
- User interface: `frontend/src/`.

## Working Practices

- Preserve unrelated changes and existing runtime data.
- Use relative imports within the backend package.
- Keep provider credentials out of source, logs and commits.
- Do not start paid analyses or deploy without explicit authorisation.
- Check for active jobs before restarting or deploying the service.
- Preserve completed research and checkpoints when diagnosing failures.
- Verify request outcomes before retrying paid provider calls.
- Make narrow changes with focused tests. Do not redesign workflows or
  presentation as a side effect of maintenance.
- Match the current frontend theme and component conventions. Markdown content
  uses the shared `markdown-content` class.

## Local Verification

Use `uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001` for the backend
and `npm --prefix frontend run dev` for the frontend. Vite proxies `/api` to 8001.

Run relevant tests under `tests/unit/` and build the frontend after UI changes.
Integration tests may contact paid providers. Report test failures and limitations
accurately; the initial snapshot has known findings in `RELEASE_SNAPSHOT.md`.

Production configuration is in `fly.toml` and `Dockerfile.analysis`. Runtime
model assignments can override code defaults; inspect effective routing when
diagnosing model behaviour.
