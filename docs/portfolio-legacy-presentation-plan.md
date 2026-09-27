# Portfolio Memo: Restore The Legacy Reading Experience

18 September 2026. Presentation plan only; no layout changes made in this pass.
The DeepSeek-led / Opus-review model roster has been applied locally, separately
from this document. No production deployment or new paid analysis was started.

## Decision

Restore the legacy memo's visual hierarchy and useful allocation graphics while
keeping the new analytical sequence. This is a reader-layer change, not a return
to the legacy reasoning architecture or a wholesale rollback of the component.

The reader should understand the market view, see the independently chosen
portfolio, understand what changes in their own book, and read the investment
arguments. Graphics should help compare those decisions, not displace the memo.

Keep the established light and dark themes, typography, saved-memo sidebar and
navigation. No new dashboard, oversized hero, collection of score cards or
diagnostic-first page. User approval of the legacy presentation does not imply
approval to recreate the previous analytical defects.

## What Actually Changed

The historical `PortfolioPositioningLab.jsx` at `HEAD` includes a coloured stacked
allocation bar, a six-column allocation grid, action markers, separated rationales,
cash/theme metadata and current-versus-strategic summaries. The present component
still contains much of this code.

Workflow 3 now wraps `CurrentSleeveDecisions` and `AllocationTable` in
`!independent`. The independent memo therefore bypasses the existing allocation
bar and styled grids, replacing them with two generic Markdown tables. This is a
specific rendering decision, not an absence of model output.

Separately, `backend/portfolio_memo.py:text()` recursively flattens dictionaries
and lists into semicolon-delimited prose. The memo repeats overlapping arguments
under targets, reconciliation, commentary and investment cases. The same-day
documents reached 15,355 and 18,677 words. Changing colours alone will not solve
that editorial problem.

The fast memo endpoint currently exposes current/final rows but not a compact
structured independent-ideal view. Restoring rich ideal graphics must extend that
small reader response, not fetch the full evidence/checkpoint artifact again.

The August reference was inspected in the current reader and against historical
source. Its allocation bar is presently suppressed by the later funding check;
that does not mean the legacy design lacked it. Do not undo this check to make an
invalid total look like a valid 100% portfolio. The April memo remains the main
reference for concise section order; August is useful for the surrounding visual
components.

## Proposed Reading Order

| Section | Reader sees | Presentation |
| --- | --- | --- |
| Investment view | The conclusion, main opportunity and principal risk | A short opening argument with the existing date/title hierarchy; cash and theme metadata remain secondary |
| Market setting | Growth, inflation, rates, credit and material commodity drivers | Short analytical subsections; selected observations with dates/units, not the entire research packet |
| Independent ideal | What the research favours before seeing holdings or ideas | Legacy-style allocation bar and table, followed by the reasons; no current-weight column |
| Your portfolio | What deserves retaining, reducing or exiting | Current-weight/action table and concise rationale; the current-aware alternative remains inspectable |
| Your investment plays | An explicit answer to each submitted hypothesis | One score, one verdict and an investment argument; omit the section when no plays were submitted |
| Recommended portfolio | The practical outcome and how it differs from both starting views | Allocation bar; current/range/reference/stance/conviction grid; funded changes and reasons |
| What would change the view | The important conditions and risks | Compact condition/implication rows with available observation dates; not a debug checklist |
| Sources and supporting analysis | Source links, alternative outputs, detailed evidence and provenance | Existing collapsed appendices at the end, loaded on demand |

This order is the editorial structure, not a requirement for every historical memo
to contain data it never recorded. Keep genuine older memo sections and fallbacks.

## Graphics And Formatting

### Allocation Graphics

Reuse the existing stacked-bar design at the independent and recommended
portfolio sections. Give the same economic exposure a stable colour across views;
the existing index-based colour assignment changes when rows reorder and is not
sufficient for comparison. Use restrained, distinct colours for major exposures
and neutral treatments for residual categories, within both existing themes.

Labels outside the bar or a compact key must expose small segments; no tiny text
forced into a 1% slice. Values remain available as text and on keyboard focus,
not only hover. The corresponding table is the accessible source of exact values.

The reference weights alone determine segment widths. Min/max ranges are not
extra capital. Never normalise an invalid 121% table into a convincing 100% bar.
For a partial or unbalanced proposal, preserve the rows and show the actual total;
omit the misleading stacked graphic rather than discard the analysis.

Do not introduce pies, gauges, invented risk scores or an equity curve. None adds
information beyond the data retained here. A three-view comparison must not imply
that unlike instruments are interchangeable: bullion and miners, or short and
long government duration, remain distinct.

### Tables And Narrative

Restore the legacy alignment, spacing, range column, clear numbers and restrained
action markers. Keep conviction separate from implementation readiness. Use
explicit EXIT treatment instead of styling unknown actions as HOLD. Preserve
zero, absent and unknown values as different states.

For each exposure, give the principal investment argument once. Put its detail
under a labelled expansion: why this expression, what is priced in, the contrary
case and the condition that changes the view. Material objections and uncertainty
belong in the visible argument; only repetitive substantiation belongs below it.

Use the established serif light-mode narrative and existing dark-mode styling.
Maintain clear heading levels, normal paragraphs, selective emphasis and compact
tables. Do not reconstruct either theme from memory or change global styles.

On narrow screens, stack the existing summary information and keep the memo
readable. Tables may scroll within their own labelled container; the whole page
must not widen. Do not truncate the investment reasoning to fit a visual block.

### Editorial Boundaries

Stop passing entire nested evidence objects through the generic text flattener
for main-body market sections. Map the existing market summary, relevant dated
observations and model commentary to explicit reader sections. Keep the complete
packet in supporting analysis with a visible route to it.

Do not add another LLM call merely to change formatting. Existing commentary can
supply narrative; existing structured rows can supply graphics. If legacy or
partially completed data lacks a summary, preserve the saved text or show that the
particular section was not assessed. Do not silently invent a shorter conclusion.

Set an editorial target of roughly 2,500-4,000 words for the primary reading path,
not a hard limit that deletes model output or fails a run. All original output
remains accessible. Repetition can be removed by assigning each argument a main
section, not by slicing text after an arbitrary character count.

## Investment Plays: Settled Design

**Yes: retain the feature. Treat a play as a hypothesis to test, not an allocation
instruction and not necessarily a new asset class.** This was implemented in the
local independent-workflow build, not just proposed.

The current flow is:

```text
Independent market research -> saved independent ideal
Current book -> separately saved current-aware assessment
Both views + user plays -> exposure review + defensive challenge
Material unanswered questions -> focused research where needed
Investment cases -> final recommendation, with a response to every play
```

The new roster assigns the exposure assessment to DeepSeek and the defensive
challenge to Opus. Plays do not enter either initial proposal. This keeps a real
distinction between what the system found independently and what the user asked
it to consider. Both initial views remain recorded even if a play changes the
final portfolio substantially.

Each play receives:

- **Investment case: N/10**, with a reason. This is analytical conviction in the
  case, not a probability, expected return or portfolio percentage.
- **Include, Watch, Reject or Needs research**, separate from the score.
- Mechanism, proposed exposure, what appears priced in, contrary evidence and
  overlap with the existing portfolio.
- An explicit final disposition. Inclusion can introduce a new exposure; it must
  explain the funding and why it improves on holding, cash or another expression.

Use `Not yet assessed` when the central case cannot be judged. Do not convert
missing minor metadata into a zero score or erase the rest of the analysis. A
high score need not produce an allocation if the exposure is already held or the
instrument/price is unsuitable. Preserve substantive reviewer disagreement.

### Agriculture / Fertiliser Example

Suggested hypothesis: **Agriculture and fertiliser opportunities if disruption
through the Strait of Hormuz constrains relevant supply or trade flows.**

The model should test the premise and its duration, identify the affected flows,
separate potential beneficiaries from businesses facing higher input/freight
costs, examine pass-through and normalisation risks, and assess current pricing.
Do not treat all agricultural businesses or fertiliser producers as one trade.
This is an example to investigate, not an assertion that the disruption currently
exists or that any exposure deserves a particular score.

It may propose a new exposure such as a particular fertiliser-producer category
when supported, prefer an existing exposure, leave it on watch, or reject it. The
idea must not receive a favourable answer simply because the user supplied it.
Do not fabricate an example score before doing the research.

### Current Implementation And Limits

| Capability | Current state |
| --- | --- |
| Editable ideas | `PortfolioIdeas.jsx` provides title/thesis rows under Investment plays |
| Optional detail | API accepts catalyst, horizon and expression; these are not separate UI inputs yet |
| Scoring and verdict | `PLAY_SCHEMA` / `PLAY_RULES` request 0-10 or unassessed plus a distinct verdict |
| Independence | Initial research, ideal and current-aware prompts exclude plays |
| Reassessment | A linked new assessment can reuse compatible saved workflow-3 work at the original cutoff; the original memo stays unchanged |
| Manual additions | User adjustment saves a separately labelled alternative, including new exposures; it does not rewrite the memo or recorded holdings |
| Automated coverage | Unit tests exercise play identity, input isolation, every-play handling and changed-play checkpoint reuse |
| Live validation | Neither live comparison supplied any plays; live assessment quality is not yet demonstrated |

The browser at port 5194 is a read-only comparison preview. It cannot submit an
assessment even though it renders the shared interface. This is not evidence
that the production plays workflow has been deployed.

Reassessing at the saved cutoff answers a historical question. For an idea based
on new events, start fresh research with an explicit new cutoff; do not imply that
cached historical research is current. Original holdings and memo remain intact
when a user later saves their own alternative.

## Build Scope And Sequence

1. Capture approved legacy desktop/mobile views in both themes, plus the current
   independent memo. Preserve exact existing styles as the starting reference.
2. Extend the compact memo read projection with only the ideal/current-aware rows,
   final comparison, play summaries and reader section data needed for the page.
   Keep raw research, receipts and full supporting data lazy-loaded.
3. Extract and reuse the current allocation graphic/table components, with an
   explicit ideal versus recommendation mode. Do not merely remove `!independent`,
   which would duplicate the Markdown tables and retain the wrong reading order.
4. Render the sections above using saved narrative and structured data. Put raw
   evidence packets and repeated supporting detail in the existing appendix.
   Preserve the original Markdown for inspection and historical fallbacks.
5. Add play verdict presentation at the correct point in the memo. Do not move
   play injection earlier in the analytical pipeline to make the UI simpler.
6. Test partial, unbalanced, no-plays and novel-exposure cases, then review the
   desktop/mobile result with the user before deployment.

Primary files: `frontend/src/components/PortfolioPositioningLab.jsx`,
`PortfolioMemoContent.jsx`, `PortfolioMemoAppendix.jsx`, `PortfolioIdeas.jsx`,
the existing portfolio CSS files, `backend/routers/runs.py`,
`backend/portfolio_read_store.py` and `backend/portfolio_memo.py`.

Exposure identity/funding and citation identity defects identified in the audits
are separate correctness work. Do not cover them up with visual normalisation.
They need resolution before comparison graphics can present affected outputs as
fully reconciled; unaffected valid portfolios can still be displayed.

## Acceptance Criteria

- The memo leads with readable analysis, not diagnostics or a wall of percentages.
- Legacy visual hierarchy, themes and useful allocation graphics are recognisable.
- Ideal, current-aware and final views remain distinct; no accidental relabelling.
- Every displayed number comes from saved data, including zero and unresolved values.
- Invalid totals remain visible, never cosmetically rescaled to 100%.
- No duplicate portfolio tables or repeated full arguments in the primary path.
- Every submitted play has an explained disposition; no empty plays section.
- No full-artifact request is required to open a saved memo; appendices stay lazy.
- Both themes work at desktop and mobile widths with readable labels and controls.
- Raw outputs, historical memos and current holdings are unchanged.
- Formatting causes no model calls and no new analysis workload.

See [model routing](model-routing.md), the [independent workflow build](portfolio-independent-memo-build.md)
and the [four-way comparison](portfolio-ling-opus-comparison-20260918.md).
