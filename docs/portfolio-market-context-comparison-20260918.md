# Market Context Retrieval Comparison: 18 September 2026

## Conclusion

**Parallel Ultra2x supplied the best evidence packet on this request.** The
Parallel-plus-DeepSeek arm produced the strongest finished brief, but DeepSeek
largely restated an already-good packet, added nine minutes, and omitted one
source definition. For this role I would use the Parallel packet directly in
the existing evidence/synthesis pipeline rather than mandate another rewrite.

Sonar was the fastest and cheapest, and appropriately admitted missing yield
data, but its broken citation mapping prevents treating this output as a
fully traceable research brief. Gemini retrieved useful facts but made material
financial interpretation errors. Opus was expensive without solving the
same-date yield retrieval problem; it also made financial errors.

This is a task-specific recommendation, not proof that one provider is
universally better. In particular, Grok was not run on this same prompt.

## Measured Results

| Alternative | Time | USD cost | Result on this question |
| --- | ---: | ---: | --- |
| Parallel Ultra2x + DeepSeek V4.1 Flash | 11m 58s end-to-end | $0.60320 | Best combined evidence and financial discipline; extra rewrite added little |
| Perplexity Sonar Pro | 18s | $0.02775 | Fast and cautious, but no exact curve and materially broken citations |
| Gemini 3.8 Flash + native Google Search | 47s | $0.13319 | Correct older curve and macro facts; unsafe real-return/duration claims |
| Claude Opus 5 + native Anthropic search | 1m 41s | $1.54133 | Useful nuance, but mixed yield dates, financial errors and poor retrieval value |

**Parallel's research alone took 2m 48s and costs $0.60 at list price.**
DeepSeek took a further 9m 01s and reported $0.00319707. Roughly nine additional
seconds in end-to-end delivery came from local polling/download/orchestration.
DeepSeek resolved to `deepseek/deepseek-v4.1-flash` and completed normally;
its 5,309 completion tokens included 3,492 reasoning tokens. This was latency,
not token-limit truncation. One observation does not establish normal latency.

The experiment totals **$2.30546**, combining response-reported model costs
with Parallel's published $0.60 successful-task price. It is not a reconciled
invoice. Native search charges are already included in the returned
OpenRouter totals, not added twice. The rejected direct Anthropic request
reported no usage; no positive cost is assumed for it.
[Parallel pricing](https://docs.parallel.ai/getting-started/pricing).

| Quality dimension | Parallel + DeepSeek | Sonar | Gemini | Opus |
| --- | --- | --- | --- | --- |
| Latest decision and six CPI/employment values | Correct in checked claims | Correct | Correct | Correct |
| Latest four-maturity, single-date official curve | All four, September 17 | All four missing | All four correct for September 16, one day older | Incomplete and dates mixed |
| Publication vs observation dates | Clearly separated; missing publication time admitted | Release dates underspecified | Mostly explicit | Yield dates unreliable |
| Source traceability | Best packet; DeepSeek drops reference 6 | Two nonexistent references plus wrong mappings | Mixed source quality/attribution | Official and secondary material mixed |
| Financial interpretation | Most careful of the four | Generally cautious, less complete | Material duration/real-return errors | Material reinvestment and pricing errors |
| Dated post-meeting futures probabilities | Not established, admitted | Not established, admitted | Not established; older odds added | Not established; older odds qualified |

## Scope

One identical, unseeded research question was sent to four alternatives for the
portfolio's current-news and market-context role. This is a live paid experiment,
not simulated answers and not a rerun of the portfolio. No application code,
saved portfolio, persistent model route or deployment was changed.

The question asked for the latest Fed decision, a same-date official Treasury
curve, the latest CPI and employment releases, changes in the policy outlook,
and the case for and against cash/bills, short Treasuries and long-duration
Treasuries. Every arm received the same cutoff, **18 September 2026 at
07:54:33 UTC**, and a request for 700-1000 words, dated evidence, short excerpts,
primary sources, balanced interpretation and explicit unknowns. No source URLs,
holdings, past memo or desired investment conclusion were supplied.

The complete prompt and its hash are in
`outputs/audits/market-context-20260918/manifest.json`.

## Configurations

| Arm | Configuration | Source of interpretation |
| --- | --- | --- |
| Perplexity | `sonar-pro`, native Sonar API, default search context | Sonar Pro |
| Gemini | `google/gemini-3.8-flash`, OpenRouter with explicitly native Google search | Gemini |
| Claude | `anthropic/claude-opus-5`, OpenRouter with explicitly native Anthropic search | Opus |
| Parallel + DeepSeek | Parallel Task `ultra2x`, then `~deepseek/deepseek-flash-latest` without additional search | Parallel's research reasoning, then DeepSeek's brief |

Gemini and Claude were not silently given Exa search. The request explicitly
selected `engine: native`, and the responses reported Google/Anthropic providers
and native search usage. [OpenRouter native-search documentation](https://openrouter.ai/docs/guides/features/plugins/web-search).

The original direct Anthropic request was rejected before generation because
that separate account had insufficient credit. The accepted Opus call used the
already-funded OpenRouter account. Both responses are retained. The rejection
is not treated as a model-quality failure.

These are four **retrieval-plus-interpretation systems**, not four raw models
with identical tools. Parallel Ultra2x performs research and synthesis itself;
DeepSeek then receives its complete packet. The shared instruction says to
start with five relevant sources and expand only for unresolved material facts.
It is not a five-source hard limit, and provider search budgets differ.

## Independent Reference Checks

Primary documents were opened independently after submission. None of this
verification material was fed back into the benchmark arms.

| Check | Reference value | Primary source |
| --- | --- | --- |
| Latest decision | September 16; +25 bp to 3.75%-4.00%; effective September 17 | [FOMC statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm), [implementation note](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a1.htm) |
| Latest Treasury curve | September 17: 3M 4.12%, 2Y 4.67%, 10Y 4.94%, 30Y 5.29% | [Treasury nominal par curve](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=2026&type=daily_treasury_yield_curve) |
| Prior Treasury curve | September 16: 3M 4.14%, 2Y 4.74%, 10Y 5.01%, 30Y 5.35% | Same Treasury table; corroborated by [H.15](https://www.federalreserve.gov/releases/h15/) |
| CPI | August: headline +0.4% m/m SA, +3.4% y/y NSA; core +0.3% m/m SA, +2.4% y/y NSA; released September 11 | [Archived BLS CPI release](https://www.bls.gov/news.release/archives/cpi_09112026.htm) |
| Employment | August: payrolls +162,000; unemployment 4.1%; released September 4 | [Archived BLS employment release](https://www.bls.gov/news.release/archives/empsit_09042026.htm) |
| SEP median policy path | 2026 4.1%, 2027 4.1%, 2028 3.9%, 2029 3.6%, longer run 3.2%; projections, not market prices | [September SEP](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm) |

The saved H.15 release was dated September 17 but its last observation was
September 16. Treasury's own table contained September 17. This is precisely
why publication date and observation date cannot be used interchangeably.
The Treasury page does not expose an exact publication timestamp for each row;
the September 17 row was present during verification on September 18.

Compressed HTML snapshots and hashes are saved under the audit's
`source-checks/` directory. Direct BLS HTTP requests received 403 responses;
the archived releases were successfully read through the independent web
research tool. The saved 403 pages are explicitly labeled as such, not claimed
to contain successful source downloads.

## Perplexity Sonar Pro

**Strongest feature:** fast, inexpensive, and generally cautious about numerical
gaps. It recovered the correct decision, all six CPI/employment headline values
and the 4.1% year-end SEP median. It declined to fabricate the Treasury curve
or current futures probabilities. Its maturity discussion was generally
balanced, although nominal versus real return received little explicit treatment.

**Material problems:**

- No exact yield was recovered for any of the four requested maturities.
- The response has 37 citation URLs, but cites `[39]` and `[41]`, which cannot
  resolve. This defect exists in the saved raw provider response, before any
  application processing.
- The CPI sentence cites `[27]`, which maps to the Fed SEP rather than BLS.
  The employment sentence also cites `[29]`, which maps to Yardeni's SEP page.
  Yield discussion cites `[19]` and `[30]`, mapping to FinanceFeeds and Fisclear,
  not the Treasury table described in the prose.
- Release dates are often reduced to "September" rather than the requested
  specific dates. It supplies no supporting-excerpt table.

There are useful BLS and Treasury results elsewhere in the returned source
list. That does not repair incorrect claim-to-source mapping. Source discovery
and reliable citation attribution are separate requirements.

## Gemini 3.8 Flash

**Strongest feature:** the most complete fact table among the three integrated
model/search arms. All six CPI/employment values and release dates checked out,
as did the decision and main SEP median values. Its four yields are valid for
September 16, which it labels, but not the latest September 17 curve available
during this test.

**Material problems:**

- It explicitly calls bills "Zero Duration Risk" and later says they eliminate
  capital risk. A fixed-maturity bill has small, nonzero price sensitivity before
  maturity. Principal repayment at maturity is not a guarantee of its resale
  price. [Treasury pricing](https://www.treasurydirect.gov/marketable-securities/understanding-pricing/),
  [SEC interest-rate-risk explanation](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-86).
- It repeatedly labels nominal yield minus trailing CPI as a real return that
  the instrument delivers. That is a backward-looking comparison, not a locked
  future purchasing-power return over three months, two years or thirty years.
- Bills do not reset immediately like floating-rate notes; newly purchased or
  rolled bills reflect changed yields. Its "Floating Reset" language blurs this.
- The purported Treasury excerpts use "Up"/"Down" wording characteristic of
  the secondary dashboard referenced in the grounding annotations, not the
  official table. The numbers can be checked, but the quoted attribution is poor.
- The grounding metadata mixes official sources with social, trading and other
  secondary sites. Sixteen citation URLs and eight searches do not establish
  that every assertion was supported by a primary source.

It recognizes the absence of an exact post-meeting futures snapshot, but also
introduces pre-meeting probability estimates that this audit has not independently
validated. Its final paragraph is too confident relative to that limitation.

## Claude Opus 5

**Strongest feature:** a useful distinction between energy-driven headline
inflation and decelerating core inflation, and explicit disclosure of conflicting
yield sources. It recovered the correct main macro releases and clearly warned
against treating an undated futures snapshot as a current probability.

**Material problems:**

- It did not retrieve the requested official, single-date curve. The 3M figure
  is a flagged September 10 estimate. Its 2Y 4.67%, 10Y 5.00% and 30Y 5.36%
  correspond together to September 15, but are presented as September 16 or
  an ambiguous September 15/16. The official September 16 values differ.
- It states the SEP year-end projection range as 4.1%-4.4%. The table identifies
  that as the central tendency; the full range is 3.9%-4.4%.
- It claims locking a thirty-year coupon eliminates reinvestment risk for the
  coupon stream. Fixed coupon amounts do not fix the rates at which those
  received payments can be reinvested. [FINRA yield and return guidance](https://www.finra.org/investors/insights/bond-yield-return).
- Its short-end yield premium is treated too directly as extra hikes already
  priced in, without establishing the expected path and term-premium decomposition.
- Some real-return phrasing also relies on trailing CPI, albeit with more
  qualification than Gemini. Speculative interpretation of the curve does not
  compensate for incorrect observation dates.

The API reported 255,390 prompt tokens across the search interaction and nine
search requests. This is observed billed usage, not 255,390 tokens of our
original prompt. It was the most expensive successful arm by a large margin.

## Parallel Ultra2x And DeepSeek

**Strongest feature:** the research packet recovered the latest official
September 17 curve and correctly separated CMT yields from bank-discount bill
quotes and executable security prices. It preserved reporting periods, used
the archived BLS releases, and explained why trailing inflation cannot establish
a future real return. Its discussion treated duration as two-sided, cash as
an unspecified vehicle rather than a single guaranteed yield, and Fed dots as
conditional projections rather than market prices.

DeepSeek preserved those main facts and qualifications. It correctly states
that it performed no additional search. The final text is 917 whitespace-delimited
words compared with 1,023 in the Parallel packet including its references.

**Remaining limitations:**

- No numerical, dated CME futures probabilities were recovered. A provider
  timestamp and methodological description are not the missing probability
  table. This is a genuine unresolved part of the request.
- The exact publication timestamp of Treasury's September 17 row was not
  established; the observation date is clear.
- The final text cites `[6]` but omits that reference from its source list.
  The original Parallel packet retains it: the annual Treasury table. The
  same substantive yield claim also cites the retained monthly table `[7]`.
  This is a recoverable citation omission, not grounds to discard the brief.
- Some provenance inherited from the packet, such as the H.15 reference's
  older title date, still needs normalization against the actual saved page.
  H.15 was not relied on for the September 17 curve.
- DeepSeek added no independently retrieved evidence or demonstrated
  verification. Its low token cost does not make a nine-minute rewrite useful.

## Recommended Architecture

1. Use Parallel Ultra2x for the focused current-news/context packet, sharing
   that evidence with the portfolio analysts. Do not add an obligatory
   DeepSeek paraphrasing step merely because a second model is available.
2. Retrieve repeated structured series, especially Treasury yields, through
   their official data feeds. Preserve date, units and yield convention.
   Reserve research for developments, contradictions and material missing
   context instead of repeatedly asking models to recover the same table.
3. Preserve source identifiers outside model-written prose. Check that cited
   identifiers resolve and actually support the associated claim. A missing
   citation should be marked/repaired locally, not invalidate all useful work.
4. Keep facts, provider interpretation and downstream investment judgment
   distinguishable. Do not propagate claims of zero duration or guaranteed
   real returns just because they arrive inside a cited research answer.
5. Before replacing Grok in production, test this winner against Grok on the
   same prompt and another materially different news question. This four-way
   test did not measure X-specific discovery or broad emerging-theme recall.

No part of this recommendation has been implemented in production.

## Limits

This is one question, one accepted generation per arm, and a targeted spot
audit, not exhaustive validation or a general financial-model leaderboard.
The audit was performed manually, not model-blind. Provider defaults differ.
None of the four was supplied a known answer or given a repair prompt after
quality inspection. Grok was not included in this four-way comparison, so this
does not establish that the winner beats Grok on the same request.

A local disk-space error interrupted polling of the already-submitted Parallel
task. Its task ID was retained and that same task was resumed; no duplicate
research submission was made. Provider elapsed time can therefore be separated
from local end-to-end delivery time.

## Full Outputs

- [Sonar Pro](../outputs/audits/market-context-20260918/sonar.md)
- [Gemini 3.8 Flash](../outputs/audits/market-context-20260918/gemini.md)
- [Claude Opus 5](../outputs/audits/market-context-20260918/claude.md)
- [Parallel Ultra2x original packet](../outputs/audits/market-context-20260918/parallel-evidence.md)
- [Parallel + DeepSeek final brief](../outputs/audits/market-context-20260918/parallel_deepseek.md)

Raw requests, complete API responses, timings, usage, provider task IDs,
source snapshots and the offline inventory are in
`outputs/audits/market-context-20260918/`. Credentials are not saved in them.
