# Council Submission Recovery

Implemented on `codex/final-migration-hardening`. Deployment is a separate step.
Deploy this contract before the matching Terminal frontend.

## Contract

All routes retain existing `/api/` authentication. No paid calls are made by lookup.

`POST /api/analysis-jobs` accepts its existing JSON or multipart request plus an
optional `Idempotency-Key` UUID header. New Terminal submissions always send it.
Clients without this header remain compatible but have no duplicate protection.

| Condition | Response | Launches work? |
| --- | --- | --- |
| New valid request and key | 202, existing public job fields plus `submission_id` | Once, after durable reservation and job metadata |
| Same key and same normalized request/upload bytes | 202, original public job | No |
| Same key with changed request or attachment | 409, `detail` string | No |
| Invalid UUID | 400, `detail` string | No |
| Funding preflight rejected/unavailable | 402/503, `detail` with `message`, `funding`, `code: COUNCIL_PREFLIGHT_REJECTED`, `submission_status: not_submitted` | No reservation or job |
| Reserved key whose job was not published | 202, `code: COUNCIL_SUBMISSION_UNCERTAIN`, `submission_status: uncertain`, `submission_id`, `detail`; no `job_id` | No |

`GET /api/analysis-submissions/{uuid}` returns 200 with the original public job,
including its status and `job_id`. It returns the uncertain body above for a
reservation without job metadata, 404 for an unknown reservation, and 400 for an
invalid UUID. A 404 is not proof the original POST has stopped processing.

The public job ID/status contract is unchanged. Lookup can recover a job even
when the POST response was lost or the service restarted. Startup marks
interrupted jobs failed; it does not silently rerun paid work.

## Durability And Boundaries

- `JOBS_META_DIR/submissions.sqlite` stores the UUID, request fingerprint and job
  ID. SQLite's transaction reserves identity atomically before job creation.
- Job JSON is fsynced before rename, then the metadata directory is fsynced,
  before publication in memory. Include both metadata files and the registry in
  service-volume backups; neither is disposable cache.
- The fingerprint covers normalized request fields and uploaded filename/bytes.
  Reusing an ID is not a way to amend a submitted request.
- A crash between reservation and publication requires operator review. Do not
  delete the reservation or invent a fresh key as an automatic retry.
- This is a single durable-volume service, not a distributed queue or a
  per-user multi-tenant authorization layer. Separate machines with independent
  volumes cannot provide a shared idempotency guarantee.
- Existing job result/artifact retention still applies. Identity does not
  recreate a deleted result, refund a provider charge or guarantee job success.

## Terminal Behaviour

Terminal records the UUID before transmitting. A lost response triggers a bounded
GET lookup, never a POST retry. An unresolved identity survives page reload;
attempting the same security/job type recovers it first instead of starting
another paid run. Logout clears private browser state. Portfolio analysis also
retains its submission identity in saved job state.

Funding and validation rejection messages are surfaced from structured `detail`
instead of being replaced with a generic failure. This does not bypass funding
checks or retry an uncertain job.

## Verification

`tests/unit/test_submission_identity.py` exercises simultaneous reservation,
same-key replay, conflicting payloads, recovery after restart, reservation-only
crashes and uploaded-byte fingerprints without contacting providers.

The unit suite redirects runtime outputs to temporary directories and blocks
external HTTP. Queue lifecycle tests cover reopening on a new event loop without
losing durable announcement work. Terminal's proxy tests cover lost replies,
structured rejection details, reload recovery and the no-POST-retry boundary.
