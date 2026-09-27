# Portfolio retrieval: Grok versus Parallel

Date: 18 September 2026. Scope: the saved independent portfolio run and the
research reused by the Ling/Opus and proposed Gemini comparisons. No provider
was changed, and no new paid retrieval was commissioned for this audit.

## Conclusion

Grok did useful research. It is not failing to search, and the saved evidence
does not justify calling Parallel universally better. Parallel is the better
fit for the primary, source-traceable evidence service in this application;
Grok is more useful as a distinct market/news discovery and challenge lane.
Replacing Grok with three more copies of the current Parallel task would
preserve several architectural mistakes and lose some market breadth.

This is an audit of contemporaneous outputs, not a controlled provider A/B:
the providers received different prompts and output contracts. The earlier
17 September experiment compared Parallel with Tavily, not Grok.

## What Actually Ran

Each initial lane ran native xAI Grok, Parallel Ultra2x and Perplexity.
Parallel also retrieved text behind citation-only URLs and answered material
follow-up questions. The services are already complementary, not alternatives
that have never been used together.

| Initial lane | Grok web calls | Grok X calls | Grok time | Grok cost | Parallel time | Parallel selected sources |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Macro regime | 22 | 0 | 129s | $0.711004 | 262s | 5 |
| Sector leadership | 16 | 0 | 138s | $0.329464 | 170s | 5 |
| Coverage audit | 19 | 0 | 189s | $0.368618 | 262s | 5 |
| Total | 57 | 0 | Concurrent, not additive | $1.409086 | Concurrent, not additive | 15 |

Grok's costs are the returned `cost_in_usd_ticks` divided by 10^10, including
its tools and caching. [xAI documents this cost field](https://docs.x.ai/developers/cost-tracking).
Parallel's three initial Ultra2x tasks cost $1.80 at the published $0.60/run
rate, not an invoice-confirmed figure. These exclude subsequent extraction,
follow-up, Perplexity and analysis. [Parallel pricing](https://docs.parallel.ai/getting-started/pricing).
The initial Grok calls were both faster and cheaper than the initial Parallel
tasks in this sample. "Replace Grok to save money" is therefore not established.

## Strengths And Limitations

### Grok

- Broad, timely market overview: yield curve, commodities, breadth, credit,
  growth nowcasts, policy, competing forecasts and investment implications.
- Correct central policy observation in this sample: the 16 September hike
  to 3.75%-4.00%, supported by the [Fed statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm).
- Distinguished Atlanta GDPNow from official GDP and noted conflicting
  growth estimates. That distinction is useful for the allocator.
- No X searches, despite both native tools being supplied. X capability is
  not evidence that this run used it.
- The macro summary made many numerical claims with only five attached URLs;
  the sector summary had seven. That is weaker claim-level traceability than
  the breadth of the prose suggests, not proof all those claims are wrong.
- One GDP citation illustrates the provenance weakness: the text calls it
  the August second estimate but points at the July advance-estimate page.
  The numerical value agrees, but the cited vintage does not. The [BEA page](https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026)
  identifies the July 30 advance release and the later August 26 release.
- Three similar macro discussions recur because our wrapper demands a
  comprehensive macro review, commodity list, quadrant verdict and capital
  preferences every time, even for sector and coverage requests.

### Parallel

- Returned excerpts with original sources: Fed/BLS/BIS in macro; S&P sector
  performance, State Street flows, FactSet earnings and bank research in
  sector leadership; fund documentation and issuer filings in coverage.
- Kept different evidence types separate. For example, flows, past returns
  and earnings are not treated as one interchangeable leadership measure.
- Explicitly qualified issuer claims and distinguished report observation
  dates from publication dates in several cases.
- It was not comprehensive. Macro omitted separate current yield and
  commodity price series and explicitly attributed this to the five-source
  limit. It nevertheless marked the broad question "answered".
- Coverage selected VTI, AVUV, GLDM and two NextEra sources, leaving major
  asset categories without evidence. It asked for an available-portfolio
  inventory because our prompt still asks about "available portfolio asset
  classes", although this phase is intentionally portfolio-blind.
- This does not prove Parallel cannot cover those topics. It shows the
  current task definition and follow-up decision are inadequate.

## Citation Workload

The native Grok results contained 5, 7 and 95 URL annotations respectively:
101 unique URLs across the three lanes. Parallel's initial discovery supplied
15 unique URLs; just one exact URL overlapped. Low exact-URL overlap is not
the same as unique information, because different pages can repeat a fact.

The 95-URL response used zero start/end offsets on the sampled annotations,
so the URLs were not attached to identifiable passages. Our adapter retains
these as `provider_citation_only`. It does not pretend their content is a
verified quote. However, all eligible citation URLs then enter hydration.

Grok's native adapter supplied no source text in its normalized result rows.
After hydration, 101 of its 107 result rows carried Parallel citation excerpts,
five reused other retrieved text and one still had none. Counts include
duplicate URLs across lanes. This is direct evidence that Grok discovery
already depends substantially on Parallel for source text in this pipeline.

The checkpoint contains six initial citation-extraction tasks, and one later
follow-up extraction task. Initial extraction serves the shared provider pool,
so its entire cost must not be attributed solely to Grok. Stage-cache task IDs,
not the artifact's compressed receipt list, are needed to count these tasks.

## Recommended Changes, Not Applied

1. Make Parallel the primary source-evidence service. Preserve dated excerpts,
   units, benchmarks and original URLs; keep generated interpretation separate.
2. Use short, distinct research questions. Five results is a starting point
   for one focused question, not a maximum for the entire macro environment.
   Expand only for a material unresolved question, reusing the evidence pool.
3. Remove the portfolio-inventory language from blind coverage discovery.
   Ask about overlooked investable economic exposures and contrary evidence.
4. Give Grok a genuinely different assignment: fast-changing market/news
   developments and alternative explanations not already covered. Use X when
   the question actually calls for it, not as a mandatory activity quota.
5. Treat unanchored URL lists as discovery candidates. Retrieve sources needed
   for material claims or gaps, while retaining all raw output for inspection.
   Do not turn every incidental URL into mandatory downstream work.
6. Do not require the source collector to choose the allocation's quadrant or
   preferred asset classes. The analytical models should form and challenge
   those conclusions from the evidence, not inherit them as established facts.

This keeps the useful breadth of Grok without paying for three near-duplicate
macro essays. A later same-question comparison should score primary-source
coverage, exact claim support, timestamps, unique useful evidence and total
downstream cost. Neither word count nor the number of URLs is a quality score.

## Reproduction

Saved source: `outputs/audits/portfolio-independent-uplift/live/independent-live.json`.
Original provider packets and task IDs: the adjacent checkpoint's hydrated
`PortfolioRuntime.cache` and `provider_tasks`. Inspect those rather than only
the artifact's post-hydration `evidence_runs`.

Code locations: `portfolio_positioning_memo.py` (`_build_macro_environment_news_prompt`,
`_build_evidence_lane_specs`, `_run_single_evidence_lane`),
`backend/research/providers/xai.py` (`cited_sources`),
`backend/portfolio_retrieval.py` (`ParallelSourceProvider`, `normalize_result`),
and `backend/portfolio_sources.py` (`hydrate_citations`).
