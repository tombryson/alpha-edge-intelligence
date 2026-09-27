# Portfolio model benchmark results

23 September 2026. Completed: six models, two historical cases, 12 full decision
notes. Production configuration and the active production memo were not changed.

## Decision

**GPT-6 Sol Pro had the strongest answers in this test. GPT-6 Luna Pro offered the
best balance of financial quality and cost.** Sol was close to Sol Pro and faster.
DeepSeek was competent on oil but weaker on bond-return mechanics. MiMo's confident
presentation concealed several material financial and evidence errors.

For a further controlled trial, I would use Luna Pro for routine analytical work,
Sol for final judgment and memo composition, and reserve Sol Pro for genuinely
difficult decisions rather than adding another compulsory review stage. This is a
candidate configuration, not a production change or a universal model ranking.

## Scores, Cost and Time

Scores are the evaluator's weighted judgments out of 10, not calibrated financial
performance estimates. Oil and hedge cases have equal weight. Differences of a few
tenths, particularly between Sol and Sol Pro, are not statistically established.

| Exact model | Oil | Gold/bonds | Overall | Reported USD, both cases | Mean successful latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| `openai/gpt-6-sol-pro` | 8.7 | 9.0 | **8.9** | $0.15099 | 37 s |
| `openai/gpt-6-sol` | 8.4 | 8.9 | **8.6** | $0.07847 | 26 s |
| `openai/gpt-6-luna-pro` | 8.2 | 8.7 | **8.4** | $0.01097 | 41 s |
| `openai/gpt-6-luna` | 7.5 | 8.6 | **8.0** | $0.00248 | 23 s |
| `deepseek/deepseek-v4.1-flash` | 8.2 | 7.4 | **7.8** | $0.01842 | 58 s |
| `xiaomi/mimo-v2.6-pro` | 5.7 | 5.7 | **5.7** | $0.01544 | 132 s |

**Total reported usage cost: $0.276771755**, including $0.00510854 for the two paid,
empty DeepSeek responses. Successful DeepSeek answers alone cost $0.01331176.
Costs come from each response's `usage.cost`, not the shared account balance,
which also funds the active production run. The immediate generation-detail lookups
returned 404; a later read-only reconciliation returned all 14 paid generation
receipts, whose `total_cost` values exactly matched the response usage totals.
No billed usage was returned for pre-inference 429/404 rejections. This is API billing
reconciliation, not a separate account invoice.

The latency column excludes failed attempts, queueing, setup, reading and grading.
DeepSeek's initial empty calls took 177.6 and 182.0 seconds; those failures must not
be hidden in a production cost/latency comparison. Neither was a completed answer
silently discarded in favor of a better sample.

Luna Pro cost about 14% of Sol's reported cost and 7% of Sol Pro's on these two
cases. Plain Luna was cheapest, but its oil note contained a substantive arithmetic
mistake. Pro did not cost the same in practice: Luna Pro used about 4.4 times Luna's
reported cost, and Sol Pro about 1.9 times Sol's. Equal listed token prices do not
mean equal task costs when reasoning/token usage differs.

## Quality Breakdown

| Model | Evidence 25% | Finance 25% | Decision 20% | Countercase 15% | Numbers 10% | Readability 5% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sol Pro | 9.0 | 8.8 | 8.8 | 8.8 | 9.0 | 9.0 |
| Sol | 8.5 | 8.8 | 8.5 | 8.8 | 8.5 | 9.0 |
| Luna Pro | 8.5 | 8.5 | 8.0 | 8.3 | 9.0 | 8.5 |
| Luna | 8.0 | 8.5 | 7.8 | 8.3 | 7.0 | 8.5 |
| DeepSeek | 8.3 | 7.3 | 7.5 | 7.5 | 8.5 | 8.3 |
| MiMo | 5.5 | 5.5 | 5.5 | 6.0 | 6.3 | 7.0 |

### Sol Pro

Best overall separation of physical oil scarcity, saleable production, forecasts,
valuation and concentration. It did not equate inaccessible Saudi production with
usable spare capacity or dismiss the disruption because recovery was forecast.
The hedge note distinguished bills, long nominal bonds, TIPS and bullion, explicitly
considered currency matching, and avoided funding changes by exhausting cash.

Its advantage over Sol was modest. It still did not audit the IEF narrative/table
inconsistency or quantify the gross/net borrowing distinction. It is not a substitute
for source verification or security valuation.

### Sol

Strong decision-oriented writing with funding and implementation logic. Its oil
answer held the core exposure and proposed selective rotation rather than an
automatic trim. Its hedge answer funded bullion from miners and clearly explained
that positive real yields are an opportunity cost for gold.

One imprecise oil statement said the inventory components should not be added into
a global balance. They can reconcile the recorded stock change approximately:
-65 -52 +23 = -94 million barrels, consistent with the rounded -95 total. The note
was right not to invent a new supply/demand balance, but its wording was too broad.

### Luna Pro

Useful, cautious, financially coherent notes at very low cost. Correctly separated
demand/supply growth from a predicted surplus, and identified that the energy sleeve
is not necessarily pure oil exposure. The hedge note understood real-duration risk,
inflation pricing, miner/bullion differences and funding from existing holdings.

Less detailed than Sol Pro on source limitations and implementation. The oil trim
decision relied substantially on concentration rather than demonstrating a marginal
portfolio improvement. Still the most attractive economical analytical worker here.

### Luna

The fastest and cheapest. Its gold/bonds note was good, though funding the new hedge
was not explained as clearly as Sol's. Its oil note said demand-growth forecasts from
+0.4 to -2.5 mb/d span 3.4 mb/d. The correct growth spread is 2.9; 3.4 is the spread
between forecast demand levels. It repeated the right-looking headline number in
the wrong calculation. Cheap deterministic arithmetic checks could catch this
without another model stage.

### DeepSeek V4.1 Flash

Strong on the oil arithmetic: it correctly combined annual demand 102.4 with supply
100.7 to obtain a conditional 1.7 mb/d deficit, kept the regional inventory signs
straight, and calculated aggregate resource exposure correctly.

The hedge note was weaker. It asserted that nominal bonds only win if inflation
falls or real rates decline. That is not the right general relative-return rule:
realized inflation versus what is priced over a matched horizon, duration and yield
changes matter. Inflation falling is neither necessary nor sufficient. It also
recommended USD Treasury/TIPS implementation without addressing the explicitly
unknown spending currency. Useful draft analysis, but not the strongest final judge
in this sample.

### MiMo V2.6 Pro

More assertive sizing and more statistics did not produce better analysis.

- Claimed oil futures already contained the IEA's 2027 supply recovery, although
  the packet contained no futures curve or market-pricing evidence.
- Called the OECD's 23-million-barrel total stock build a commercial stock build.
  The excerpt says commercial builds offset a 19-million government draw; commercial
  build is therefore about 42 million by inference, not 23.
- Treated normalization as the modal path and a trim as clearly correct without
  security valuations or justified scenario probabilities.
- Used an invalid source ID and confused a stock-flow trigger's units.
- Claimed a short Fed PCE forecast path established nominal outperformance versus
  10-year CPI-linked bonds, then said nominals beat gold because gold earns no income.
  The index/horizon mismatch and omission of gold price appreciation are material.
- Proposed reducing TIPS when breakeven exceeds current core CPI, another invalid
  comparison of inflation definitions and horizons.

These were not merely style differences. I would not promote MiMo to an allocation
or final-judgment role on this evidence.

## What the Experiment Did and Did Not Prove

Both cases used the same frozen September 21 research and historical portfolio
(high risk, 5+ years, energy producers 33.6635%, gold/silver miners 31.0358%). There
was no fresh retrieval and no previous model conclusion in the prompt. Four oil
sources and eight hedge sources were selected; full recorded excerpts were retained.
Some report the same underlying dataset. Citation presence is not independent
verification of publisher content.

All models broadly rejected adding indiscriminate oil exposure at that existing
weight and rejected replacing every bond with gold. That agreement is not proof of
the right market view or superior investment returns. The test rewarded mechanisms,
source handling and decision quality, not agreement with the user's plays or a
conservative allocation stance.

OpenAI's four models ran at medium reasoning. MiMo used enabled/default reasoning.
DeepSeek's scored answers used high reasoning through Fireworks after operational
correction. This is not equal compute. All final responses reported the exact model
IDs requested, finished with `stop`, and retained the identical per-case messages.
Settled receipts identify OpenAI snapshots dated 20260922, MiMo 20260921, and
DeepSeek 20260910; these underlying versions are preserved in the reconciliation.

The scoring protocol was fixed before calls. The eight OpenAI answers were scored
under randomized labels before their identities were revealed. Provider errors
revealed MiMo/DeepSeek identities during recovery, so those four answers were not
fully blind. A single assistant evaluated two samples per model; no independent
expert panel, repeated-seed confidence interval or paid model judge was used.

Most notes read well and used sensible tables; this benchmark did not test the
application's memo renderer, whole-portfolio optimization, long-context robustness,
fresh source discovery, securities valuation, or forecast accuracy. It supports a
shortlist and a small follow-on trial, not an automatic production migration.

## Operational Record and Harness Corrections

18 submissions produced 12 complete notes:

1. Eight OpenAI calls completed first attempt.
2. Two MiMo calls were rejected 429 by DeepInfra before generation. Two manual
   recovery calls through Xiaomi completed. All original receipts were preserved.
3. Two DeepSeek calls through OpenInference ended after 4,227/4,244 reasoning tokens
   with no visible answer and `length`. We sent no output cap. The harness incorrectly
   requested medium despite the catalog listing low/high/max; this was our setup
   error, not evidence of poor financial understanding.
4. Two native DeepSeek recovery requests were rejected 404 by the account's
   data-training privacy rule. The privacy settings were not changed.
5. Two final requests through Fireworks used high reasoning, `data_collection=deny`
   and the endpoint's advertised output allowance, and completed. This changed
   provider and effort together, so it does not isolate the initial failure's cause.

The initial plan was 12 requests/no retries. The deviations above were manual,
bounded recoveries of known failures, disclosed before proceeding. No completed
answer was regenerated. No ambiguous paid request was blindly replayed. MiMo's
retry omitted an app output cap; final DeepSeek calls used the selected endpoint's
943,718-token allowance to avoid an unknown provider default, not a 16k/32k ceiling.

Harness now rejects unsupported advertised reasoning efforts before dispatch,
preserves every attempt, refuses duplicate intents and restricts recovery to the
known failed cases. These changes are benchmark-local, not deployed application
changes. Do not interpret a terminal `length` with no visible answer as successful
completion just because the HTTP stream ended normally.

## Files

- [Protocol](portfolio-six-model-benchmark-20260923.md)
- [Benchmark runner](../scripts/benchmark_portfolio_six_models.py)
- [Result metadata](../outputs/audits/portfolio-six-model-benchmark-20260923/results.json)
- [Per-answer grades](../outputs/audits/portfolio-six-model-benchmark-20260923/blind-grades.json)
- [Recovery disclosure](../outputs/audits/portfolio-six-model-benchmark-20260923/retry-addendum.md)
- [All answers, named](../outputs/audits/portfolio-six-model-benchmark-20260923/all-answers.md)

Provider configuration reference: [OpenRouter reasoning options](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
Costs and capabilities above were read from this run's saved API responses/catalog,
not inferred from generic vendor claims.
