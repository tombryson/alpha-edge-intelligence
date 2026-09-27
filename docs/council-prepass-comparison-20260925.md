# Analyst Council prepass pilot: 25 September 2026

## Decision

Parallel ultra2x is a credible replacement for the **web research component**, not yet a demonstrated replacement for the entire prepass. It recovered important filings missed by the fresh Perplexity packets and handled conditional events well. It was only modestly cheaper and roughly twice as slow in this pilot. Do not remove native ASX discovery, PDF decoding or document-level evidence preservation.

The strongest immediate improvement is preserving material evidence through the existing handoff. A provider swap without that fix still discards useful research.

Production routing and configuration were not changed. No council job or deployment was started.

## Experiment

Two companies with saved prepasses: AT4 (cutoff 19 August 2026), EIQ (17 August 2026). Each fresh arm received the same cutoff, research brief and three material native-discovery URLs. All requested source-grounded facts, not investment recommendations. Independent arms ran concurrently.

1. Perplexity Responses API using the observed production `openai/gpt-5.6-sol`, deep-research preset and max_steps 4.
2. Parallel Task API `ultra2x`, one research task per company.
3. Parallel advanced Search (five results), Extract, and one summary call using the historical worker `openai/gpt-5-mini`.
4. Diagnostic extension of arm 3: same URLs and worker, full-content extraction instead of default excerpts.

**Important limits:** the fresh Perplexity arm replays its retrieval component, not the full production native/PDF/vision harness. The Search/Extract arm uses a batch worker prototype, not the original per-document worker. Live searches constrained to historical dates are not archived-web experiments. These are two exploratory cases, not a universal engine ranking. No downstream analyst or full council was rerun; the handoff was inspected directly.

Historical full prepasses were fetched read-only: AT4 had 40 decoded documents and 25 bundled documents; EIQ had 39 and 25. Native discovery added 48 and 26 candidates respectively. These references cannot fairly be assigned the fresh retrieval timings or costs.

## Results

Ten material checks per company were frozen before inspecting fresh answers. Each receives 0 (missing/wrong), 1 (partial), or 2 (accurate and appropriately qualified). This measures selected material coverage, not the truth of every sentence. Detailed scoring is in `scores.json`; definitions in `rubric.json`.

| Fresh approach | AT4 coverage /20 | EIQ coverage /20 | AT4 time | EIQ time | AT4 USD | EIQ USD |
|---|---:|---:|---:|---:|---:|---:|
| Perplexity retrieval | 12 | 17 | 4m41s | 3m58s | 0.739 | 0.603 |
| Parallel ultra2x | 17 | 18 | 9m11s | 7m27s | 0.600* | 0.600* |
| Search + default excerpts + worker | 0 | 4 | 40s | 55s | ~0.020* | ~0.029* |
| Same URLs + full extraction + worker | 10 | 10 | 67s | 79s | ~0.028* | ~0.042* |

Perplexity prices are actual API-reported usage; worker prices are actual OpenRouter response usage. Asterisks combine these with Parallel list-price estimates, not a reconciled invoice. Full-content times/costs include the original search as the hypothetical standalone path, not every earlier diagnostic attempt. Ultra2x costs $600 per 1,000 tasks; Search advanced is $5/1,000 and Extract $1/1,000 billed units at published rates. See [Parallel pricing](https://parallel.ai/pricing).

Across the two cases, ultra2x list cost was about 11% below Perplexity's measured retrieval cost. This is **not evidence of a large full-pipeline saving**. Historical complete-harness cost was not measured. Total pilot cost, including both extraction variants, is approximately **US$2.65** using those assumptions, excluding any unreported charge for the rejected request.

## What improved, and what did not

### AT4

- Perplexity accurately distinguished the potential US$18m DOE award from committed funding, conditional acquisition from ownership, and permitted feed capacity from production. It supplied useful acquisition dilution detail.
- It missed the June quarterly cashflow: A$19.514m cash, A$6.289m operating outflow and the dated 3.10-quarter funding ratio. Its cash discussion instead retained the older A$26.5m pro-forma calculation. It also omitted the material Antimony Canyon target/intercept evidence checked here.
- Ultra2x found that cashflow and the conceptual exploration target. It reconciled the September meeting dates and highlighted contradictory reported share counts rather than guessing a reconciled total.
- Ultra2x was not complete: it omitted the A$26.5m pro-forma bridge and did not explicitly preserve the down-hole/unknown-true-width qualification on the 10.37m intercept. Its lack-of-expansion-study qualification was present only in a later risk field.
- Excerpt-only extraction returned document headings and fragments but missed the DOE amount and conditions. The worker incorrectly called these undisclosed. Full extraction recovered the relevant paragraphs and the same worker then preserved them. This is a concrete extraction failure followed by an overconfident summary, not proof that the worker cannot understand the filing.

### EIQ

- Both research engines preserved important placement, cash, regulatory and data-licensing conditions.
- Ultra2x found the **17 August executed note and option agreements**, distinguished execution from cash receipt, and superseded the older documentation-pending status. Perplexity missed this release and left execution as an unanswered question. Native discovery in the historical prepass had found it.
- Ultra2x separated AS clearance from HF review, distribution access from customers/revenue, and initial financing from the optional clearance-dependent second tranche. It identified the issuer's 91.0% versus 91.1% specificity discrepancy without inventing a reconciliation.
- Perplexity covered Mount Sinai and the separate Mayo cardio-oncology collaboration better. Ultra2x omitted Mount Sinai; its H1 2027 study milestone appeared only in quarterly timeline/catalyst fields.
- Full extraction contained June operating cash use of A$2.733m, but the batch worker still omitted it. Full extraction therefore fixes only one source of loss; materiality-aware summarisation remains necessary.

## Source fidelity and compatibility

Material spot checks used the saved primary-document text: DOE conditions, refinery expansion status, AT4 quarterly cashflow, EIQ executed agreements, conditional Pro Medicus financing, Advara terms and EIQ cashflow. Raw responses, provider citation bases and excerpts remain inspectable. Not every discovered source or numerical assertion received an exhaustive external audit.

No packet carried an explicitly post-cutoff document date. This metadata check does not prove absence of all temporal leakage from live websites. Perplexity deliberately included older foundational ownership/clearance disclosures outside the preferred 365-day window, which is reasonable when correctly dated.

The five-result Search prototype produced irrelevant or weak discovery, including an American Airlines URL for AT4, a blocked secondary page, and current financial aggregation pages. The worker did not turn the airline page into AT4 evidence, but fetching it wasted work. Many useful results came from the supplied native seeds, not new discovery. Five broad search results are not an adequate replacement for a filing inventory.

Both ultra2x tasks returned valid JSON followed by a Markdown References appendix despite the text-only JSON instruction. A deterministic adapter parsed the first object and retained the appendix; no paid repair was needed. The raw output remains saved. A production integration should request a structured schema, preserve provider citation basis, and tolerate only understood wrappers.

EIQ's worker returned `capital_structure` as a dictionary rather than the requested list in both extraction variants. The existing handoff iterates its keys, not its values. Some capital facts survived elsewhere, but this is a real compatibility defect. There must be explicit normalization of this field before integration, not silent success or a wholesale memo failure.

One diagnostic Extract submission used the wrong full-content parameter location and received HTTP 422. Its receipt was preserved and a corrected, separately labelled request was accepted. The valid setting is `advanced_settings.full_content`; [official settings](https://docs.parallel.ai/extract/advanced-extract-settings). No uncertain paid request was repeated. Initial parser-error files remain as historical diagnostics even after successful deterministic parsing.

## Existing handoff loses research

`backend/jobs/prepass.py::_build_stage1_prepass_source_rows_from_bundle` orders price-sensitive documents first, then importance/date; selects at most 24; concatenates one-line summary, paragraph, key points, timeline, catalysts, capital and risks; then cuts each result to 1,600 characters. Supporting excerpts and top-level unanswered questions do not enter these source rows.

| Packet | AT4 rows clipped | EIQ rows clipped |
|---|---:|---:|
| Historical full prepass | 24/24 | 24/24 |
| Fresh Perplexity | 8/11 | 10/11 |
| Ultra2x | 5/20 | 4/11 |
| Full extraction prototype | 3/3 | 4/4 |

Clipping is not itself proof of lost materiality. Specific verified losses are:

- Historical AT4: precise June cash and operating burn occur later in the full summary, while the handoff retains rounded cash and a runway figure but drops A$6.289m operating outflow.
- Historical EIQ: A$2.733m operating outflow is in the full summary but absent from the handoff.
- Fresh Perplexity AT4: its correctly qualified A$26.5m pro-forma cash bridge disappears from the acquisition source row.
- Ultra2x AT4: the explicit absence of an expansion scoping/PFS/FS and established costs/economics disappears.
- Ultra2x EIQ: the H1 2027 cardio-oncology study milestone disappears.

The saved historical bundles also contain generic governance/index material with substantial importance scores. More documents do not necessarily mean a better Stage 1 packet. The non-price-sensitive EIQ financing execution demonstrates why the exchange's price-sensitive marker must not be the dominant definition of materiality.

## Recommended architecture

```text
Native ASX / issuer filing inventory (retain)
                  |
        deduplicate + date/issuer checks
                  |
       full text / tables / vision when needed
                  |
 material document summaries, reuse cached work
                  |
  one evidence packet with sources and conditions
                  ^
                  |
 Parallel ultra2x: external context / material gaps
                  |
 materiality-aware handoff -> unchanged Stage 1 council
```

This is a recommended integration, **not an additional tested arm**. Do not run a full Perplexity research pass and a full ultra2x pass for every company. Parallel replaces a research function; it should not create a new compulsory debate/review loop.

### Smallest useful next changes

1. Fix the handoff first: keep value, date, unit, status/condition and source together; avoid summary duplication; choose complete material facts rather than chopping the tail. Preserve cash/burn, binding status, dilution and catalysts without simply making every packet much larger.
2. Retain native filing discovery. Require the latest relevant cashflow and financing/status disclosures to be considered, regardless of price-sensitive tags. Use missing evidence as a qualification, not a reason to fail the entire analysis.
3. Add a provider adapter for Parallel ultra2x with the same source contract and saved citation basis. Use structured output and narrow deterministic normalization. Do not refactor council voting or chairman logic.
4. Use full-document extraction or the existing PDF decoder for financial tables and binding terms. Default excerpts are useful for discovery, not a substitute for reading a material filing. Distinguish 'not in retrieved excerpt' from 'not disclosed'.
5. Validate the hybrid on these cases and one different sector before switching production. Hold the analyst model/prompt constant in a subsequent paired Stage 1 check to establish whether improved packets actually improve the analysis.

Do not add more reviewer models, generic checklists, or repeated searches to compensate for a lossy handoff. The evidence already contains much of what we need.

## Reproduction and artifacts

- Driver: `scripts/benchmark_council_prepass.py`
- Offline measurements: `scripts/assess_council_prepass_benchmark.py`
- Root: `outputs/audits/council-prepass-20260925/`
- Frozen protocol/settings: `manifest.json`; scoring: `rubric.json`, `scores.json`; mechanical measurements: `metrics.json`.
- Each company directory contains historical documents, requests, responses, raw content, parsed packets, handoffs, and Parallel task status/result/citation basis.
- Paid POST requests have saved submission receipts before dispatch; a request without a response is not automatically resubmitted. Successful responses are reused. Task polling follows the saved run ID.
- No secrets were written to benchmark artifacts. Only local benchmark scripts and this report were added; unrelated existing worktree changes were preserved.

## Handoff repair implemented locally

After this comparison, the authorised handoff repair removes the per-document character cut and per-field list slices. It retains complete facts, capital terms, risks, dated milestones and their conditions; normalizes string/list/object fields; and removes exact repeated statements within a source. Similar statements with different numbers, dates or qualifications are deliberately not merged. Source IDs, URLs and dates remain attached. Existing document selection/count policy is unchanged.

Stage 1 now receives one authoritative packet instead of overlapping clipped fact digests and excerpts. Its second per-document cut and lossy prompt compression are bypassed for that packet; the non-prepass path is unchanged. The cache version is advanced so old clipped rows cannot silently masquerade as complete evidence. Old artifacts are not deleted; a stale cache will require the normal fresh-prepass path on the next run.

Offline replay of eight saved packets verified the restored AT4/EIQ cash-burn figures, AT4 pro-forma cash and expansion-study qualification, and EIQ H1 2027 milestone in the analyst prompt. Every replay passed the existing mandatory-fact coverage check. Results are saved separately in `handoff-remediation-replay.json`; the original benchmark artifacts are unchanged. No paid model call was made for this repair.

Size tradeoff: complete ultra2x excerpts total 26,161 / 18,673 characters for AT4/EIQ versus the previous clipped 23,782 / 16,072. Verbose historical bundles total 152,704 / 129,151 versus about 38,400 previously. Those older bundles contain many differently worded repetitions; this deterministic change does not claim to eliminate semantic paraphrases. It preserves them rather than risk merging contradictory financial claims. Removing missing information necessarily increases inputs relative to clipped evidence; reducing the upstream repetition further is separate from this repair. No new research or model-review loop was introduced. Not deployed.

## Web-provider substitution implemented locally

The authorised production-code substitution now defaults the full-document prepass to Parallel Task `ultra2x`. `backend/research/providers/parallel_prepass.py` returns source candidates under the existing research-provider contract, with structured output, dates, material facts and conditional status. The pipeline still performs native MarketIndex/direct-ASX discovery, issuer checks, PDF/text decoding, worker/vision summarisation and bundle construction. Eligible web-discovered ASX documents now survive the native merge rather than being discarded merely for not residing on the issuer website.

Model Routing exposes `Analyst Council / Prepass - Web research`, using `COUNCIL_PREPASS_WEB_PROCESSOR` (default `ultra2x`) and `PARALLEL_API_KEY`. The app explicitly selects Parallel; the standalone utility retains `--web-research-provider perplexity` for deliberate legacy comparisons, never as an automatic paid fallback. This does not change Perplexity Stage 1 analyst assignments or unrelated portfolio research.

Each output directory saves `parallel_web_research.json`: submission intent, exact request, frozen cutoff, processor, task ID, raw result and citation basis. Re-entry with the same request polls its saved task; completed results are reused. Uncertain or rejected POSTs are not blindly repeated. Missing credentials, rejected research or pending tasks are recorded while native discovery can continue. The local utility and worker module paths also work outside the flattened Docker image.

Verification uses mocked provider responses and the actual native-merge path, not another paid research run. No production overrides, secrets or deployments were changed by this implementation.
