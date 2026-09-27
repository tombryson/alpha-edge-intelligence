# Portfolio Retrieval Comparison: 17 September 2026

## Conclusion

For this single request, **Parallel Ultra 2x produced the strongest finished
evidence packet**, while **Pro offered the best speed and cost tradeoff**.
Ordinary Ultra added breadth but also an incorrect missing-data claim. Among
the two search-only calls, **Tavily returned the more useful source set**.

This supports testing Parallel Task research for a focused portfolio evidence
pass. It does not support a blanket claim that Parallel Search is better than
Tavily, or that the more expensive task tier is always more accurate.

All five calls completed. No application configuration, production deployment,
portfolio database, broken-run checkpoint or saved memo was changed. The failed
portfolio run has not been resumed. The only new files are this report and the
standalone benchmark artifacts.

## Test Design

The question was narrowed from the failed run's gold-miner exposure follow-up.
It is not a replay of the original three-trade, 4,526-character request. A single
911-character brief was submitted to every arm:

> As of 2026-09-17 04:47:31 UTC, retrieve dated evidence comparing gold-mining equities with physical gold for portfolio exposure. Cover: (1) latest available gold price in USD/troy oz, identifying spot or futures; (2) latest reported production, all-in sustaining costs (AISC) and realized gold prices for Newmont and Barrick, preserving reporting periods and units; (3) valuation evidence, without inferring cheapness from gold prices alone; (4) miner operating and financial risks versus bullion, including implementation costs; (5) evidence against switching from miners into bullion. Prefer company filings, exchange/fund documents and official industry data. Provide source URLs, publication dates, observation periods and short supporting excerpts. Identify missing evidence explicitly. Exclude information published after the cutoff. Retrieve evidence, not portfolio weights or personal investment advice.

- Parallel Pro, Ultra and Ultra 2x received identical input and identical JSON
  output schemas. Separate memory scopes were used; no prior interaction was supplied.
- Tavily used Advanced Search, 12 results, no generated answer and no full-page
  extraction, matching the portfolio search's essential settings. Publication
  dates and usage metadata were additionally requested.
- Parallel Search used Advanced mode, the same objective and three derived
  keyword queries. Its default returned 10 results. This extra control separates
  search-engine comparison from search-versus-research-agent comparison.
- All arms received the same cutoff instruction. No asymmetric hard date filters
  were applied. Live retrieval is not an archived, point-in-time web snapshot.
- Only one submission per arm was made. Task run IDs were saved immediately;
  subsequent requests only fetched status/results. No paid retries or tier
  escalations were made.
- The Trading Terminal integration uses the same Parallel Task API, currently
  configured for Ultra 4x. This benchmark did not change that configuration.

## Measured Results

| Arm | Duration | Cost basis | Returned material | Assessment on this request |
| --- | ---: | ---: | --- | --- |
| Tavily Advanced Search | 6.97 s | 2 credits | 12 source results | Better search-only source coverage |
| Parallel Advanced Search | 2.69 s | US$0.005 list price | 10 source results | Faster, but missed Newmont's primary release and repeated Barrick's |
| Parallel Pro | 2m 45s | US$0.10 list price | 9 structured findings | Best speed/value; strong fundamentals with provenance limitations |
| Parallel Ultra | 7m 44s | US$0.30 list price | 12 structured findings | Broader, but introduced a false missing-data statement |
| Parallel Ultra 2x | 7m 01s | US$0.60 list price | 11 structured findings | Best finished packet; more precise and better implementation detail |

Task durations use provider creation-to-completion timestamps, including provider
queueing but excluding our polling/download delay. Search times are local HTTP
elapsed times. Ultra 2x finishing before Ultra is one observation, not a general
latency claim. Findings and source results are different units, not comparable
quality scores.

The three completed research tasks total **US$1.00 at published prices**. With
Parallel Search, the published-price total is US$1.005 plus two Tavily credits.
At Tavily pay-as-you-go rates those two credits would cost US$0.016; the actual
account plan or free allowance may differ. These are usage/list-price calculations,
not a reconciled billing invoice. Sources: [Parallel pricing](https://docs.parallel.ai/getting-started/pricing)
and [Tavily credits](https://docs.tavily.com/documentation/api-credits).

## Evidence Quality

### Search-only comparison

Tavily found the current Q2 releases for both issuers, plus other company filings.
However, some excerpts were dominated by definitions, disclaimers and flattened
tables rather than the exact figures needed. Its explicit price result was a
September 11 CFD observation, not a fresh official spot benchmark. Neither its
returned excerpts nor Parallel Search's established a complete valuation and
implementation-cost comparison. Search discovery still needs source reading.

Parallel Search returned useful Barrick Q2 figures directly in its excerpts,
but used three result slots for the same Barrick release across the issuer,
Manila Times and BNN Bloomberg. It did not return Newmont's primary release.
Several other results were commentary or commercial bullion content. Eight of
ten results had publication dates, compared with twelve of twelve for Tavily.
This is date-field completeness, not independent verification of those dates.

### Pro

Pro correctly recovered all six checked Q2 company metrics: production, AISC
and realized gold price for each issuer. It retained units, reporting periods,
non-GAAP caveats and a balanced case for keeping some mining-equity exposure.

Its weaknesses were substantive but local: a 2019 GLD prospectus was used for
implementation evidence, direct bullion costs remained unquantified, and its
precise valuation multiples were supported by a generic Fiscal.ai homepage
citation whose saved excerpt contained field metadata rather than the actual
numbers. Newmont's valuation observation was dated September 17 without a
publication time. The saved material cannot establish that it preceded the cutoff.

Pro also left Barrick's production ownership basis unresolved. The original
release identifies it as attributable; this was retrievable detail, not an
absence in the disclosure.

### Ultra

Ultra added half-year figures, mining-ETF costs, annual-report risks and richer
valuation-feed excerpts. It explicitly flagged the uncertainty around the
September 17 Newmont valuation refresh and CAD/USD reconciliation for Barrick.

However, it said the Newmont release did not provide first-half AISC. The release
does provide YTD by-product AISC of **US$1,321/oz** and co-product AISC of
**US$1,822/oz**. It also used rounded Q2 production rather than the available
1.293 million figure. The first issue is an incorrect evidence-gap claim; the
second is a precision difference. More research did not eliminate reading errors.

### Ultra 2x

Ultra 2x recovered the six checked operating figures and explicitly resolved
Barrick's attributable basis. It used a January 2026 GLD custody FAQ and the
GLDM issuer page, rather than relying on Pro's old prospectus. It identified
GLDM's 0.10% expense ratio, distinguished fund ownership from personally held
bullion, and documented the absence of actual dealer/storage/insurance quotes.

Its Fiscal.ai excerpts at least included dated September 16 P/E observations,
and it assigned low confidence to those rows. Nevertheless, a generic homepage
URL and missing valuation methodology still prevent independent reproduction.
It did not solve the valuation problem simply by using a higher tier.

It also found company-reported sensitivity and cash-flow evidence. These are
useful analytical inputs, but Newmont's sensitivity is pretax guidance and
excludes a stated royalty/tax effect; it is not incremental free cash flow.

## Independent Checks And Limits

The original [Newmont Q2 release](https://www.newmont.com/investors/news-release/news-details/2026/Newmont-Reports-Robust-Second-Quarter-2026-Results-Remains-on-Track-to-Achieve-Full-Year-Guidance/default.aspx)
and [Barrick Q2 release](https://www.barrick.com/English/news/news-details/2026/q2-2026-results/default.aspx)
were opened independently. Reference values were:

| Q2 2026 measure | Newmont | Barrick |
| --- | ---: | ---: |
| Attributable gold production | 1,293,000 oz | 796,000 oz |
| Gold AISC | US$1,621/oz, by-product basis | US$1,866/oz |
| Realized gold price | US$4,414/oz | US$4,417/oz |

The cited [GLDM fee](https://www.ssga.com/us/en/intermediary/etfs/spdr-gold-minishares-gldm),
[GDX fee](https://www.vaneck.com/us/en/investments/gold-miners-etf-gdx/overview),
and [January 2026 GLD FAQ](https://www.ssga.com/library-content/products/fund-docs/etfs/us/tax-documents/gld-faq.pdf)
were checked. The 2019 date on Pro's prospectus was also confirmed.

All three tasks found a September 15 LBMA PM record. An independent JSON fetch
during the audit exposed a September 16 record too. The public JSON does not
carry record-publication timestamps, so this cannot prove when the newer record
became available relative to the cutoff. Ultra and Ultra 2x found September 16
secondary-source spot quotes at different times; those different prices are not
in themselves a contradiction. Their CNBC/USA Today excerpts were preserved,
but independent page opening was unsuccessful, so those quotes are not counted
as independently verified here.

This is a targeted spot audit, not verification of every sentence or every
citation. None of the outputs fully established direct physical-bullion costs,
point-in-time valuation provenance, or a like-for-like total-return comparison.
Those gaps should qualify the relevant claims, not invalidate the usable facts.

One sample cannot establish average quality, reliability, latency or portfolio
outperformance. Nor did this test measure the full pipeline's downstream token
cost or prove that an extraction/review stage can safely be removed. Search and
Task APIs perform different amounts of work.

## Recommendation For The Next Pass

1. Use **Ultra 2x** when the objective is the best finished packet among these
   tested options for a consequential, focused question. Use **Pro** when the
   objective is routine evidence retrieval with shorter turnaround. Do not run
   all three tiers as a new mandatory council.
2. Do not replace Tavily with Parallel Search solely on this result. Tavily was
   the stronger discovery call here. Parallel Task is the more promising change
   for structured follow-up evidence, potentially replacing existing work rather
   than adding another layer.
3. Regardless of provider, fix the overlong-query construction, the follow-up
   triggered by deliberately deferred fields, and the all-providers-required
   failure rule. Preserve baseline research and process successful supplements.
4. Preserve Parallel's field-level basis, source excerpts, dates, units and
   provider run IDs. Keep uncertain valuation records labeled as such; do not
   substitute provider confidence for independent source support.
5. Once the patch is tested, resume the failed run from its retained checkpoint.
   This benchmark has not been inserted into that run or treated as a replacement
   for its missing evidence processing.

## Saved Outputs

The complete exact requests, raw responses, run IDs, timings and offline inventory
are in `outputs/audits/parallel-tavily-20260917/`. Readable copies:

- [Parallel Pro](../outputs/audits/parallel-tavily-20260917/parallel_pro.md)
- [Parallel Ultra](../outputs/audits/parallel-tavily-20260917/parallel_ultra.md)
- [Parallel Ultra 2x](../outputs/audits/parallel-tavily-20260917/parallel_ultra2x.md)
- [Tavily Advanced Search](../outputs/audits/parallel-tavily-20260917/tavily_search.md)
- [Parallel Advanced Search](../outputs/audits/parallel-tavily-20260917/parallel_search.md)

The standalone submission script refuses to repeat a manifest's paid requests.
Credentials were held only in memory and excluded from all saved requests and
responses. No package installation or application dependency change was needed.
