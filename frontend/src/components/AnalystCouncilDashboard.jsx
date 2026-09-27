import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import './AnalystCouncilDashboard.css';

const RUN_LIST_LIMIT = 100;

function navigateTo(pathname) {
  if (typeof window === 'undefined') return;
  window.history.pushState({}, '', pathname);
  window.dispatchEvent(new Event('app:navigate'));
}

function currentRunIdFromUrl() {
  if (typeof window === 'undefined') return '';
  try {
    return new URL(window.location.href).searchParams.get('run_id') || '';
  } catch {
    return '';
  }
}

function setRunIdInUrl(runId) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  const clean = String(runId || '').trim();
  if (clean) url.searchParams.set('run_id', clean);
  else url.searchParams.delete('run_id');
  window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
}

function formatDate(value) {
  const ts = Date.parse(String(value || ''));
  if (!Number.isFinite(ts)) return 'n/a';
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(ts));
}

function formatRelative(value) {
  const ts = Date.parse(String(value || ''));
  if (!Number.isFinite(ts)) return 'n/a';
  const diffMs = Date.now() - ts;
  const diffDays = Math.max(0, Math.floor(diffMs / 86400000));
  if (diffDays <= 0) return 'today';
  if (diffDays === 1) return '1d ago';
  if (diffDays < 31) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths <= 1) return '1m ago';
  return `${diffMonths}m ago`;
}

function scoreTotal(raw) {
  if (raw && typeof raw === 'object') {
    const total = Number(raw.total ?? raw.score ?? raw.value);
    return Number.isFinite(total) ? total : null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function scoreLabel(value) {
  return Number.isFinite(value) ? value.toFixed(1) : 'n/a';
}

function scoreTone(value) {
  if (!Number.isFinite(value)) return 'neutral';
  if (value >= 75) return 'positive';
  if (value >= 55) return 'base';
  return 'risk';
}

function pathTone(value) {
  const text = String(value || '').toLowerCase();
  if (text.includes('bull')) return 'positive';
  if (text.includes('bear')) return 'risk';
  if (text.includes('base')) return 'base';
  return 'neutral';
}

function cleanText(value, fallback = 'n/a') {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  return text || fallback;
}

function runTicker(run) {
  return cleanText(run?.ticker, 'N/A').toUpperCase();
}

function runCompany(run) {
  return cleanText(run?.company_name || run?.company || run?.label, 'Unknown company');
}

function runFreshness(run) {
  const freshness = run?.freshness && typeof run.freshness === 'object' ? run.freshness : {};
  const status = cleanText(freshness.status, 'unknown').toLowerCase();
  const age = Number(freshness.age_days);
  return {
    status,
    label: `${status}${Number.isFinite(age) ? ` ${age}d` : ''}`,
    tone: status === 'fresh' ? 'positive' : status === 'stale' ? 'risk' : 'neutral',
  };
}

function runMeanScore(run) {
  const direct = Number(run?.mean_quality_value_score);
  if (Number.isFinite(direct)) return direct;
  const quality = Number(run?.quality_score);
  const value = Number(run?.value_score);
  return Number.isFinite(quality) && Number.isFinite(value)
    ? (quality + value) / 2
    : null;
}

function detailStructured(payload) {
  return payload?.structured_data && typeof payload.structured_data === 'object'
    ? payload.structured_data
    : {};
}

function recommendationFromStructured(structured) {
  const rec = structured?.investment_recommendation && typeof structured.investment_recommendation === 'object'
    ? structured.investment_recommendation
    : {};
  const verdict = structured?.investment_verdict && typeof structured.investment_verdict === 'object'
    ? structured.investment_verdict
    : {};
  return {
    rating: cleanText(rec.rating || verdict.rating, 'N/A'),
    conviction: cleanText(rec.conviction || verdict.conviction, 'N/A'),
    summary: cleanText(rec.summary || verdict.summary || structured?.thesis_summary, ''),
  };
}

function currentPathFromStructured(structured) {
  const extended = structured?.extended_analysis && typeof structured.extended_analysis === 'object'
    ? structured.extended_analysis
    : {};
  const thesis = extended?.current_thesis_state && typeof extended.current_thesis_state === 'object'
    ? extended.current_thesis_state
    : {};
  return cleanText(thesis.leaning || thesis.path || structured?.current_path, 'unknown');
}

function targetSummary(structured) {
  const targets = structured?.price_targets && typeof structured.price_targets === 'object'
    ? structured.price_targets
    : {};
  const horizon24 = targets['24m'] || targets['24M'] || targets.twenty_four_month || targets.two_year || {};
  const weighted = Number(
    horizon24.probability_weighted
    ?? horizon24.prob_weighted
    ?? horizon24.weighted
    ?? targets.probability_weighted_24m
  );
  return Number.isFinite(weighted) ? weighted.toFixed(3) : 'n/a';
}

function runSearchText(run) {
  return [
    run?.id,
    run?.label,
    run?.ticker,
    run?.company_name,
    run?.analysis_date,
    run?.updated_at,
  ].map((value) => String(value || '').toLowerCase()).join(' ');
}

export default function AnalystCouncilDashboard() {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(currentRunIdFromUrl);
  const [selectedPayload, setSelectedPayload] = useState(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingSelected, setLoadingSelected] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoadingRuns(true);
        setError('');
        const payload = await api.listGanttRuns(RUN_LIST_LIMIT);
        const nextRuns = Array.isArray(payload?.runs) ? payload.runs : [];
        if (cancelled) return;
        setRuns(nextRuns);
        setSelectedRunId((current) => {
          if (current && nextRuns.some((run) => String(run.id) === String(current))) return current;
          return String(nextRuns[0]?.id || '');
        });
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load council runs');
      } finally {
        if (!cancelled) setLoadingRuns(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  useEffect(() => {
    const clean = String(selectedRunId || '').trim();
    setRunIdInUrl(clean);
    if (!clean) {
      setSelectedPayload(null);
      return undefined;
    }
    let cancelled = false;
    const load = async () => {
      try {
        setLoadingSelected(true);
        const payload = await api.getGanttRun(clean);
        if (!cancelled) setSelectedPayload(payload || null);
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load selected run');
      } finally {
        if (!cancelled) setLoadingSelected(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  const filteredRuns = useMemo(() => {
    const needle = String(query || '').trim().toLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => runSearchText(run).includes(needle));
  }, [runs, query]);

  const selectedRun = useMemo(
    () => runs.find((run) => String(run.id) === String(selectedRunId)) || filteredRuns[0] || null,
    [runs, filteredRuns, selectedRunId]
  );

  const companyCount = useMemo(() => {
    return new Set(runs.map((run) => runTicker(run)).filter(Boolean)).size;
  }, [runs]);

  const freshCount = runs.filter((run) => runFreshness(run).status === 'fresh').length;
  const structured = detailStructured(selectedPayload);
  const rec = recommendationFromStructured(structured);
  const qualityScore = scoreTotal(structured?.quality_score);
  const valueScore = scoreTotal(structured?.value_score);
  const currentPath = currentPathFromStructured(structured);
  const routerSummary = selectedRun?.scenario_router || {};

  const openSelectedRun = useCallback((runId = selectedRunId) => {
    const clean = String(runId || '').trim();
    navigateTo(clean ? `/council/runs?run_id=${encodeURIComponent(clean)}` : '/council/runs');
  }, [selectedRunId]);

  return (
    <main className="analyst-council-dashboard">
      <section className="analyst-council-topbar">
        <div>
          <h1>Analyst Council</h1>
          <p>Saved company analysis runs, thesis state, model consensus, and research artifacts.</p>
        </div>
        <div className="analyst-council-actions">
          <button type="button" onClick={() => setReloadToken((value) => value + 1)}>
            Refresh
          </button>
          <button type="button" className="is-primary" onClick={() => navigateTo('/council/new')}>
            New analysis
          </button>
        </div>
      </section>

      <section className="analyst-council-metrics" aria-label="Council run metrics">
        <div><span>Runs</span><strong>{runs.length}</strong></div>
        <div><span>Companies</span><strong>{companyCount}</strong></div>
        <div><span>Fresh</span><strong>{freshCount}</strong></div>
      </section>

      <section className="analyst-council-workbench">
        <aside className="analyst-run-list" aria-label="Saved council runs">
          <div className="analyst-run-list-head">
            <div>
              <h2>Runs</h2>
              <span>{filteredRuns.length} shown</span>
            </div>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter ticker or company"
              aria-label="Filter council runs"
            />
          </div>

          <div className="analyst-run-rows">
            {filteredRuns.map((run) => {
              const freshness = runFreshness(run);
              const meanScore = runMeanScore(run);
              const selected = String(run.id) === String(selectedRunId);
              return (
                <button
                  type="button"
                  className={`analyst-run-row${selected ? ' is-selected' : ''}`}
                  key={run.id}
                  onClick={() => setSelectedRunId(String(run.id || ''))}
                >
                  <span className={`analyst-run-score tone-${scoreTone(meanScore)}`}>{scoreLabel(meanScore)}</span>
                  <span className="analyst-run-main">
                    <strong>{runCompany(run)}</strong>
                    <em>{runTicker(run)} - {formatDate(run.analysis_date || run.updated_at)} - {formatRelative(run.updated_at)}</em>
                  </span>
                  <span className={`analyst-run-freshness tone-${freshness.tone}`}>{freshness.label}</span>
                </button>
              );
            })}
            {!filteredRuns.length && (
              <div className="analyst-run-empty">
                {loadingRuns ? 'Loading saved runs...' : 'No saved runs match this filter.'}
              </div>
            )}
          </div>
        </aside>

        <section className="analyst-run-preview" aria-label="Selected council run">
          {selectedRun ? (
            <>
              <div className="analyst-run-preview-head">
                <div>
                  <span>{runTicker(selectedRun)}</span>
                  <h2>{runCompany(selectedRun)}</h2>
                  <p>{cleanText(selectedRun.label, selectedRun.id)}</p>
                </div>
                <button type="button" className="is-primary analyst-run-open-action" onClick={() => openSelectedRun(selectedRun.id)}>
                  Open run
                </button>
              </div>

              <div className="analyst-run-preview-grid">
                <div>
                  <span>Recommendation</span>
                  <strong>{loadingSelected ? 'Loading...' : rec.rating}</strong>
                  <em>{rec.conviction}</em>
                </div>
                <div>
                  <span>Thesis path</span>
                  <strong className={`tone-${pathTone(currentPath)}`}>{currentPath}</strong>
                  <em>{formatDate(selectedRun.analysis_date || selectedRun.updated_at)}</em>
                </div>
                <div>
                  <span>Quality</span>
                  <strong className={`tone-${scoreTone(qualityScore)}`}>{scoreLabel(qualityScore)}</strong>
                  <em>score</em>
                </div>
                <div>
                  <span>Value</span>
                  <strong className={`tone-${scoreTone(valueScore)}`}>{scoreLabel(valueScore)}</strong>
                  <em>score</em>
                </div>
              </div>

              <div className="analyst-run-thesis">
                <h3>Run Thesis</h3>
                <p>{loadingSelected ? 'Loading run detail...' : rec.summary || 'No thesis summary available in the selected run artifact.'}</p>
              </div>

              <div className="analyst-run-detail-table">
                <div><span>24M weighted target</span><strong>{targetSummary(structured)}</strong></div>
                <div><span>Updated</span><strong>{formatDate(selectedRun.updated_at)}</strong></div>
                <div><span>Router state</span><strong>{cleanText(routerSummary.status || routerSummary.latest_state, 'n/a')}</strong></div>
                <div><span>Run id</span><strong>{selectedRun.id}</strong></div>
              </div>
            </>
          ) : (
            <div className="analyst-run-empty analyst-run-empty-large">
              <strong>No saved council runs found.</strong>
              <span>Start a new analysis to generate a durable Analyst Council run.</span>
              <button type="button" className="is-primary" onClick={() => navigateTo('/council/new')}>
                New analysis
              </button>
            </div>
          )}
        </section>
      </section>

      {error && <div className="analyst-council-error">{error}</div>}
    </main>
  );
}
