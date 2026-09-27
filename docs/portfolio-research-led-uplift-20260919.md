# Research-led portfolio analysis uplift

Date: 19 September 2026

Status: **Deployed as workflow version 4 in Fly release 353 on 19 September 2026. Paid analytical comparison remains outstanding.**

The original findings and acceptance criteria below are retained as the audit baseline.
Implementation details and verification are recorded in section 11.

## 1. Decision

Make substantive research precede substantive investment judgments. Parallel should investigate the economic questions on which a recommendation depends, not merely supply a general news digest and answer optional questions after the models have already assigned ratings.

Keep the independent ideal portfolio, the separate current-portfolio assessment, explicit critique of user plays, existing model assignments, paid-task recovery and preservation of partial output. Do not add another standing council of reviewers. Change what the existing process researches, when it researches it, and how conclusions depend on that evidence.

This plan incorporates the outstanding issues in the [19 September comparison audit](portfolio-remediation-comparison-20260919.md). It supersedes the late-follow-up research sequencing in the [independent-memo uplift](portfolio-independent-memo-uplift.md), not its independence requirement. The [source-retrieval notes](portfolio-source-retrieval.md) also need updating during implementation: their three-follow-up description does not match the six requests selected in this run.

## 2. What happened in the oil assessment

Audited artifact: `portfolio_positioning_job_portfolio_remediation_comparison_20260919_030458.json`. Local snapshot: `outputs/audits/portfolio-remediation-review-20260919/latest.json`.

### The judgment's origin

The oil-producer **4/10 originated in the Opus defensive review**, not the independent DeepSeek analysis. DeepSeek subsequently carried the assessment into the final memo. Ling's stored oil component was unassessed. Neither reasoning model performed internet research in those calls; they received an evidence packet.

There were sources, but they did not substantiate the scope or confidence of the conclusion:

| Memo premise | Saved provenance | Problem |
| --- | --- | --- |
| Oil prices around $100 | Investrade daily settlements; World Bank quarterly averages | Establishes prices, not physical scarcity, forward returns or producer valuation. Different periods need different interpretations. |
| Citi forecasts Brent at $86 in Q3 | Goodreturns quotes a bank forecast | Original forecast date and assumptions are not established. A quarterly average is not a forecast of a 15-18% decline from a late-quarter spot price. |
| Saudi export capacity restoration | ICRYPEX commentary describes efforts to restore capacity and reduced immediate anxiety | The review strengthens efforts and sentiment into a physical restoration claim without measured exports or restored throughput. |
| Gasoline demand is structurally weak | Schwab market commentary on US gasoline demand and hybrid sales | Does not establish global crude balances or European diesel availability. Supply-constrained consumption, cyclical weakness and structural substitution need separating. |
| Oil fell below $100 | News text extracted from Trading Economics' US government-bond-yield page | A headline on an unrelated page is not a sufficiently specified benchmark, contract and observation. |
| Oil producers may be overpriced | Ten-day price range and the cited bank forecast | Neither establishes equity valuation, forward earnings, operating exposure or how much disruption is already discounted. |

The original Opus action explicitly identified concentration, rather than investment merit, as the binding constraint. The shortened final assessment did not preserve that distinction adequately. A 33.7% allocation can warrant a concentration discussion even if the sector thesis is strong. It must not mechanically make that thesis a 4/10.

### Research existed, but it was misdirected and too late

The three initial Parallel ultra4x tasks were broad macro, sector-leadership and coverage prompts, each returning five selected sources. Perplexity also researched each lane. Parallel received the short lane focus, not the richer research query. Five sources covering an entire macro universe is not equivalent to five sources answering a focused market question.

The coverage prompt referred to available portfolio asset classes without supplying a universe. Parallel substituted **Aware Super's diversified investment universe**. That is not coverage of this portfolio, nor a genuinely open-ended opportunity search. All three initial Parallel outputs nevertheless called their questions answered.

The final 46-entry source packet contains **no IEA or EIA URLs**. The models had broad prices and commentary, but no adequate oil physical-balance dossier. A fourth cross-asset-risk specification exists in code but was outside the three selected lanes. Merely switching on another broad lane would not fix the underlying question design.

Only after ideal/current allocations, play reviews and a provisional comparison did the application request focused research. Its oil question asked whether supply would normalize or escalate, rather than requesting the measurable inputs needed to assess those scenarios. All six supplementary Parallel calls returned HTTP 402 insufficient credit. Three questions overlapped on uranium; none targeted fertiliser. The memo correctly survived, but the affected judgments were not sufficiently reconsidered. Progress counted completed processing despite failed retrieval.

### Material information was available before the run

The **11 September IEA report** describes more than 10 million barrels/day of Gulf production shut in, a 507-million-barrel inventory draw since February, and severe refined-product tightness affecting Europe as well as other regions. It also projects demand contraction, which belongs in the countercase rather than being ignored. These are material physical-market facts missing from the run's packet. [IEA September report](https://www.iea.org/reports/oil-market-report-september-2026)

The **18 September IEA commentary** separates headline lost Hormuz flows from the smaller net deficit after supply and demand offsets. It also describes renewed damage to bypass infrastructure. The model needed this distinction, not an assumption that restoration headlines settled the balance. [IEA supply-shortfall analysis](https://www.iea.org/commentaries/oil-markets-strain-to-plug-the-gap-left-by-middle-east-supply-shortfall)

A credible countercase was available too: **EIA's 9 September outlook**, completed on 3 September, assumes gradually recovering regional flows and forecasts lower future prices, while retaining export constraints through year-end. Its forecast vintage and recovery assumptions are indispensable to interpreting it. [EIA September outlook](https://www.eia.gov/outlooks/steo/)

These sources substantiate the criticism that the memo missed the scale and mechanisms of disruption. They do **not**, by themselves, prove that every oil producer is undervalued or that an existing concentration should increase. Producer location, uninterrupted volumes, hedges, costs, taxes and valuation still determine the investment expression. The remedy must investigate these questions, not replace an unsupported bearish verdict with an automatic bullish one.

## 3. Proposed sequence

```text
Market orientation, blind to holdings and plays
    -> Identify material developments and candidate opportunities
    -> Reuse evidence; research their decisive unanswered questions
    -> Save independently researched ideal portfolio

Introduce current holdings, but not ideal weights or user plays
    -> Research material exposure-specific gaps
    -> Save separate current-portfolio assessment

Introduce user plays
    -> Establish stable play components and research their gaps
    -> Existing reviewers critique researched cases and both portfolios
    -> Resolve material new factual challenges within remaining budget

Reconcile -> validate mechanics and funding -> publish one coherent memo
```

The research scope grows when new information is legitimately introduced. This does not mean a new paid call for every phase or every asset: an adequate existing answer is reused. Independent questions within a phase run concurrently.

Market orientation discovers developments and opportunities, including ones absent from the holdings. It is not a completed sector thesis. Replace the ambiguous blind coverage audit with an open-ended search for important structural changes, transmission mechanisms and overlooked opportunities. Explicit investment constraints are allowed; a borrowed fund taxonomy is not.

Focused research should precede the ideal allocation's first substantive commitment. The models can generate hypotheses and research questions before that, but preliminary ideas must not be presented as researched ratings. New holdings or play information must never silently rewrite the saved blind baseline. A later revised view is separately labeled and traceable.

If research is unavailable, preserve the partial analysis and say which conclusions remain provisional. This is a sequencing and disclosure requirement, **not a new rule that destroys the memo when a field or source is missing**.

## 4. The reusable research contract

Extend the existing retrieval/runtime boundary with a provider-neutral question record and an evidence-backed topic brief. Portfolio analysis is the first consumer. Council and terminal analysis can subsequently use the same contract without inheriting portfolio weights, play scores or allocation assumptions. Do not migrate all applications in the first release.

### Question record

| Field | Purpose |
| --- | --- |
| Stable ID and topic | Identify the economic question independently of its phrasing. |
| Focused question | Ask for observable facts or explicitly attributed forecasts, not a generic prediction. |
| Entity, geography, period, horizon and cutoff | Prevent wrong-market answers and historical/forward-period confusion. |
| Material reason | Record which thesis, comparison or decision could change. Keep portfolio weights private to the application. |
| Known evidence and remaining gap | Reuse existing facts and specify precisely what is still missing. |
| Required answer dimensions | State the quantities, mechanisms or assumptions needed for this question. Dynamically generated, not a fixed asset allowlist. |
| Related thesis/play IDs | One answer can inform multiple decisions without repeated searches. |
| Priority, estimated cost and disposition | Explain selection, expansion, deferral and recovery. |

Send Parallel a short individual question plus concise research context: cutoff, benchmark, horizon, known observations and missing dimensions. The current adapter drops most of that context and passes only the question string. Fix the adapter; do not paste portfolio JSON or a diagnostic checklist into the search. Do not silently discard a material question merely because its wording exceeds the current 350-character filter; reformulate it and retain the original.

### Answer and source record

Return observations, attributed forecasts, contrary evidence, unresolved dimensions and a brief explanation of what the evidence establishes. Every material statement should resolve to a source excerpt and publication/observation period, or be explicitly labeled inference. Store source versions and retrieval times for mutable URLs.

Preserve Parallel's field-level research basis and confidence alongside its output. Its citation excerpts support traceability; provider confidence does not certify an economic conclusion. The [Parallel research-basis contract](https://docs.parallel.ai/task-api/guides/access-research-basis) already supplies the relevant citation structure. Reuse it rather than adding another ungrounded synthesis layer.

Source treatment must distinguish:

- Measured flows, installed capacity, announced repairs and actual restored throughput.
- Price levels, futures contracts, historical averages and dated forecasts.
- Independent corroboration from several sites repeating one original report.
- Forecast disagreements caused by different publication vintages or assumptions.
- Missing evidence from evidence that the hypothesis is false.

One authoritative report may answer several questions. Multiple sources are not a mandatory quota. Useful non-primary reporting remains admissible with attribution; a preferred-source catalog is guidance, not an allowlist that discards outside evidence.

Do not impose artificial balance. One bearish forecast does not neutralize several measured supply constraints just because the memo needs a contrary-evidence paragraph. Weight evidence by relevance, reliability, magnitude, timing and assumptions. Conversely, a large gross disruption does not establish the remaining deficit after offsets. Models may use general financial knowledge to explain mechanisms, but must not present remembered or inferred current conditions as retrieved observations.

### Evidence sufficiency

The application should track which material premises have answers, not count source IDs and infer completeness. For a claim of restored supply, a sentiment headline does not answer the throughput question. For a valuation claim, a spot price does not answer the forward earnings or discounted-price question.

Use explicit coverage states: answered, partly answered, unresolved or conflicting, each with reasons and supporting references. Coverage checking belongs in the existing structuring/review work, with deterministic checks for dates and dimensions. Do not commission another model call for each fact. Partial answers remain usable for the claims they actually support.

## 5. Oil as the first regression case

The following are example research questions, **not six compulsory additional searches**. Read and reuse a relevant report first; dispatch only the remaining material gaps.

| Focused question | What a useful answer establishes |
| --- | --- |
| How have Gulf production, Hormuz exports and bypass flows changed since the disruption? | Dated volumes, actual versus nameplate capacity, damaged assets, recovery evidence and uncertainty. |
| What is the net global balance after non-Gulf supply, demand changes and inventory releases? | Comparable periods and definitions; no double-counting lost exports, shut production or stock releases. Gross disruption is not the residual deficit. |
| Where are European crude and refined-product constraints most acute? | Crude versus diesel/gasoil, refinery runs, product inventories, trade flows, cracks and freight; physical transmission rather than a generic geopolitical label. |
| What restoration evidence would reverse the scarcity case, and over what horizon? | Repair milestones, sustained throughput, shipping availability and plausible offsets; forecasts tied to assumptions rather than asserted as facts. |
| What do the forward curve and dated forecasts imply, and how do they differ? | Contract maturity, benchmark, forecast publication date and averaging period. No quarter-average versus daily-spot valuation shortcut. |
| Which producer exposures benefit after operating and valuation effects? | Geography, realized volumes, hedges, costs, fiscal take, capital returns and scenario cash flows; separate upstream, refining and services. |

A question can require historical data, present conditions and conditional outlooks. Future research means investigating drivers, capacity, contracts, projects, inventories, expectations and competing assumptions. Parallel cannot retrieve a future outcome as an observed fact.

The resulting analysis should explain the chain **disruption -> net availability -> prices/margins -> producer earnings -> valuation -> portfolio decision**. Each unsupported link must be visible. A well-supported scarcity case can coexist with a decision to trim an oversized position; those are different conclusions.

Generalize the same approach to other topics. Fertiliser requires feedstock costs, nitrogen/phosphate/potash distinctions, supply interruptions and farmer affordability. Miners require commodity exposure, grades, production, costs, capex and valuation, not just bullion prices. Uranium requires contracts, inventories, restarts and fuel-cycle constraints. Bonds require maturity, nominal/real yields, inflation compensation and conditional price effects. Other sectors need their own economic drivers. These are examples, not a closed template catalogue.

## 6. Workload, funding and recovery

Spend research effort according to material uncertainty, not the number of holdings or how many reviewers repeat a question.

1. Search the saved evidence by subject, measure, geography, period and source version before buying retrieval.
2. Cluster economic duplicates, retaining distinct subquestions. Three phrasings of uranium supply/contract economics should share a research task; materially different periods must not be merged blindly.
3. Prioritize potential decision impact, uncertainty, evidence freshness and distinct thesis coverage. Zero current weight must not make a new opportunity or submitted play ineligible.
4. Start with five distinct relevant source results for a focused question. Select by coverage and authority, not merely the first five URLs in a response. Retain the full raw response. Expand only an identified unresolved gap.
5. Do not exclude an entire previously seen URL when only an irrelevant fragment was extracted. Reuse the saved source where adequate; fetch the missing section or changed version when necessary.
6. Share one run-level research budget across orientation, focused research and later challenges. Show estimates, reservations, actual charges where known and deferred questions. Preserve capacity for a material challenge rather than reserving the entire budget for the first loosely ranked list.
7. Run independent selected questions concurrently, with one checkpoint per task. Resume paid Parallel task IDs rather than submit duplicates. Retain successful answers if extraction, another provider or synthesis fails.

Do not silently increase the research budget to finance the redesign. Reallocate the misdirected coverage and overlapping follow-up work first. If estimated cost exceeds the authorized budget, present the additional cost or a prioritized incomplete plan; do not promise comprehensive research for a fixed price regardless of scope. Keep existing providers/models unless separately authorized to change them.

Parallel funding is separate from OpenRouter funding. Add provider-specific preflight where a supported read-only account capability is available; otherwise report Parallel funding as unverified. Do not invent a balance, assume OpenRouter credit covers retrieval, or use a paid probe as if it were a free check. On a credit error, stop scheduling further known-to-fail calls to that provider, retain work and make funding-required questions resumable. Other usable research and memo production continue.

Separate request lifecycle from answer quality and run outcome. A terminated HTTP 402 request is not a successful research answer. Show question progress, active provider task, elapsed time, last checkpoint and funding status. For this run, supplementary progress should have said **0 of 6 questions researched; Parallel credit required**, not implied six research successes. Receipts can still record all six processed failures.

No new output truncation or lower token ceilings. Reduce duplicated work and repeated prose, not the amount of reasoning a provider is allowed to return. Retry only the failed or materially affected work, with visible cause and cost.

## 7. Close the other audit findings

| Issue | Required change | Acceptance example |
| --- | --- | --- |
| Merit confused with allocation size | Separate thesis merit /10, evidence confidence, portfolio fit and proposed action. Explain the rating without mechanical weights. | Changing current oil weight alone changes fit/action, not the underlying research-based thesis score. Unresearched is not 4/10 by default. |
| Broken play component identity | Establish a canonical component inventory once, after the blind/current baselines and before research/review. Preserve original text and economic meaning; reviewers use stable IDs. Do not identify components solely by a shared quote. | The five-commodity sentence produces five identifiable legs. The saved uranium analysis cannot be relabeled fertiliser or overwrite a sibling. |
| User intent altered | Store expression and direction separately from comparison preference. | Gold preferred to bonds remains a relative hedge choice, not an invented short trade. |
| Financial reasoning mistakes | Validate instrument-specific mechanics and comparisons; use targeted review of material conditional claims. | Falling short yields do not mechanically cause short-bond price losses; cash 11% is not greater than a 14% sleeve. |
| Invalid yield decompositions | Distinguish price return, carry, reinvestment, real yield, breakeven and term premium. | A policy-to-bond yield spread is not a measured term premium. Falling breakevens alone do not prove an absolute TIPS loss. |
| Valid calculations rejected | Replace identical-field checks with operation-aware compatibility: curve spread, time change, same-maturity nominal/real comparison and explicitly defined return comparisons. | Same-date 5.01% ten-year minus 4.76% two-year yields returns 25bp; a time-change operation permits different dates. Incompatible currencies/benchmarks still produce a qualified result. |
| Missing metadata treated as falsehood | Keep value, observation, vintage and attribution assessments separate. | A supported numerical observation with unknown publication metadata remains useful, with that uncertainty disclosed. |
| Weak instrument generalizations | Distinguish bullion from miners, nominal from inflation-linked bonds, producers from commodities, and established pharma from development biotech. | No claim that bullion and miners have identical sensitivity; no invented holding-level cash-flow profile when only a broad sleeve is supplied. |
| Corrections do not propagate | Publish all final sections from one authoritative decision record. Material findings link to affected claims, calculations, scenarios and sizing. | A correction updates every dependent final statement; unchanged weights receive an economic explanation rather than automatic approval. |
| Unfunded smaller-change alternative | Materialize unchanged holdings explicitly, then calculate cash, trades and totals. Compare hold, smaller-change and full proposal using declared assumptions. | The alternative totals 100%; missing residual weights cannot hide behind hold-the-rest prose. Costs stay unknown when not supplied. |
| Conditional ideas appear executable | Distinguish researched strategic destination from supported action now. | A uranium increase conditional on contract evidence is not rendered as an unconditional instruction. |
| Nonfunctional monitoring | Link each condition to an available observation source, benchmark, unit, freshness and evaluation time. Keep predictions separate from allocation intentions. | An observable trigger evaluates; unavailable data displays unknown, never silently passed. A target portfolio weight is not a market forecast. |
| Bloated memo | Restore the legacy reading order and selective tables/charts, generated from consistent decision data. Detailed research and diagnostics follow the argument. | The conclusion and allocation appear before review history; no raw fact IDs, six-decimal weights or repeated investment cases in the main narrative. |

Financial mechanics should be tested against the relevant primary definitions: [SEC bond price/yield explanation](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-86), [Federal Reserve nominal/real yield data](https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm), [New York Fed term-premium explanation](https://www.newyorkfed.org/newsevents/speeches/2023/per231116), and [Treasury TIPS mechanics](https://www.treasurydirect.gov/marketable-securities/tips/).

### Reader presentation

Use the existing reader and theme. Do not redesign the application during the research uplift.

Reading order: executive investment view; current/independent/proposed allocation comparison; consequential changes and retained convictions; play assessments; implementation alternatives and monitoring; supporting research and audit details. Preserve full raw outputs behind the existing detail surfaces.

Useful graphics include comparable allocation bars and a funded sources-and-uses view. Scenario graphics require actual comparable inputs; do not fabricate probability distributions, return estimates or risk numbers to fill space. Presentation work follows analytical correctness, with legacy artifacts used as reading-order references rather than copied financial conclusions.

## 8. Implementation boundaries and order

| Order | Existing code | Work |
| --- | --- | --- |
| 1 | `scripts/portfolio_positioning_memo.py`, `backend/portfolio_independent.py` | Move focused research before substantive judgments; preserve blinding/frozen baselines; canonicalize play components before reviewers. |
| 2 | `backend/portfolio_retrieval.py`, `backend/portfolio_evidence.py`, `backend/portfolio_judgment.py` | Question context, reusable topic answers, semantic deduplication, coverage-aware selection, source versions and material-premise checks. |
| 3 | `backend/portfolio_runtime.py`, `backend/portfolio_progress.py`, `backend/portfolio_funding.py` | Distinct retrieval/coverage outcomes, provider-specific funding visibility, cost reservations and checkpoint-compatible recovery. |
| 4 | `backend/portfolio_judgment.py`, `backend/portfolio_exposures.py` | Operation-aware calculations, decision dependencies, funded alternatives and final consistency. |
| 5 | `backend/portfolio_memo.py` and existing portfolio reader | Authoritative final narrative, concise legacy hierarchy, reader-friendly play assessments and research appendix. |

Keep the provider adapter, runtime, source store and role configuration. Introduce a small shared research contract only where needed to avoid duplicating these concerns across applications. Do not create a separate orchestration framework or per-sector agent fleet.

Version new question records and workflow checkpoints. Read old artifacts unchanged; do not backfill a completed 19 September judgment as though missing research had existed at the time. Reuse compatible paid outputs when resuming, but invalidate dependent answers when question meaning, cutoff, evidence or analysis contract changes. Preserve the superseded versions for comparison.

## 9. Verification and release criteria

These are tests for releasing the implementation, not conditions for throwing away a user's partial memo.

### Deterministic regression fixtures

1. Freeze this run's portfolio, plays, cutoff, routes and available evidence. Assert no holdings, plays or borrowed fund taxonomy reaches the blind research/allocator inputs.
2. The broad packet fails to establish oil supply normalization. Missing decisive evidence becomes a focused research need, not an automatic bearish rating.
3. Add the pre-cutoff IEA/EIA material. The answer must address physical disruption, offsets, product constraints and forecast vintages. Do not assert an expected bullish score or target weight.
4. Alter holdings while keeping research fixed. Thesis merit remains independent of concentration; portfolio fit changes appropriately.
5. Rephrase the uranium questions. Duplicate economic work is reused while genuinely distinct contract/restart subquestions remain visible. Fertiliser is not silently dropped.
6. Simulate Parallel 402, one failed extraction and a restart after paid submission. Successful research survives, failed questions remain explicit, and paid tasks are not duplicated.
7. Test five play legs, shared source spans and relative hedge preferences. No duplicate fertiliser component, cross-component overwrite or invented short direction.
8. Cover curve-spread/time-change arithmetic, incompatible measurements, bond/TIPS conditional mechanics, scalar comparisons and fully funded alternatives.
9. Correct a material claim and verify all dependent final sections, scenario assumptions and sizing explanations. Unsupported details remain qualified rather than erased.
10. Render legacy and new artifacts at desktop/mobile sizes. Main conclusions precede diagnostics; no giant flattened paragraphs or repeated investment-case sections. Original saved outputs remain accessible.

### Controlled paid comparison, separately authorized

First compare old and revised synthesis using the **same frozen evidence** to isolate decision/rendering changes. Then compare broad versus question-led retrieval at the same historical cutoff, using the same portfolio, plays, models and authorized research budget. Save every input and source version. Historical availability must be demonstrable; fetching a mutable page today is not proof of its earlier contents.

Judge factual coverage of decisive premises, quality of contrary evidence, economic transmission, forecast-horizon alignment, independence, valuation support, conditionality, coherence, readability and cost. Report question counts, unique paid tasks, reuse, failures, retries, wall time and charges separately. Unknown provider charges stay unknown. More facts, sources or completed stages are not success metrics.

Release only after the main failure cases above are demonstrated resolved. A realistic target is a materially better researched argument with less repeated work and a more legible memo, not a guaranteed investment outcome or a predetermined oil view.

## 10. Audit trail

Key implementation references at the time of this audit:

- `_build_evidence_lane_specs`, `_run_research_lanes` and `_run_independent_pipeline` in `scripts/portfolio_positioning_memo.py`: broad prompts and late targeted-research ordering.
- `_trade_research_questions` and `_run_targeted_research` in the same file: exact-text deduplication, upfront budget reservation, context loss and URL exclusion.
- `ParallelSourceProvider` and `normalize_result` in `backend/portfolio_retrieval.py`: five-source selection, basis extraction and resumable task handling.
- `register_play_components` and `complete_play_assessments` in `backend/portfolio_independent.py`: quote-based component identity and reassignment of component names.
- `calculate_financial_claims`, `measurement_issues` and `disposition_issues` in `backend/portfolio_judgment.py`: over-literal compatibility and incomplete review closure.
- The local audit artifact's `analytical_reviews`, `play_assessments`, `evidence_runs`, `evidence_brief.source_packet`, `targeted_research` and `stage_receipts`: exact model outputs, sources and provider failures.

Oil provenance fact IDs: `fact_ea9c5fb45fd64f44b9ac`, `fact_a2065895feceab5b1f37`, `fact_6b8a0b0ef830cf211d58`, `fact_ec404aa567468971fe49`, `fact_92a833656a3abcf16e6c`, `fact_b862742eb99b0b9084b7`. The first four are linked by the final oil component; the original Opus component additionally links the final two.

The original audit used saved artifacts, source code and public primary-source checks. The subsequent implementation and deployment are recorded below; no paid analysis was started during this rollout.

## 11. Local implementation and verification

### Implemented

- New `backend/portfolio_research.py` owns the provider-neutral question contract,
  economic identity, per-dimension answer coverage and affected-decision qualifications.
  Existing source excerpts and exact observations remain necessary; a fact ID or
  provider's "answered" flag alone is not sufficient coverage.
- `_run_independent_pipeline` now sequences orientation, independent focused research,
  saved ideal, current-exposure research, saved current assessment, canonical play
  inventory and play research, then reviews/reconciliation. Later challenges reuse the
  same contract. Existing role models and blind-baseline boundaries are preserved.
- Parallel receives concise economic context, not portfolio JSON. Selection favours
  uncovered answer dimensions; full provider research basis stays in the raw receipt.
  Semantic grouping uses planner-supplied canonical economic keys, not embeddings or
  a claim that arbitrary paraphrases can be deterministically understood.
- Discovery has durable shared reservations, per-phase allowances, explicit deferrals,
  paid-task reuse with zero fresh allowance and a 402 circuit breaker. Existing
  citation extraction is still batched and charged separately. Parallel credit remains
  unverified without its separate Account API OAuth; no paid credit probe is used.
- Play components are frozen by economic identity and direction before reviewers.
  Shared source sentences cannot overwrite siblings. Merit, evidence confidence,
  portfolio fit and action have separate fields. Unresolved central research retains
  the original judgment in the artifact and presents the affected leg as unassessed.
- Curve/time/revision/breakeven calculations use operation-specific compatibility.
  Dated source-checked observations remain useful when publication metadata is unknown;
  contradicted observations and after-cutoff sources do not gain supported status.
- Reviewed text corrections are retained rather than stripped and regenerated.
  Material decision changes invalidate affected details. A conditional final review
  checks newly generated prose; further unresolved decision concerns remain visible
  instead of opening an unlimited loop. Final publication uses settled target cases,
  preserving original baselines and superseded detail records separately.
- Explicit hold-the-rest alternatives are materialized before funding arithmetic.
  Monitoring can use matching dated observed facts; allocation intentions are not
  market forecasts. Missing or stale observations remain unknown.
- Workflow-v4 presentation leads with the executive view and current/ideal/proposed
  allocation table. It separates merit from portfolio action, limits displayed weight
  precision and puts supporting research and sources in collapsed sections at the end.
  Historical memo rendering and both themes are retained; no site redesign or new
  speculative scenario graphics were introduced.
- Progress distinguishes successful retrieval, failed requests and answered/open
  questions. Checkpoint counts exclude cached failures. Funding estimates include
  question-planning calls and the conditional final consistency pass.
- Reassessment recognises both v3 and v4 independent-workflow checkpoints. Saved
  company evidence and research context survive reassessment; explicit baseline
  preservation remains supported without rewriting the source artifact.

### Verification

- Full offline unit suite: **456 passed**, with five existing SWIG deprecation warnings.
- Includes paid-task resume without duplicate POST despite an exhausted allowance,
  Parallel 402 and later funded resume, extraction failure with sources retained,
  answer-coverage checks, cutoff rejection, shared-sentence play identity, corrected
  investment-case preservation, typed arithmetic, explicit alternative funding,
  monitoring inputs, phase ordering and identical-request checkpoint reuse.
- Frontend production build and lint of the changed components pass. Vite reports
  the existing large-bundle warning; lint reports stale baseline-browser data.
- Browser checks use saved artifacts and mocked GET endpoints only. They test the
  new collapsed appendix and responsive table in both themes at 1440, 768 and 390px,
  the historical independent reader, and progress/reconnect/interruption states.
  The saved-artifact presentation fixture has 4,341 main-body words with the appendix
  collapsed. These are presentation fixtures, not new model analyses.

### Remaining evaluation and limitations

The separately authorized paid comparison in section 9 has **not** been performed.
In particular, improved live IEA/EIA coverage, forecast-assumption interpretation,
economic judgment and merit-versus-weight invariance remain evaluation requirements,
not claims established by mocked tests. No bullish oil verdict is hardcoded.

Dimension coverage validates reference integrity and known source-review failures;
economic entailment and interpretation are still model-reviewed, not mechanically
proven. Bond/TIPS and valuation reasoning receive explicit targeted financial review;
the program does not pretend to formally verify arbitrary English financial claims.
Research can remain incomplete within the unchanged budget. Those gaps qualify the
affected decisions while preserving the memo and all successful work.

Compare old/new synthesis on frozen evidence, then compare question-led retrieval
using an explicitly authorized budget. Retain model responses, original sources,
charges when reported and visual QA. The user explicitly requested deployment before
this comparison; deployment is not evidence that the financial-quality criteria passed.

## 12. Production deployment

- Application: `llm-council-analysis`, Fly release **353**, 19 September 2026.
- Image: `deployment-01M2WCCBEW1C3HWZ80HZQHJM1P`.
- Image digest: `sha256:42fdac3f1b0c0efce3e713e234432a12324b3ae2e9c6b81e10152528f5780a43`.
- Fly health check and public `/readyz` passed; the deployed frontend asset returned HTTP 200.
- Live `PortfolioRuntime` defaults to workflow v4. SHA-256 checks for 16 changed
  backend and pipeline files matched the local deployment source, including the
  v4 reassessment compatibility fix.
- All effective model routes and the persistent routing-file hash were unchanged.
  Parallel remains `ultra4x`; DeepSeek, Ling and Opus role assignments are preserved.
- Authenticated saved-run listing and the previous remediation memo reader passed.
  Existing artifacts keep their recorded workflow version; they were not regenerated.
- No queued or running analysis jobs were present before or after deployment. No
  paid comparison or new portfolio analysis was started.
