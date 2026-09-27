# Portfolio memo loading

Saved memos are read-only documents. Opening a memo must not invoke research,
models, recovery, or the portfolio pipeline, and must not alter its presentation.

## Reader and research

- `GET /api/portfolio-positioning-runs/{id}?view=memo` returns the original memo
  Markdown and the fields used by the existing summary and allocation tables.
  Research packets, source excerpts, execution records and duplicate memo text
  are excluded from this response, not removed from the saved analysis.
- The reader sends a private, revalidated ETag based on the artifact's file
  version. Unchanged requests return 304 without reading the large artifact.
- `?view=research` loads the supporting data only when the reader's existing
  accordion is opened. Closing it preserves loaded data and unsaved review edits.
- The default full-data endpoint remains available to existing integrations.
  Full/research responses are not cached because review calculations can be
  time-sensitive. Gzip compresses responses; SSE remains unbuffered/uncompressed.
- Switching memos cancels the previous reader request and ignores late results.
  It does not refresh the sidebar. Refresh, deletion and opening a newly created
  run still update the sidebar.

## Persistent read models

`backend/portfolio_read_store.py` maintains `.portfolio-index-v1.json` and a
`.portfolio-views-v1/` directory beside the original artifacts. These are derived,
rebuildable caches, never the source of record. No original artifact is rewritten.

The index stores small summaries and remembers non-portfolio files too, so stock
analysis files are not repeatedly parsed to discover that they are not memos.
Each record is validated against source size, nanosecond modification time and
change time. Additions, edits, atomic replacements and deletions are reflected
without a 15-second expiry or a full reread. File listing/stat operations remain;
unchanged analysis JSON does not get reopened. Memo memory caching is limited to
64 compact views. Deletion also clears the associated cached view and index entry.

Startup warms the index before accepting traffic. The first migration reads legacy
artifacts once; subsequent starts reuse persisted metadata and compact memo views.
Cold indexing, artifact processing and memo JSON serialization run in worker
threads, not directly in async request handlers. Corrupt caches are rebuilt;
unwritable caches must not prevent access to original memos.

Increment `VERSION` when changing the persisted summary/reader projection so an
old derived view cannot survive a schema change. These caches describe the saved
artifact; current evidence/review checks remain in the full research/review path.

## Verification

The pre-fix production audit measured 68 files / 574,903,544 bytes scanned to list
22 memos. A cold list took 7.9-8.1 seconds and delayed both the memo and the auth
endpoint by about eight seconds. The April memo endpoint alone took 0.06 seconds.

Using the captured latest production memo, the reader response is 61,439 bytes
(14,343 bytes with gzip), down from 2,482,413 bytes. Memo text is unchanged.
These are payload comparisons, not a post-deployment latency measurement.

Regression coverage:
- `tests/unit/test_portfolio_read_store.py`: persistent reuse, changed-file
  invalidation, deletion, corrupt/unwritable cache recovery, compact/full API
  compatibility, ETags, cold-index concurrency, legacy documents and SSE.
- `tests/browser/portfolio-reader.mjs`: production-build browser checks for
  independent memo/sidebar loading, cancellation, lazy research, failure/retry,
  retained edits, unchanged layout, both themes and mobile/desktop widths.
- `tests/browser/portfolio-integrity.mjs`: existing historical memo and review flows.
