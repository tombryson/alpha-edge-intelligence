# Portfolio Replay: Ling Financial + Claude Opus 5

Audit date: 18 September 2026. Replay completed locally at 16:40 AEST, with limitations retained. No production deployment.

## Judgment

**Ling Financial + Opus 5 produced a more forceful critique, not a demonstrated improvement in financial reliability.** The final allocation balances at 100%, and Opus offers useful objections to concentration and undefined hedges. However, it repeatedly misreads the independent proposal, carries incorrect risk arithmetic into the finished commentary, and substitutes confident sector stories for some missing investment evidence.

Ling supplies a genuinely different independent view, but its financial specialization did not prevent unsupported sizing, benchmark mismatches or unreliable response structure. The application also loses some usable Ling detail before synthesis. This is not a clean test of everything Ling returned.

My decision: **do not replace the existing analytical roster wholesale on this evidence.** Retain the independent workflow. Opus is promising as a challenger and writer, but its conclusions still need accurate proposal reconciliation and financial checks. Ling needs compact inputs and better integration before its contribution can be judged fairly. None of these artifacts establishes superior investment performance.

- **Best architecture:** the two new-workflow runs tie; both establish genuinely separate initial views.
- **Best document to read:** legacy, mixed Ling/Opus, original new workflow, previous September.
- **Best observed accounting:** mixed and previous September; the original new run's application ledger is invalid despite its model proposal totalling 100%.
- **Best instrument distinctions in this sample:** original new workflow. The mixed run's bill/TIPS, commodity/equity and healthcare arguments contain important regressions.

[Read the mixed memo](http://127.0.0.1:5194/portfolio-analysis?run_id=mixed-ling-opus.json) or [the original same-day memo](http://127.0.0.1:5194/portfolio-analysis?run_id=independent-live.json).

## Experiment

This is a local, frozen-evidence replay of the new independent portfolio workflow. Production model routing, application code and the visual layout have not been changed or deployed for this experiment.

| Analytical role | Replay model |
| --- | --- |
| Holdings-blind ideal portfolio | `inclusionai/ling-3.0-flash-fin:free` |
| Separately formed current-portfolio assessment | `anthropic/claude-opus-5` |
| Exposure-equivalence review | Ling |
| Defensive-regime review | Opus |
| Provisional reconciliation | Opus |
| Investment-case batches | Ling |
| Final reconciliation | Opus |
| Financial commentary | Opus |

Research retrieval, extraction and source checks are reused, not regenerated. No new Grok, Perplexity or Parallel research was requested. Grok remains the retrieval choice for a fresh run, but it is not called in this experiment.

The saved research cutoff is `2026-09-18T01:08:38.750731Z`. Both same-day runs use the same portfolio: 12 held asset classes, no standalone position records, no supplied investment plays and no completed investor mandate. The initial ideal request excludes existing holdings and their category catalogue; the current-aware allocator does not receive the ideal. Models meet only at the review stage.

This is not a perfectly isolated model-quality experiment. The original completed run started allocation responses at 16k tokens; this replay uses the subsequent 32k allocation setting. Different providers, tokenizers, retries and one sample per role also matter. The comparison does not establish expected returns, outperformance or a general model leaderboard.

Saved hashes confirm identical portfolio context, research cutoff, initial ideal prompt, initial current-aware prompt and final evidence bundle. The ideal was saved before the current-aware request; that request did not see it. Transport-format repairs and the final Markdown recovery are documented below. Older-generation comparisons remain observational because their portfolios, evidence and prompts differ.

## Updated Scorecard

Scores are ordinal judgments out of 10, using the same rubric as the [earlier three-generation audit](portfolio-three-generation-comparison-20260918.md). They evaluate these saved artifacts, not model brands in general. One-point differences are not statistical precision. The first three columns preserve the earlier judgments.

| Dimension | Legacy | Previous September | Original new | Ling + Opus | Replay finding |
| --- | ---: | ---: | ---: | ---: | --- |
| Independence from existing holdings | 2 | 5 | 9 | 9 | Same verified input isolation. |
| Freedom to choose exposures | 3 | 6 | 8 | 8 | Ling forms its own portfolio rather than filling current categories. |
| Assessment of the current book | 5 | 6 | 7 | 6 | All holdings assessed, but small-position and sector assumptions are too categorical. |
| Macro reasoning | 5 | 6 | 6 | 6 | Useful mechanisms; much of the regime framing is inherited from research. |
| Pricing, expectations and investable edge | 3 | 4 | 5 | 4 | Some explicit pricing discussion, but cheapness and exact weights remain underwritten poorly. |
| Instrument and exposure distinctions | 3 | 7 | 8 | 6 | Strong objections coexist with bill/TIPS and commodity/equity errors. |
| Challenge and contrary evidence | 4 | 5 | 7 | 7 | Undefined hedges and shared policy risks receive useful challenge. |
| Faithful reconciliation | 4 | 5 | 4 | 3 | Wrong long-bond attribution survives into the final memo; numeric links also lost. |
| Risk and sizing justification | 3 | 4 | 4 | 3 | Commodity shock is applied directly to equity weight; no justified risk model. |
| Investor constraints | 2 | 5 | 3 | 3 | Same empty mandate and existing projection limitations. |
| Source traceability and verification | 3 | 6 | 5 | 4 | 19 of 63 structured references no longer resolve; 11 others lack source-review checks. |
| Data vintage and benchmark comparability | 3 | 5 | 5 | 5 | Explicit cautions help, but benchmark and period mismatches remain. |
| Funding arithmetic | 2 | 8 | 2 | 8 | Raw proposal and assembled ledger both equal 100% in this sample. |
| Positioning ranges versus required trades | 7 | 3 | 6 | 6 | Ranges retained; economic mapping is still not robust. |
| Preservation of model conviction | 6 | 1 | 7 | 7 | All 14 proposed ratings survive. |
| Readability and analytical structure | 8 | 2 | 4 | 5 | Commentary is more direct, but the assembled document remains excessive. |
| Signal relative to volume | 8 | 3 | 2 | 2 | 18,677 words, longer than the original new memo. |
| Machine-usable monitoring | 2 | 6 | 2 | 2 | 12 notes, none meeting the evaluator's required fields. |
| Recovery and inspectability | 2 | 7 | 6 | 5 | Work retained, but context and format failures required local intervention. |
| Diversity of model judgment | 7 | 5 | 5 | 5 | Different initial views; Opus controls both reconciliation and prose. |
| Future performance evaluation readiness | 1 | 5 | 2 | 2 | No decision timestamp or dated forecasts in the required contracts. |

There is no averaged grand score: a correct ledger does not cancel an incorrect investment argument, and better prose does not repair broken source links.

## Measured Results

| Measure | Original new run | Ling + Opus replay |
| --- | ---: | ---: |
| Independent / current-aware / final targets | 11 / 8 / 12 | 12 / 13 / 14 |
| Final model target total | 100% | 100% |
| Assembled target total | 121% | 100% |
| Assembled rows, including exits/current-only rows | 25 | 16 |
| Memo words | 15,355 | 18,677 |
| Second-level sections | 15 | 15 |
| Frozen evidence facts | 553 | 553 |
| Structured final fact references | 69 | 63 |
| Structured references missing from final ledger | 16 | 19 |
| Resolving references without source-review checks | 7 | 11 |
| Missing references including inline IDs | 21 | 22 |
| Valid typed monitoring conditions | 0 | 0 |
| Dated forecasts / decision timestamp | 0 / absent | 0 / absent |

All 19 missing structured references in the replay existed in the initial evidence packet. They are **not newly invented fact IDs**: merging research changed evidence identity without updating every downstream reference. The extra unchecked citations partly reflect this replay's deliberate reuse of the original source checks rather than rechecking newly selected claims.

The replay retains four STRONG, five MEDIUM and five WEAK ratings on its 14 positive targets; two exit rows are UNASSESSED. Its recorded one-way turnover from the current book is 48.93%, before costs. A balanced capital ledger is not a trading instruction: mandate, tax, instrument selection, currency and implementation remain unresolved.

## What The Starting Views Actually Say

Ling's ideal is genuinely different: 12 exposures totalling 100%, including 28% equities, 35% bonds, 18% cash/bills, 4% non-energy commodities, 4% gold, 2% FX and 9% alternatives/hedges. Its equity sector sleeve is broad rather than separately funded by sector. It holds 5% long nominal government bonds and 2% high-yield credit despite describing them as underweights.

Opus's current-aware proposal has 13 exposures totalling 100%: 72% equities, 12% TIPS, 10% short government bonds and 6% cash. It assesses all 12 existing sleeves, proposing exits from copper and lithium while retaining a materially larger mining and healthcare allocation than Ling's independent view.

Those differences establish that the workflow does not merely reproduce the number of existing categories. They do not, on their own, establish which view is financially better.

### Where The Final Allocation Lands

| Exposure | Opus current-aware | Mixed final |
| --- | ---: | ---: |
| Energy producers | 18% | 16% |
| Gold miners | 10% | 9% |
| Silver miners | 4% | 3% |
| Uranium miners | 3% | 3% |
| Pharma / biotech | 12% | 12% |
| Healthcare services | 4% | 3% |
| TIPS | 12% | 12% |
| Short government bonds | 10% | 10% |
| Long nominal government bonds | 0% | 4% |
| Broad equity | 10% | 10% |
| Semiconductors | 4% | 4% |
| Staples | 4% | 3% |
| Defence | 3% | 2% |
| Cash | 6% | 9% |
| **Total** | **100%** | **100%** |

The final has 65% equities, 26% government bonds and 9% cash. It reallocates only seven percentage points of capital relative to Opus's current-aware proposal, measured as half the sum of absolute weight changes. Final weights are identical to the provisional reconciliation despite the intervening investment-case work.

Compared with the original same-day final, energy doubles from 8% to 16%, standalone healthcare rises from 2% to 15%, cash falls from 20% to 9%, and bullion gives way to mining equities. The original is approximately 54% equity versus 65% here. These are analytical preferences applied to the same frozen evidence, not new market discoveries. Some sleeves differ economically and should not be forced into one-to-one equivalence.

The original DeepSeek-led reconciliation stayed close to DeepSeek's ideal; this Opus-led reconciliation stays close to Opus's current-aware view. Model names remain visible in both review and reconciliation inputs. **That pattern warrants a model-blind synthesis test; it does not prove self-favouritism.** Different roles and objections could justify different outcomes, but neither result provides sufficiently reliable attribution to settle the question.

The research packet itself already supplies the 53% Q2 / 25% Q3 / 12% Q1 / 10% Q4 regime distribution, a preferred market interpretation and asset implications. Both models repeat much of that framing. **Holdings independence is real; agreement on the regime is not independent corroboration.** This replay tests interpretation of an already interpreted research packet, not two independent macro investigations.

## Financial Findings

### Useful Challenges

Opus makes the concentration-versus-thesis distinction more explicit. A plausible energy view does not by itself underwrite a 50.7% energy-producer weight. It also challenges whether defence diversifies energy when de-escalation can hurt both, and whether healthcare sub-sectors diversify one another when they share policy risks.

Its strongest criticism of Ling is the 9% alternatives/convex-hedge sleeve. Evidence that tail risk exists does not establish which hedge to buy, its premium or capital requirement, expected carry, payoff, capacity, counterparty exposure or effectiveness. An allocation to an undefined hedge is not a completed risk-management argument.

Opus also identifies the real-duration risk in long TIPS and questions the assumption that an oil shock must push long-run inflation compensation higher. That is a useful improvement on treating inflation-linked bonds as universally protective. Inflation indexation and secondary-market interest-rate exposure are different properties. [TreasuryDirect](https://www.treasurydirect.gov/indiv/research/indepth/tips/res_tips_rates.htm), [SEC Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds).

### Errors The Reviews Did Not Reliably Correct

1. **Misreading the independent portfolio.** Opus repeatedly says neither baseline holds long nominal duration. Ling explicitly holds 5%. The initial reconciliation then describes its own 4% allocation as a departure from both baselines, even while its structured comparison records the ideal's 5%. This is an internal contradiction, not a disagreement about the merits of duration.

2. **Cheapness inferred from poor performance.** The current-aware answer calls healthcare cheap because earnings declined and flows lagged, without a valuation bridge. Opus's defensive review correctly flags the missing valuation evidence, but Ling's exposure review repeats the cheapness claim. Lower earnings or weaker flows do not establish a lower price relative to sustainable earnings.

3. **A sector label treated as a risk model.** Pharma/biotech is repeatedly described as defensive earnings, and healthcare services as utilisation/reimbursement-driven diversification, without position-level earnings, development-stage or cash-flow data. Such characteristics might describe some holdings; they have not been established for this portfolio.

4. **Nominal bills conflated with contractual real yield.** Opus groups bills with TIPS as providing a contractual 2.4%-3.0% real return. Nominal bills do not contractually index principal to inflation. Comparing short bill yields with long breakevens does not lock in that real return. Breakevens also include inflation and liquidity risk premia, rather than measuring only expected inflation. [TreasuryDirect](https://www.treasurydirect.gov/indiv/research/indepth/tips/res_tips_rates.htm), [St. Louis Fed](https://www.stlouisfed.org/on-the-economy/2022/jul/fomc-actions-recent-movements-inflation-expectations).

5. **Commodity shock treated as an equity shock.** The current-aware answer and initial reconciliation multiply an oil-price drawdown directly by the producer-equity weight, despite discussing operating and financial leverage. That arithmetic needs an assumed equity sensitivity or an explicitly stated equity-price shock; it is not a demonstrated portfolio scenario.

6. **Small position equals bad position.** Copper and lithium are exited partly because they are small and under-researched. No minimum position-size or monitoring-cost policy was supplied. Missing evidence should qualify the thesis or prompt a material research question, not automatically become evidence for an exit. Opus also calls the book twelve sub-1% mining positions, then elsewhere describes twelve sleeves with four below 0.65% as a ten-position portfolio. The input has 12 held sleeves; only four are below 1%.

7. **Benchmark mismatch in Ling's commodity case.** Ling supports a non-energy allocation with aggregate GSCI momentum. The broad GSCI contains energy as well as other sectors; its return does not isolate a non-energy opportunity. This weakness also appears in the earlier same-day memo. [S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/commodities/sp-gsci/).

8. **An over-sensitive funding trigger.** Ling's ideal treats SOFR exceeding ON RRP as a stress trigger. ON RRP is designed to provide a floor under money-market rates; a higher private-market rate alone does not establish stress. The trigger needs an economically meaningful spread, persistence and context. [Federal Reserve](https://www.federalreserve.gov/monetarypolicy/iorb-faqs.htm).

9. **Cash-return arithmetic fails in the finished commentary.** The cash paragraph cites bills at 4.07% and effective fed funds at 3.63%, then calls the return slightly negative against headline CPI of 3.4%. Both quoted nominal rates exceed 3.4%. This simple current-rate comparison is not a guaranteed future real return, but the paragraph is inconsistent even on its own terms.

The final writer does not reliably act as a corrective layer. It repeats the false claim that neither baseline holds long duration, repeats the commodity-to-equity shock arithmetic, describes twenty positions where the input has twelve, and retains the small-position exit argument. It usefully concedes that healthcare cheapness lacks valuation evidence, but still rests part of the thesis on it. The writing is more assured than the verification warrants.

These findings are about the saved analytical arguments. Quoted market levels are inputs to the experiment, not independently re-certified current market data. External references above explain instrument mechanics and were not added to the models' frozen research.

## Software Effects On The Comparison

### Correct Economic References Rejected By Name Matching

The first Opus reconciliation was complete JSON, not a truncated response. The validator rejected economically meaningful links because its identifiers differed from Ling's labels. Examples include the ideal's 12% TIPS, 5% long nominal bonds, 10% broad equity and 18% cash/bills. It demanded null references instead.

Some comparisons still require human care: the independent 2-5 year government sleeve and the reconciled bills-to-2-year sleeve are related, not identical instruments. A proper relationship should say so. Replacing every unmatched label with null neither proves nor disproves the economic comparison.

In the accepted final, 19 of 22 rows have null ideal references. Only IG credit, HY credit and the alternatives sleeve retain numeric ideal references. Some absent links are legitimate because the ideal has no matching exposure; others erase clear comparisons such as the ideal's 5% long nominal allocation. Nine current-aware references are also null, including rows for absent exposures. Null alone is not proof of a defect; the documented economically matching cases establish it.

The rejected full response remains in the audit records. The production workflow's repair request was left intact for comparability. This repeats the earlier same-day audit's finding: **the application can erase useful comparison values and pay to regenerate the whole answer because it lacks an explicit exposure relationship.** This is not evidence that Opus invented the corresponding baseline weights.

### Model Context And Response Limits

Ling's provider exposes a 262,144-token total context window and a 32,768-token maximum response. Its initial specialist-review input used 257,816 tokens, leaving only about 4,300 response tokens. Increasing the requested output cap could not fix a full context window. Three truncated responses were retained.

The replay helper then applied compact JSON serialization to Ling's user messages, with a decoded-value equality assertion. No field, value, source, fact or instruction was removed. The same review input fell to 234,698 tokens. Its first 10k response still truncated at the output limit; the normal 20k retry completed with 6,415 output tokens, including reasoning.

Opus's defensive review also reached its initial 10k response limit and completed on a 20k retry. Initial allocation budgets of 32k do not mean every reviewer and writer starts at 32k.

The failed and successful responses are all retained. Recovery reused the completed ideal, current-aware assessment and defensive review. The process was interrupted only after the Opus review was durably checkpointed and before the next paid analytical dispatch.

The later detail requests were larger still: three compacted requests exceeded Ling's total context window and the fourth left only about 489 response tokens. A second recovery encoded the fact objects as a lossless table: common field names become headers, with every original value and per-row extra field retained. A whole-prompt decode check proved equality. In the tested batch this retained all 553 facts while reducing compact input from 837,879 to 709,515 bytes. The recovered requests used about 233k-234k reported input tokens and returned substantive answers.

This is a transport-format difference from the original run and must be included among the experiment's limitations. No facts were selected out to fit the smaller model.

The second recovery preserved the first completed final recommendation, but its writer request had already started when the process was interrupted. That writer has no returned response or usage receipt. Any charge for it is unknown and is not included in the sum of reported response costs.

### Detail Work Lost Between Batches

All four detail batches were attempted again after the capacity repair. Across their raw structured replies, Ling supplied investment-case text for **all 14** proposed exposures. The assembled detail packet carries that text for **only nine**. Broad equity, cash, long nominal government bonds, semiconductors and staples have case text elsewhere in the raw replies but blank normalized fields.

There are two separate failures. Ling sometimes reviewed the entire portfolio instead of its four assigned exposures, and one answer used a different response structure. The application then filtered otherwise usable, exactly identified details from other batches instead of recovering the missing cases from the already returned work. Raw replies remain inspectable; the missing fields are not invented or silently treated as verified.

Consequently, final synthesis does not receive every piece of Ling's returned detail work. This materially limits a claim that the assembled memo measures Ling's full contribution. It also identifies a narrow repair: retain relevant returned case fields by proposal identifier with provenance and explicit conflict handling, rather than making each batch an isolated owner of its assigned rows. This does not require another research call or a new analytical agent.

### What This Test Does Not Repair

The same application ledger, citation identity, monitoring and rendering machinery remains in use. This time the ledger totals 100% because the final targets line up with the existing identifiers. That does not repair the duplication defect exposed by the original run's freely named exposures.

The 12 monitoring notes still omit the age field required by the evaluator, and the final artifact has neither a decision timestamp nor dated forecasts. The source-reference failures also remain, as measured above. No UI redesign or application-code repair was bundled into this experiment.

The saved supplementary research is introduced at the original stage. New questions raised by this model combination do not receive fresh searches or new source checks. Those gaps remain visible rather than being silently resolved with later information.

### Commentary Recovered Without Another Model Call

Opus returned complete commentary as Markdown with the exact three requested section names, but the application demanded a JSON object and rejected it. Its next request received HTTP 402 with reason `in_flight_budget_exhausted`. That provider response is not proof the account balance was zero. The application's generic funding message lost that distinction.

The local finalizer split the existing sections and paragraphs into the required fields, matched exact displayed exposure names to their saved identifiers, and proved that reconstructing the Markdown reproduced the original text. No financial prose, numbers or conclusions were rewritten. The original failed receipt remains, with a separate format-recovery record and warning. Finalization then reused every analytical checkpoint with model dispatch disabled.

The saved status is **Analysis complete with limitations**. This means the output was retained and assembled, not that its financial claims passed this audit.

## Runtime And Cost

| Measure | Replay |
| --- | --- |
| Analytical workflow | 11 logical steps, counting the four detail batches separately |
| Actual model dispatches | 33: 21 Ling, 12 Opus |
| Returned transport records | 32; one earlier interrupted writer has no returned response |
| Retained request receipts used in cost sum | 31; the HTTP 402 retry exists in transport records, not a normal stage receipt |
| Reported OpenRouter charges | **US$25.347115**; Ling's returned token charges were zero |
| First dispatch to completed local artifact | About 69m29s, including funding pauses, failed attempts and recovery |
| New retrieval or extraction charges | None; frozen research reused |

This is a recovery-inclusive experimental subtotal, not a clean-run price or the total account bill. It excludes any charge for the interrupted writer whose response was never received. The earlier run's audited reported OpenRouter subtotal was $3.059837, excluding external providers and its lost writer response; those are not like-for-like all-in costs.

Three whole-response repairs caused by exact-name comparison validation cost an additional **$8.82**. The three substantive responses they replaced had already cost **$8.48** and remain retained. A second full final synthesis was also necessary in this experiment after recovering the oversized detail inputs. These mechanics explain much of the bill; it would be misleading to attribute it solely to a more expensive model or assume every normal run costs this amount.

The checkpoint reports 12 completed input versions because it retains both versions of final synthesis. That is not 12 independent analysts. Likewise, 33 dispatches include retries and recovery, not 33 distinct investment perspectives.

## Recommendation

1. Keep the independent ideal and separately formed current assessment. This experiment confirms they can produce materially different views from identical evidence.
2. Repair economic exposure links, stable fact identity and cross-batch detail recovery before another expensive model comparison. Those failures affect the comparison itself.
3. Require the reconciler to quote the actual saved baseline weights and distinguish a commodity-price scenario from an equity-return scenario. Check these targeted claims; do not add another full research council.
4. Retain completed Markdown or partially structured answers with provenance instead of paying to rewrite finished analysis for format alone.
5. Run the next synthesis on model-blind versions of the same retained proposals. This is a much narrower test of reconciliation than repeating discovery and extraction.
6. Restore the existing monitoring and evaluation contracts. Edit the memo for readers later, within the current layout, as requested.

Ling is worth further testing on compact, clearly scoped financial questions. Opus's strongest demonstrated contribution here is adversarial explanation, particularly the refusal to fund an undefined hedge. Neither result justifies accepting the final recommendation without correcting the specific analytical and integration defects above.

## Verification

The read-only browser check passed at 1440px and 390px in light and dark themes: the memo loaded, both portfolio tables rendered, the sources appendix stayed collapsed, and the memo workspace had no horizontal overflow or JavaScript page errors. The check did not modify application code or start another run. Existing navigation and editorial density were not redesigned.

## Reproduction

- Runner: `outputs/audits/portfolio-independent-uplift/mixed_run.py`
- Artifact: `outputs/audits/portfolio-independent-uplift/live/mixed-ling-opus.json`
- Checkpoint: `outputs/audits/portfolio-independent-uplift/live/mixed-ling-opus.checkpoint.json`
- Transport responses and settings: `outputs/audits/portfolio-independent-uplift/mixed/requests/`
- Read-only metrics utility: `outputs/audits/portfolio-independent-uplift/compare_mixed.py`
- Read-only browser check: `outputs/audits/portfolio-independent-uplift/verify_mixed.mjs`
- Offline commentary finalizer: `outputs/audits/portfolio-independent-uplift/finalize_mixed.py`
- Format-only recovery and round-trip verification: `outputs/audits/portfolio-independent-uplift/mixed/commentary-format-recovery.json`
- Measurements: `outputs/audits/portfolio-independent-uplift/mixed/comparison.json`
- Browser results and screenshots: `outputs/audits/portfolio-independent-uplift/mixed/browser/`
- Earlier scorecard: [Three-generation comparison](portfolio-three-generation-comparison-20260918.md)
