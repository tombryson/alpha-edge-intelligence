# September 23 Finish-Only Recovery

## Scope

The user authorised completion of the saved memo after topping up, without reopening source checks or switching the run to the new research architecture. This is an assessment copy, not a certification that every cited claim has been verified.

Source job: `bc9b81a2-6518-47cc-8ea5-6d05d3b11716` (failed, terminal).
Source artifact: `portfolio_positioning_job_portfolio_recovery_20260923_070012.json`.
Destination: `portfolio_positioning_job_portfolio_finish_only_20260923_091506.json`.

## Recovery Contract

- Preserve the original artifact and checkpoint. Require identical portfolio context, mandate and plays, sealed independent/current baseline portfolios, completed reviews and a saved provisional recommendation.
- Reuse the original research, query, cutoff, citations, proposals and reviews. No discovery, extraction, new play research or new source-check requests.
- Preserve actual source-check verdicts, including adverse findings. Explicitly leave unfinished checks unverified; a closed stage is not a successful verification.
- Reuse an investment case only when its decision and evidence hashes still match. Six saved cases qualify; the remaining material cases require completion or reassessment.
- Run only investment cases, final allocation, any cases changed by that allocation, and memo commentary. No subsequent model consistency/reconsideration loop. Retain deterministic funding, allocation and comparison checks.
- Keep both successful provenance and previous failures. Historical failures are archived under the recovery record rather than presented as newly failed requests.
- Append the source-check qualification and absence of an additional model review to the memo. Keep the normal reader and existing memo layout.

## Isolation

The one-off runner uses the exact deployed release-362 pipeline with only the finish-only changes overlaid. It loads existing production backend dependencies and a new additive completion helper from a separate operation directory. It does not overwrite application files, deploy unrelated local changes, restart the web server or change model routing.

The final model remains `anthropic/claude-opus-5.5`. The operator runner rejects any new model request outside the four permitted completion stages and checks the model assignment before starting. An exclusive operation manifest prevents blind duplicate submission after an uncertain SSH response.

Operation directory: `/data/operations/portfolio-finish-only-20260923-091506/`.
Operational files: `operation.json`, `preflight.json`, `worker.log`.
Local code and deployed source snapshot: `outputs/audits/portfolio-finish-only-20260923/`.

This detached operator recovery is not a new entry in the web server's in-memory analysis-job registry. Progress is read from its manifest, checkpoint and provider receipts. The final artifact uses the normal portfolio memo reader.

## Verification

Before the final early-return adjustment: 801 unit tests passed. After that adjustment: 19 focused recovery/cache tests passed. Nine completion tests also passed after the final qualification change. Focused correctness lint passed.

Tests cover rejecting changed mandates or incomplete baselines, preserving unsupported source verdicts, leaving unchecked claims unverified, exact case-reuse requirements, unchanged original checkpoint bytes, unchanged baseline/review hashes, no upstream or consistency model requests, substantive commentary and allocation arithmetic.

Credit check at 09:15 UTC: approximately US$11.20 available. This is a balance reading, not a guaranteed total cost. Provider credit protection remains active.

Production preflight passed, including hash verification of every transferred code file. The completion worker started at 09:25:22 UTC (19:25:22 Melbourne), PID 803 on machine `683d6eeb612638`. It retains 296 completed cache entries. The isolated deployed-code overlay also passed all nine completion tests.

The first worker was OOM-killed at 09:26:17 UTC, before any provider request. The saved artifact reports zero new model/research requests, no new receipts and no active request phases. The original remains intact. Do not interpret its stale `running` manifest as a live worker.

The recovery loader now references archived raw research and the original completed-request cache instead of copying them into multiple live snapshots. Source facts, sealed portfolios, reviews and current investment cases remain materialized. Cache/record-memo copies that cannot be requested in finish-only mode are released; their full checkpoint remains unchanged and explicitly referenced. This avoids turning preservation into repeated hydration of hundreds of past responses. An unpaid real-checkpoint probe stops before provider dispatch; twenty focused tests pass after this memory remedy.

The real-checkpoint unpaid probe passed after this change, reaching two intended investment-case dispatches and stopping before either provider call. Peak resident memory was 1,203,776 KiB. Twenty focused tests and ten isolated-deployed-overlay tests pass. The completed independent-workflow/recovery regression set also passed 54 tests before the memory-only adjustment.

The worker restarted at 09:41:47 UTC (19:41:47 Melbourne), PID 839. The first failed attempt and its zero-paid-request proof are archived under `attempt-1-no-paid-calls`; the original source hash is unchanged. The monitor `finish-saved-portfolio-memo` checks this specific operator worker, silently unless completion/failure requires attention. Current checkpoint counts describe newly completed work; 296 archived completions remain in reused receipts and the referenced original checkpoint.

At 09:46 UTC the recovery stopped on an actual OpenRouter HTTP 402 for `final_allocation`: maximum request cost exceeds available credits (`weight_exceeds_budget`). All three missing investment-case batches completed, with no retries, at a reported total of US$6.51514. Available balance is US$4.68804. No new research or source-check requests were made.

The remaining final-allocation prompt is still large under the preserved architecture: 2,551,752 serialized prompt bytes, including 2,140,358 bytes of evidence. Its evidence selector includes 1,696 of 1,776 facts. This is an outstanding payload-efficiency issue, not evidence that those sources were newly researched. No input/output truncation or model swap was introduced to force the request through.

The user was asked for a US$15 credit buffer, explicitly not a guaranteed cost. The monitor was deleted after this actionable failure. Resume from the **new finish-only checkpoint**, not the original 07:00 source: the three newly completed case batches must not be repeated. Original research, sealed baselines and the original checkpoint remain preserved.

Hash verification confirms the portfolio context/snapshot, both baseline portfolios, six plays, analytical reviews, provisional recommendation, all facts and the source packet are unchanged. The recovery now has 16 investment-case rows. It retains 478 existing fact-check verdicts; 80 selected facts remain explicitly unverified.

Status: awaiting credit at final allocation; no completed final memo yet. Final-output verification remains outstanding. The durable operation manifest and `outputs/audits/portfolio-finish-only-20260923/operation.json` identify this recovery; do not start a duplicate or repeat an uncertain paid request.

## Top-Up Resume, 09:58 UTC

The user confirmed another top-up. Fresh production balance was US$14.68804. The previous worker was confirmed stopped with an explicit provider 402, so there was no uncertain accepted final-allocation request to repeat.

The resume reuses `portfolio_positioning_job_portfolio_finish_only_20260923_091506.checkpoint.json`, including all three newly completed investment-case batches. A reuse bug was found before submission: cases adding citations in their answers were checked against the bare proposal rather than the combined proposal and saved case. The original evidence hash was created from the combined case. Matching that existing convention retains all 16 cases while still invalidating them if a cited fact or allocation changes. A regression covers answer-added citations and changed source evidence. Twenty-two focused recovery/cache tests and correctness lint pass.

Chained recovery also preserves original research archive pointers and counts archived completed receipts, rather than reporting only the three entries in the latest cache. Production preflight verified 299 preserved completed entries, all 16 cases, six plays, high risk tolerance and a 5+ year horizon. The deployed pipeline overlay hash is unchanged. Only the additive recovery helper and isolated operator runner changed; no deployment or model change occurred.

New operation: `/data/operations/portfolio-finish-only-20260923-095700/operation.json`.
New output: `portfolio_positioning_job_portfolio_finish_only_20260923_095700.json`.
Worker: PID 866, started 2026-09-23 09:58:22 UTC (19:58:22 Melbourne).

The operator now rejects any provisional `investment_cases` paid request. Only final allocation, cases genuinely changed by the final decision, and commentary are permitted. All prior archives remain intact. Status at launch: running, final output not yet verified.

## Provider Context Failure And Lossless Packet Repair

The 09:58 worker made two rejected requests, not successful generations. Final allocation received HTTP 400: `prompt is too long: 1067183 tokens > 1000000 maximum`; commentary received the same rejection at 1,017,828 tokens. Credit remained US$14.68804. The finish-only fallback incorrectly marked its materialized provisional memo complete despite both provider failures. Operator verification caught this; the output was relabelled incomplete, retaining its text, and the operation manifest records failure. No completed final memo is claimed.

The rejected final packet contained the same unchecked-source verdict 1,220 times. A narrow, lossless input encoder now stores identical source-review objects once beside the existing observation table and references them from their rows. It also emits compact JSON. It does not shorten a quotation, drop a fact, alter a verdict, reduce output limits, change a model or change the research workflow.

An unpaid probe used the exact two rejected request records. Expanding the references reconstructs the original parsed payload exactly:

| Request | Observations retained | Original bytes | Encoded bytes |
| --- | ---: | ---: | ---: |
| Final allocation | 1,696 | 2,551,752 | 2,179,579 |
| Commentary | 1,697 | 2,423,724 | 2,055,812 |

The completion path now requires a usable provider response for final allocation and commentary before claiming final generation complete. Missing minor fields remain recoverable; a rejected request is not a successful generation. Regression tests preserve saved output on these failures. Twenty-five focused tests, fifteen tests against the isolated deployed overlay, and correctness lint pass.

Next isolated operation: `/data/operations/portfolio-finish-only-20260923-100700/`.
Output: `portfolio_positioning_job_portfolio_finish_only_20260923_100700.json`.
It resumes the same 09:15 finish-only checkpoint because neither 09:58 request generated any output. All 16 cases remain reusable. The fresh launcher was submitted once; its exclusive claim and manifest guard against duplicate dispatch. Live completion verification remains outstanding.

Preflight passed again with US$14.68804, all 16 cases and 299 archived completions. Worker PID 902 started at 10:09:52 UTC. Final allocation was dispatched at 10:11:01 UTC. The runtime reserializes JSON with standard spacing, so actual dispatched input is 2,271,033 characters, rather than the minimum-byte representation in the table above. The lossless shared-verdict reduction remains active; the compact-byte benchmark must not be presented as the actual transport byte count. No input facts or output-token allowance were removed.

Final allocation succeeded on its first attempt: request `gen-1790158262-QbkpjnSiCMWY4oNGaIax`, 967,197 input tokens, 25,803 completion tokens, reported US$4.384848. Its 16 targets sum to 100% within floating-point precision. It proceeded to two changed-case batches; these initially received explicit transient provider `in_flight_budget_exhausted` responses with Retry-After 120, not successful or uncertain generations. The worker is allowed to wait for settlement and retry these rejected requests. Commentary and final memo verification remain outstanding. The retained-input footprint is still far too large for a normal run; this continuation preserves the existing research rather than claiming the underlying architecture is fixed.

## Verified Completion

The worker finished at 10:25:22 UTC (20:25:22 Melbourne). Nineteen output checks pass. The final allocation and commentary both have successful provider receipts; the memo contains 214,816 characters and substantive new commentary, rather than only the provisional fallback.

- All 299 prior completed receipts are retained. Both sealed baselines, original portfolio context/snapshot, analytical reviews and provisional recommendation are unchanged.
- All original facts and source passages are unchanged. The original checkpoint's SHA-256 still matches.
- All six plays and the high-risk/5+ year mandate are preserved; all six play assessments are present. Sixteen final targets total 100% within floating-point precision.
- Four new calls succeeded: final allocation, two genuinely changed investment-case batches, and commentary. Three additional attempts were explicitly rejected for temporary provider in-flight credit reservations, then retried after settlement. No new research or source checks ran.
- Reported cost for this successful continuation: US$13.713784. The earlier three completed case batches cost US$6.51514 and were not rerun; this is not a quote for a fresh full analysis.
- All 478 retained source-check verdicts remain. Final dependency selection leaves 119 selected facts explicitly unverified, up from 80 before the final decision. No additional model consistency review ran. The memo includes both qualifications.

Verification details: `/data/operations/portfolio-finish-only-20260923-100700/verification.json`.
Local final operation summary: `outputs/audits/portfolio-finish-only-20260923/resume-3.json`.

[Open the completed assessment memo](https://llm-council-analysis.fly.dev/portfolio-analysis?run_id=portfolio_positioning_job_portfolio_finish_only_20260923_100700.json).

This completes the authorised assessment copy, not the broader architecture remediation or source-verification programme. The nearly million-token final input remains an important efficiency defect for subsequent work.
