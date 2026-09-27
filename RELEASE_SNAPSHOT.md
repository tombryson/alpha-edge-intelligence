# Initial Public Release Snapshot

Prepared on 27 September 2026 from the existing Alpha Edge Intelligence codebase.
This date records preparation and publication, not original development dates.

## Scope

- Includes the current source and uncommitted source improvements from the
  original checkout, whose HEAD was `f9d7697932cc95b15b968e4b78bc10b2d8fde2cd`.
- Starts a new Git history with one accurately dated `Initial public release`
  commit. The original repository, branches, tags and local history are preserved
  separately; they have not been rewritten or deleted.
- Omits runtime outputs, local data, secret environment files, dependency caches
  and obsolete `.bak` source copies. Environment examples and tests are retained.
- Preserves attribution and existing notices. See [ATTRIBUTION.md](ATTRIBUTION.md).

## Deployment

The supplied `fly.toml` targets the existing `llm-council-analysis` application.
Do not deploy it into another account without changing that application name and
configuring its secrets and persistent volume.

Publication does not redeploy the application, modify its secrets or change its
production data. Deployment currently uses the Fly CLI and local build context.
The GitHub workflow runs checks; it does not deploy. No deployment credentials
are included in this snapshot or copied into the new GitHub repository.

The default branch remains `master` so the existing CI branch filters apply.
Future development can use this checkout; the original checkout and its remotes
remain unchanged.

## Verification And Known Issues

- Frontend dependency installation and production build passed. The generated
  asset filenames match the current production build.
- Python compilation of backend, scripts and entry point passed.
- Fly configuration validation passed. No deployment was performed for this
  repository publication.
- A Gitleaks scan of the copied source found no credentials. Its one finding was
  a reviewed false positive on a model-routing dictionary in
  `tests/unit/test_portfolio_allocator_roles.py`.
- The broad lint command reports 439 existing findings. The unit-suite run
  completed 253 passing tests, two skips and two failures before being interrupted
  during a stalled asynchronous test. The failures are the first two cases in
  `tests/unit/test_portfolio_case_remediation.py`, which expect one review batch
  where the implementation returns two. The full suite is not certified passing.

These are findings on the preserved application source, not a claim of a clean
CI baseline. The original CI checks are retained without suppressing failures.
