import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, RotateCw, Calculator, Save, ExternalLink, FileText } from 'lucide-react';
import { api } from '../api';
import { PortfolioRunProgress } from './PortfolioRunProgress';
import './PortfolioDecisionReview.css';

const label = (value) => String(value || '').replaceAll('_', ' ');
const pct = (value) => value == null || value === '' ? 'Not assessed' : `${Number(value).toFixed(2)}%`;
const numeric = (value) => value === '' || value == null ? null : Number(value);
const mandateFields = [
  ['base_currency', 'Base currency'], ['benchmark', 'Benchmark'], ['horizon_months', 'Horizon (months)', 'number'],
  ['max_drawdown_pct', 'Drawdown tolerance (%)', 'number'], ['liquidity_min_pct', 'Minimum cash (%)', 'number'],
  ['tax_cost_policy', 'Tax and cost constraints'], ['currency_hedge_policy', 'Currency hedging'],
];
const factors = [['rates_pp', 'Yield change (pp)'], ['equity_pct', 'Equities (%)'], ['commodity_pct', 'Commodities (%)'], ['fx_return_pct', 'Foreign currency (%)']];

function StageRecord({ runId, index }) {
  const [record, setRecord] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inspect = async () => {
    setLoading(true); setError('');
    try { setRecord((await api.getPortfolioStageRecord(runId, index)).record); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  return <div>
    {!record && <button type="button" onClick={inspect} disabled={loading}><FileText size={14} />{loading ? 'Loading...' : 'Inspect request and response'}</button>}
    {error && <p role="alert">{error}</p>}
    {record && <><details><summary>Submitted request</summary><pre className="portfolio-stage-payload">{JSON.stringify(record.request_messages || record.prompt || record.provider_metadata, null, 2)}</pre></details><details><summary>Provider response</summary><pre className="portfolio-stage-payload">{typeof record.raw_response?.content === 'string' ? record.raw_response.content : JSON.stringify(record.raw_response || record, null, 2)}</pre></details></>}
  </div>;
}

export function PortfolioHealth({ payload, onRecovered }) {
  const [job, setJob] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const health = payload.analysis_health || { status: 'incomplete', label: 'Analysis not verified', issues: [] };
  useEffect(() => {
    if (!job?.job_id || ['succeeded', 'failed'].includes(job.status)) return undefined;
    let disposed = false;
    let timer;
    const poll = async () => {
      try {
        const response = await api.getAnalysisJob(job.job_id);
        if (disposed) return;
        const updated = response.job || response;
        setJob(updated);
        setError('');
        if (['succeeded', 'failed'].includes(updated.status)) {
          if (updated.run_id) onRecovered(updated.run_id);
          else setError(updated.error || 'Recovery did not produce a memo');
        } else timer = setTimeout(poll, 4000);
      } catch (err) { if (!disposed) { setError(err.message); timer = setTimeout(poll, 4000); } }
    };
    timer = setTimeout(poll, 1000);
    return () => { disposed = true; clearTimeout(timer); };
  }, [job?.job_id, job?.status, onRecovered]);
  const recover = async () => {
    setPending(true); setError('');
    try {
      const result = await api.createAnalysisJob({ job_type: 'portfolio_positioning', resume_portfolio_run_id: payload.id });
      setJob(result.job || result);
    } catch (err) { setError(err.message); }
    finally { setPending(false); }
  };
  const running = job && !['succeeded', 'failed'].includes(job.status);
  return <section className={`portfolio-health ${health.status}`} aria-label="Analysis status">
    <div className="portfolio-review-heading">
      <strong>{health.status === 'complete' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}{health.label}</strong>
      {payload.can_resume && health.status !== 'complete' && <button type="button" onClick={recover} disabled={pending || running} title="Reuse completed stages and retry remaining work; uses configured model APIs"><RotateCw size={15} />{running ? 'Recovery running' : pending ? 'Starting...' : 'Recover analysis'}</button>}
    </div>
    {error && <p role="alert">{error}</p>}
    {health.status === 'complete' && health.decision_status === 'needs_review' && <p>{health.decision_label}</p>}
    {job && <PortfolioRunProgress job={job} error={error} />}
    <details><summary>{health.issues?.length || 0} outstanding issues · {payload.stage_receipts?.length || 0} execution records</summary>
      <div className="portfolio-review-scroll">
        {payload.workload && <p>{payload.workload.completed_tasks} completed tasks · {payload.workload.reused_tasks} reused · {payload.workload.new_model_requests} new model requests · {payload.workload.retry_requests} {payload.workload.retry_requests === 1 ? 'retry' : 'retries'}</p>}
        {Number.isFinite(payload.workload?.reported_openrouter_usd) && <p>Reported OpenRouter cost for new requests: US${payload.workload.reported_openrouter_usd.toFixed(2)}. Other providers are not included.{payload.workload.unpriced_model_requests > 0 && ` Cost unavailable for ${payload.workload.unpriced_model_requests} model requests.`}</p>}
        <ul>{health.issues?.map((issue, index) => <li key={index}><strong>{label(issue.stage)}: </strong>{issue.detail}</li>)}</ul>
        {payload.stage_receipts?.map((receipt, index) => <details key={index}><summary>{receipt.model || receipt.stage} · {receipt.status}{receipt.reused ? ' · reused' : ''}</summary>
          <p>{receipt.stage}</p><p>{receipt.error || receipt.validation_errors?.join('; ') || 'Response accepted'}</p>
          <p>{receipt.started_at} · Attempt {receipt.attempt || 1}{receipt.error_status ? ` · HTTP ${receipt.error_status}` : ''}</p>
          {receipt.request_id && <p>Request: {receipt.request_id}</p>}
          <StageRecord runId={payload.id} index={index} />
        </details>)}
      </div>
    </details>
  </section>;
}

function Field({ title, value, onChange, type = 'text' }) {
  return <label className="portfolio-review-field"><span>{title}</span><input aria-label={title} type={type} step={type === 'number' ? 'any' : undefined} value={value ?? ''} onChange={(event) => onChange(event.target.value)} /></label>;
}

export default function PortfolioDecisionReview({ payload }) {
  const decision = payload.structured_data?.decision || {};
  const rows = decision.funding?.rows || [];
  const initial = payload.portfolio_snapshot || {};
  const [tab, setTab] = useState('Evidence');
  const [mandate, setMandate] = useState(initial.mandate || {});
  const [exposures, setExposures] = useState(initial.risk_exposures || {});
  const [scenario, setScenario] = useState(initial.scenarios?.[0] || { name: 'Portfolio scenario', horizon_months: '', shocks: {} });
  const [observations, setObservations] = useState(initial.review_observations || []);
  const [returns, setReturns] = useState([]);
  const [report, setReport] = useState(null);
  const [riskAssessment, setRiskAssessment] = useState(initial.risk_assessment || {});
  const [dirty, setDirty] = useState(false);
  const edited = useRef(false);
  const editVersion = useRef(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const conditions = payload.macro_positioning?.monitoring_triggers || [];
  useEffect(() => {
    let active = true;
    api.listPortfolioReviews(payload.id).then(({ reviews }) => {
      const latest = reviews?.find((review) => !review.user_adjustment);
      if (!active || edited.current || !latest) return;
      setReport(latest);
      const inputs = latest.inputs || {};
      setMandate(inputs.mandate || {}); setExposures(inputs.exposures || {});
      if (inputs.scenarios?.[0]) setScenario(inputs.scenarios[0]);
      setObservations(inputs.observations || []); setReturns(inputs.total_returns || []);
      setRiskAssessment(inputs.risk_assessment || {});
    }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [payload.id]);
  const setExposure = (id, key, value) => setExposures((current) => ({ ...current, [id]: { ...current[id], [key]: value } }));
  const setReturn = (asset, key, value) => setReturns((current) => {
    const existing = current.find((row) => row.asset_class === asset) || { asset_class: asset, currency: mandate.base_currency || '' };
    return [...current.filter((row) => row.asset_class !== asset), { ...existing, [key]: value }];
  });
  const save = async () => {
    setBusy(true); setError('');
    const submittedVersion = editVersion.current;
    const shocks = Object.fromEntries(Object.entries(scenario.shocks || {}).filter(([, value]) => value !== '' && value != null).map(([key, value]) => [key, numeric(value)]));
    const normalizedExposures = Object.fromEntries(Object.entries(exposures).map(([key, value]) => [key, {
      ...value, annual_carry_pct: numeric(value.annual_carry_pct), transaction_cost_bps: numeric(value.transaction_cost_bps),
      sensitivities: Object.fromEntries(Object.entries(value.sensitivities || {}).map(([factor, sensitivity]) => [factor, numeric(sensitivity)])),
    }]));
    try {
      const result = await api.reviewPortfolioRun(payload.id, { mandate, exposures: normalizedExposures,
        scenarios: [{ ...scenario, horizon_months: numeric(scenario.horizon_months), shocks }], observations, total_returns: returns,
        risk_assessment: riskAssessment,
        alternatives: [{ name: 'Cash alternative', asset_class_targets: [{ asset_class: 'cash', min_pct: 100, target_pct: 100, max_pct: 100 }],
          current_sleeve_actions: rows.filter((row) => row.asset_class.toLowerCase() !== 'cash').map((row) => ({ asset_class: row.asset_class, action: 'EXIT' })) }],
      });
      setReport(result);
      setDirty(editVersion.current !== submittedVersion);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const facts = payload.evidence_brief?.facts || [];
  const sources = payload.evidence_brief?.source_packet?.sources || [];
  const judgment = payload.macro_positioning?.judgment_audit;
  const followup = payload.targeted_research;
  const scenarioResult = !dirty && report?.scenarios?.[0];
  const reviewedDecision = report?.decision || decision;
  const benchmark = String(mandate.benchmark || '').trim();
  const comparisonRows = benchmark && !rows.some((row) => row.asset_class.replace(/[^a-z0-9]/gi, '').toLowerCase() === benchmark.replace(/[^a-z0-9]/gi, '').toLowerCase())
    ? [...rows, { asset_class: benchmark, display_name: `${benchmark} (benchmark)` }] : rows;
  return <section className="portfolio-decision-review" onChange={() => { setDirty(true); edited.current = true; editVersion.current += 1; }}>
    <div className="portfolio-review-tabs" role="tablist" aria-label="Portfolio research and review">
      {['Evidence', 'Mandate', 'Scenarios', 'Conditions', 'Performance'].map((name) => <button key={name} role="tab" aria-selected={tab === name} aria-controls="portfolio-review-panel" onClick={() => setTab(name)}>{name}</button>)}
    </div>
    <div role="tabpanel" id="portfolio-review-panel" aria-label={tab}>
      {error && <p role="alert" className="portfolio-error">{error}</p>}
      {tab === 'Evidence' && <>
        {judgment && <details><summary>Decision review</summary>
          {judgment.contributors?.map((review, index) => <p key={index}><strong>{label(review.role)}:</strong> {review.model || 'Model not recorded'} · {review.contributed ? 'Contributed' : 'Did not return a substantive review'}{review.error && ` · ${review.error}`}</p>)}
          <ul>{judgment.unresolved_findings?.map((finding, index) => <li key={index}>{finding.detail}</li>)}
            {judgment.comparison_issues?.map((issue, index) => <li key={`comparison-${index}`}>{issue.purpose}: {issue.detail}</li>)}
            {judgment.exposure_mapping_issues?.map((issue, index) => <li key={`mapping-${index}`}>{issue}</li>)}
            {payload.macro_positioning?.implementation_comparison?.issues?.map((issue, index) => <li key={`alternative-${index}`}>{issue}</li>)}
            {payload.macro_positioning?.decision_reconsideration?.issues?.map((issue, index) => <li key={`revision-${index}`}>{issue}</li>)}</ul>
          {payload.macro_positioning?.consistency_review?.summary && <p>{payload.macro_positioning.consistency_review.summary}</p>}
          <ul>{payload.macro_positioning?.claim_corrections?.map((correction, index) => <li key={index}>{correction.reason}<br />{correction.replacement}</li>)}</ul>
        </details>}
        {followup?.questions?.length > 0 && <details><summary>Follow-up research</summary>
          {followup.questions.map((question, index) => <details key={question.id || index}><summary>{question.question} · {label(question.status)}</summary><p>{question.answer || question.material_reason}</p></details>)}
          <ul>{followup.unresolved?.map((question, index) => <li key={index}>{question.question}: {question.reason}</li>)}</ul>
        </details>}
        <h3>Evidence behind the proposal</h3>
        {rows.map((row) => <details key={row.asset_class}><summary>{label(row.display_name || row.asset_class)} · {row.fact_ids?.length || 0} linked facts</summary>
          <p>{row.rationale || 'No rationale recorded'}</p>
          {row.market_pricing?.observed_expectation && <p><strong>Market pricing: </strong>{row.market_pricing.observed_expectation}</p>}
          {row.investment_case?.downside && <p><strong>Downside: </strong>{row.investment_case.downside}</p>}
          {row.implementation && <p>{[row.implementation.instrument_type, row.implementation.currency, ...Object.entries(row.implementation.risk_attributes || {}).filter(([, value]) => value != null).map(([key, value]) => `${label(key)}: ${value}`)].filter(Boolean).join(' · ')}</p>}
          {(row.fact_ids || []).map((id) => {
            const fact = facts.find((item) => item.id === id);
            return <div key={id}><p>{fact ? `${fact.metric}: ${fact.value} ${fact.unit} · ${fact.benchmark} · ${fact.observed_at} · ${label(fact.claim_status || 'source support not assessed')}` : `Source fact unavailable: ${id}`}</p>{fact?.claim_review?.reason && <p>{fact.claim_review.reason}</p>}</div>;
          })}
          <ul>{row.open_questions?.map((question) => <li key={question}>{question}</li>)}</ul>
          {row.alternatives?.map((alternative, index) => <p key={index}><strong>{alternative.name}: </strong>{alternative.why_preferred}</p>)}
          <ul>{row.contrary_evidence?.map((item, index) => <li key={index}>{typeof item === 'string' ? item : item.summary || item.reason || 'Contrary evidence requires review'}</li>)}</ul>
        </details>)}
        <details><summary>Competing allocations</summary><div className="portfolio-review-scroll">
          {payload.portfolio_memo_ensemble?.lanes?.map((lane, index) => <div key={index}><h4>{label(lane.lane)}</h4><p>{lane.error}</p>
            {(lane.macro_positioning?.asset_class_targets || []).map((row) => <p key={row.asset_class}>{label(row.display_name || row.asset_class)}: {pct(row.target_pct)}</p>)}
          </div>)}
        </div></details>
        <details><summary>Company research · {initial.company_evidence?.length || 0} holdings</summary>
          {initial.company_evidence?.map((company, index) => <div key={index}><p><strong>{company.ticker}</strong> · {label(company.status)}{company.run_id && <> · <a href={`/council?run_id=${encodeURIComponent(company.run_id)}`}>Company analysis <ExternalLink size={12} /></a></>}{company.reason ? ` · ${company.reason}` : ` · ${company.age_days} days old`} · {company.announcements?.length || 0} announcements</p><ul>{company.coverage_issues?.map((issue) => <li key={issue}>{issue}</li>)}</ul></div>)}
        </details>
        <details><summary>Sources · {sources.length}</summary><div className="portfolio-review-scroll">{sources.map((source) => <details key={source.id}><summary><a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a> · {source.published_at || 'Publication date unavailable'}</summary><p className="portfolio-source-excerpt">{source.excerpt || 'Citation only; source text was not retrieved'}</p></details>)}</div></details>
        <details><summary>Research lanes · {payload.evidence_brief?.source_packet?.research?.length || 0}</summary><div className="portfolio-review-scroll">{payload.evidence_brief?.source_packet?.research?.map((lane, index) => <details key={index}><summary>{label(lane.lane)} · {lane.provider}</summary><p className="portfolio-source-excerpt">{lane.text}</p></details>)}</div></details>
        {Object.keys(payload.retained_research || {}).length > 0 && <details><summary>Recovered research</summary>{Object.entries(payload.retained_research).map(([key, item]) => <details key={key}><summary>{label(item.stage)}</summary><p className="portfolio-source-excerpt">{item.result.research_summary || item.result.summary || item.result.error}</p></details>)}</details>}
      </>}
      {tab === 'Mandate' && <><h3>Portfolio mandate</h3><div className="portfolio-review-fields">{mandateFields.map(([key, title, type]) => <Field key={key} title={title} type={type} value={mandate[key]} onChange={(value) => setMandate({ ...mandate, [key]: type === 'number' ? numeric(value) : value })} />)}</div>
        {!dirty && <ul>{reviewedDecision.mandate_issues?.map((issue) => <li key={issue}>{issue}</li>)}{reviewedDecision.mandate_checks?.map((check) => <li key={check.constraint}><strong>{label(check.constraint)}: {label(check.status)}</strong> · {check.reason}</li>)}</ul>}
        <details><summary>Portfolio risk estimate</summary><div className="portfolio-review-fields">{[['estimated_max_drawdown_pct', 'Estimated maximum drawdown (%)', 'number'], ['as_of', 'Risk estimate date', 'date'], ['method', 'Risk estimation method'], ['source_url', 'Risk estimate source']].map(([key, title, type]) => <Field key={key} title={title} type={type} value={riskAssessment[key]} onChange={(value) => setRiskAssessment({ ...riskAssessment, allocation_hash: reviewedDecision.allocation_hash, [key]: type === 'number' ? numeric(value) : value })} />)}</div></details>
      </>}
      {tab === 'Scenarios' && <>
        <h3>Hold, proposed allocation and cash</h3>
        <div className="portfolio-review-fields"><Field title="Scenario name" value={scenario.name} onChange={(name) => setScenario({ ...scenario, name })} /><Field title="Horizon (months)" type="number" value={scenario.horizon_months} onChange={(value) => setScenario({ ...scenario, horizon_months: value })} />{factors.map(([key, title]) => <Field key={key} title={title} type="number" value={scenario.shocks?.[key]} onChange={(value) => setScenario({ ...scenario, shocks: { ...scenario.shocks, [key]: value } })} />)}</div>
        {comparisonRows.map((row) => { const exposure = exposures[row.asset_class] || {}; return <details key={row.asset_class}><summary>{label(row.display_name || row.asset_class)} · assumptions</summary><div className="portfolio-review-fields">
          <Field title={`${label(row.asset_class)} currency`} value={exposure.currency} onChange={(value) => setExposure(row.asset_class, 'currency', value)} />
          <Field title="Annual carry (%)" type="number" value={exposure.annual_carry_pct} onChange={(value) => setExposure(row.asset_class, 'annual_carry_pct', value)} />
          <Field title="Trading costs (bps)" type="number" value={exposure.transaction_cost_bps} onChange={(value) => setExposure(row.asset_class, 'transaction_cost_bps', value)} />
          {factors.filter(([key]) => scenario.shocks?.[key] !== '' && scenario.shocks?.[key] != null).map(([key, title]) => <Field key={key} title={`Return sensitivity per unit: ${title}`} type="number" value={exposure.sensitivities?.[key]} onChange={(value) => setExposure(row.asset_class, 'sensitivities', { ...exposure.sensitivities, [key]: value })} />)}
          <Field title="Assumption basis" value={exposure.basis} onChange={(value) => setExposure(row.asset_class, 'basis', value)} /><Field title="Source" value={exposure.source} onChange={(value) => setExposure(row.asset_class, 'source', value)} />
        </div></details>; })}
        {scenarioResult && <div className="portfolio-comparison"><p>Hold: <strong>{pct(scenarioResult.hold_return_pct)}</strong> · Proposed: <strong>{pct(scenarioResult.proposed_return_pct)}</strong> · Cash: <strong>{pct(report.alternatives?.[0]?.scenarios?.[0]?.proposed_return_pct)}</strong></p>
          <p>{scenarioResult.method}</p><ul>{scenarioResult.rows?.filter((row) => row.missing_inputs?.length).map((row) => <li key={row.asset_class}>{label(row.asset_class)}: {row.missing_inputs.join('; ')}</li>)}</ul>
          <p>Benchmark ({scenarioResult.benchmark?.name || 'Not specified'}): <strong>{pct(scenarioResult.benchmark?.return_pct)}</strong></p>
        </div>}
      </>}
      {tab === 'Conditions' && <><h3>Review conditions</h3>{!conditions.length && <p>No review conditions were recorded.</p>}{conditions.map((condition, index) => {
        const observation = observations.find((row) => row.metric === condition.metric && row.benchmark === condition.benchmark && row.unit === condition.unit) || {};
        const update = (key, value) => setObservations((current) => [...current.filter((row) => !(row.metric === condition.metric && row.benchmark === condition.benchmark && row.unit === condition.unit)), { ...observation, metric: condition.metric, benchmark: condition.benchmark, unit: condition.unit, [key]: value }]);
        return <details key={condition.id || index}><summary>{condition.metric || condition.trigger || 'Untyped review note'} · {label(report?.conditions?.[index]?.status || 'unassessed')}</summary><p>{condition.what_changes || condition.action || condition.signal}</p><p>{condition.benchmark} · {condition.operator} {condition.threshold} {condition.unit} · {condition.next_review}</p>
          {condition.metric && <div className="portfolio-review-fields"><Field title="Observed value" type="number" value={observation.value} onChange={(value) => update('value', numeric(value))} /><Field title="Observed on" type="date" value={observation.observed_at} onChange={(value) => update('observed_at', value)} /><Field title="Published on" type="date" value={observation.published_at} onChange={(value) => update('published_at', value)} /><Field title="Observation source" value={observation.source_url} onChange={(value) => update('source_url', value)} /></div>}
        </details>;
      })}</>}
      {tab === 'Performance' && <><h3>Shadow portfolio</h3>{comparisonRows.map((row) => { const value = returns.find((item) => item.asset_class === row.asset_class) || {}; return <details key={row.asset_class}><summary>{label(row.display_name || row.asset_class)}</summary><div className="portfolio-review-fields">
        {[['total_return_pct', 'Total return (%)', 'number'], ['transaction_cost_bps', 'Trading costs (bps)', 'number'], ['currency', 'Return currency'], ['from', 'From', 'date'], ['to', 'To', 'date'], ['source_url', 'Return source']].map(([key, title, type]) => <Field key={key} title={title} type={type} value={value[key]} onChange={(next) => setReturn(row.asset_class, key, type === 'number' ? numeric(next) : next)} />)}
      </div></details>; })}
        {report && !dirty && <div className="portfolio-comparison"><p>Hold: <strong>{pct(report.performance?.hold_return_pct)}</strong> · Proposed: <strong>{pct(report.performance?.proposal_return_pct)}</strong> · Cash: <strong>{pct(report.alternatives?.[0]?.performance?.proposal_return_pct)}</strong></p><p>Benchmark ({report.performance?.benchmark?.name || 'Not specified'}): {pct(report.performance?.benchmark?.return_pct)} · Excess return: {pct(report.performance?.benchmark?.excess_return_pp)}</p><p>Maximum drawdown: {pct(report.performance?.drawdown?.proposal_max_drawdown_pct)}</p><ul>{[...(report.performance?.issues || []), ...(report.performance?.drawdown?.issues || [])].map((issue, index) => <li key={index}>{issue}</li>)}</ul></div>}
      </>}
      {tab !== 'Evidence' && <div className="portfolio-review-footer"><button type="button" onClick={save} disabled={busy}>{tab === 'Scenarios' ? <Calculator size={16} /> : <Save size={16} />}{busy ? 'Saving...' : tab === 'Scenarios' ? 'Calculate comparison' : 'Save review'}</button>{dirty ? <span role="status">Unsaved changes</span> : report && <span role="status">Reviewed {new Date(report.as_of).toLocaleString()}</span>}</div>}
    </div>
  </section>;
}
