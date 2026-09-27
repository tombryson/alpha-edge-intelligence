import { useCallback, useEffect, useRef, useState } from 'react';
import PortfolioMemoContent from './PortfolioMemoContent';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown } from 'lucide-react';
import { api } from '../api';
import PortfolioMemoAppendix from './PortfolioMemoAppendix';
import ActivePortfolioRuns from './PortfolioRunProgress';
import './PortfolioPositioningLab.css';
import './PortfolioPositioningLabTheme.css';

const THEME_STORAGE_KEY = 'alpha-edge:portfolio-theme';

function getInitialTheme() {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

function getInitialRunId() {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('run_id') || '';
}

function navigateToRun(runId) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (runId) {
    url.searchParams.set('run_id', runId);
  } else {
    url.searchParams.delete('run_id');
  }
  window.history.replaceState({}, '', `${url.pathname}${url.search}`);
}

function formatPct(value) {
  if (value == null || value === '') return 'Unresolved';
  const num = Number(value);
  if (!Number.isFinite(num)) return 'n/a';
  return `${num.toFixed(Math.abs(num) >= 10 ? 0 : 1)}%`;
}

function formatDate(value) {
  const raw = String(value || '').trim();
  if (!raw) return 'n/a';
  try {
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(raw));
  } catch {
    return raw.slice(0, 16);
  }
}

function sentence(value, fallback = 'Not assessed') {
  if (Array.isArray(value)) return value.map((item) => sentence(item, '')).filter(Boolean).join('; ') || fallback;
  if (value && typeof value === 'object') return sentence(value.assessment || value.summary || value.description, fallback);
  const text = String(value ?? '').trim();
  return text || fallback;
}

function humanizeAssetLabel(value, fallback = 'Unnamed sleeve') {
  const raw = String(value || '').trim();
  if (!raw) return fallback;
  const spaced = raw.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!spaced) return fallback;
  if (spaced === spaced.toLowerCase() || spaced === spaced.toUpperCase()) {
    return spaced.replace(/\b\w/g, (char) => char.toUpperCase());
  }
  return spaced;
}

function assetLabel(row, fallback = 'Unnamed sleeve', { caps = false } = {}) {
  const rawName = String(row?.display_name || row?.asset_class || '').trim();
  const assetClass = String(row?.asset_class || '').trim();
  const normalizedName = rawName.replace(/[^a-z0-9]+/gi, '').toUpperCase();
  const normalizedAsset = assetClass.replace(/[^a-z0-9]+/gi, '').toUpperCase();
  const label = normalizedName && normalizedName === normalizedAsset
    ? humanizeAssetLabel(rawName, fallback)
    : humanizeAssetLabel(rawName, fallback);
  return caps ? label.toUpperCase() : label;
}

function cleanRunLabel(value) {
  const text = String(value || '').trim();
  if (!text) return 'Portfolio memo';
  return text
    .replace(/\.json\b/gi, '')
    .replace(/^portfolio_positioning(?:_job)?(?:_portfolio_positioning)?(?:_\d{8}_\d{6})?/i, 'Portfolio memo')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function listFrom(value) {
  return Array.isArray(value) ? value.filter((item) => String(item || '').trim()) : [];
}

function toneForAction(action) {
  const normalized = String(action || '').trim().toLowerCase();
  if (normalized === 'add') return 'add';
  if (normalized === 'trim') return 'trim';
  if (normalized === 'review') return 'review';
  return 'hold';
}

function StatCard({ label, value }) {
  return (
    <div className="portfolio-stat-card" role="listitem">
      <div className="portfolio-stat-label">{label}</div>
      <div className="portfolio-stat-value">{value}</div>
    </div>
  );
}

function investmentTheme(strategic) {
  const theme = sentence(strategic.primary_theme);
  const firstSentence = [...new Intl.Segmenter(undefined, { granularity: 'sentence' }).segment(theme)][0]?.segment.trim() || theme;
  const compact = firstSentence.split(/\s+/).length <= 20;
  const title = compact ? firstSentence : 'Investment outlook';
  const explanation = compact ? theme.slice(firstSentence.length).trim() : theme;
  const paragraphs = [...new Set([explanation, sentence(strategic.theme_explanation, '')].filter(Boolean))];
  return { title, paragraphs, alternative: sentence(strategic.secondary_theme, '') };
}

function Synopsis({ value }) {
  const summary = sentence(value, 'No executive summary was saved in this memo.');
  return <div className="markdown-content portfolio-executive-summary">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
  </div>;
}

function AllocationTable({ rows, funded, independent = false }) {
  const targets = Array.isArray(rows) ? rows : [];
  const totalTarget = targets.reduce((sum, row) => {
    const value = Number(row?.target_pct);
    return sum + (Number.isFinite(value) && value > 0 ? value : 0);
  }, 0);
  return (
    <section className="portfolio-panel allocation-panel">
      <div className="portfolio-section-head">
        <div>
          <h2>Asset Class Targets</h2>
          <p>{funded ? 'Fully funded' : 'Funding unresolved'} · Specified targets: {formatPct(totalTarget)}</p>
        </div>
      </div>

      {!independent && targets.length && funded && Math.abs(totalTarget - 100) < 0.05 ? (
        <div className="portfolio-target-bar" aria-label="Target allocation stacked bar">
          {targets.map((row, idx) => {
            const target = Number(row?.target_pct);
            const width = Number.isFinite(target) && target > 0 ? (target / totalTarget) * 100 : 0;
            if (width <= 0) return null;
            return (
              <div
                className="portfolio-target-bar-segment"
                key={`${row?.asset_class || idx}-segment`}
                style={{
                  width: `${width}%`,
                  '--segment-index': idx,
                }}
                title={`${assetLabel(row)}: ${formatPct(row?.target_pct)}`}
              >
                {width >= 7 ? <span>{assetLabel(row, '')}</span> : null}
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="portfolio-allocation-grid" role="table" aria-label="Asset class target allocation">
        <div className="portfolio-allocation-grid-row header" role="row">
          <span role="columnheader">Asset Class</span>
          <span role="columnheader">Current</span>
          <span role="columnheader">Range</span>
          <span role="columnheader">Target</span>
          <span role="columnheader">Direction</span>
          <span role="columnheader">Conviction</span>
        </div>
        {targets.length ? targets.map((row, idx) => {
          const action = String(row?.action || 'HOLD').toUpperCase();
          const conviction = String(row?.model_thesis_conviction || row?.thesis_conviction || row?.conviction || 'UNASSESSED');
          return (
            <div className="portfolio-allocation-grid-row" role="row" key={`${row?.asset_class || idx}`}>
              <span role="cell">
                <strong>{assetLabel(row, 'Unnamed sleeve', { caps: true })}</strong>
                <em>{sentence(row?.thesis_role, 'role not stated')}</em>
              </span>
              <span role="cell">{formatPct(row?.current_pct)}</span>
              <span role="cell">{row?.min_pct == null && row?.max_pct == null ? 'Not recorded' : `${formatPct(row?.min_pct)} - ${formatPct(row?.max_pct)}`}</span>
              <span role="cell">{formatPct(row?.target_pct)}</span>
              <span role="cell"><mark className={`portfolio-action ${toneForAction(action)}`}>{action}</mark></span>
              <span role="cell">{conviction}</span>
            </div>
          );
        }) : (
          <div className="portfolio-empty-row">No asset-class target rows were saved in this memo.</div>
        )}
      </div>

      {!independent && targets.length ? (
        <div className="portfolio-allocation-rationales">
          <h3>Allocation Rationale</h3>
          {targets.map((row, idx) => {
            const action = String(row?.action || 'HOLD').toUpperCase();
            const conviction = String(row?.model_thesis_conviction || row?.thesis_conviction || row?.conviction || 'UNASSESSED');
            return (
              <p key={`${row?.asset_class || idx}-rationale`}>
                <strong>{assetLabel(row, 'Unnamed sleeve', { caps: true })}</strong>
                <span> ({sentence(row?.thesis_role, 'role not stated')}) - {action} / {conviction}: </span>
                {sentence(row?.rationale, 'No rationale supplied.')}
              </p>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

function PortfolioShapes({ views }) {
  if (!views?.some((view) => view.rows?.length)) return null;
  const keyFor = (row) => String(row.asset_class || '').replace(/[^a-z0-9]/gi, '').toUpperCase();
  const assets = [...new Map(views.flatMap((view) => view.rows || []).map((row) => [keyFor(row), row])).entries()]
    .sort(([left], [right]) => left.localeCompare(right));
  const colour = new Map(assets.map(([key], index) => [key, index]));
  return <section className="portfolio-shapes" aria-label="Portfolio shapes">
    <h2>Portfolio shape</h2>
    {views.map((view) => <div className="portfolio-shape-row" key={view.id}>
      <strong>{view.title}</strong>
      {view.status === 'balanced' ? <div className="portfolio-target-bar" role="img" aria-label={`${view.title} allocation: ${view.rows.filter((row) => row.target_pct > 0).map((row) => `${assetLabel(row)} ${row.target_pct}%`).join(', ')}`}>
        {view.rows.filter((row) => row.target_pct > 0).map((row) => <div className="portfolio-target-bar-segment"
          key={keyFor(row)} title={`${assetLabel(row)}: ${row.target_pct}%`}
          style={{ width: `${row.target_pct}%`, '--segment-index': colour.get(keyFor(row)) }}>
          {row.target_pct >= 12 && <span>{formatPct(row.target_pct)}</span>}
        </div>)}
      </div> : <span className="portfolio-muted">{view.rows?.length ? 'Allocation not fully specified' : 'Not recorded'}</span>}
    </div>)}
    <div className="portfolio-shape-legend">{assets.filter(([key]) => views.some((view) =>
      view.rows.some((row) => keyFor(row) === key && row.target_pct >= 12))).map(([key, asset]) =>
      <span key={key}><i className="portfolio-shape-swatch" style={{ '--segment-index': colour.get(key) }} />{assetLabel(asset)}</span>)}</div>
    <details className="portfolio-shape-details"><summary>Allocation breakdown</summary>
      <div className="portfolio-memo-table"><table>
        <thead><tr><th>Exposure</th>{views.map((view) => <th key={view.id}>{view.title}</th>)}</tr></thead>
        <tbody>{assets.map(([key, asset]) => <tr key={key}>
          <th scope="row"><i className="portfolio-shape-swatch" style={{ '--segment-index': colour.get(key) }} />{assetLabel(asset)}</th>
          {views.map((view) => {
            const row = view.rows.find((item) => keyFor(item) === key);
            return <td key={view.id}>{row?.target_pct != null ? `${Number(row.target_pct).toFixed(2)}%` : '\u2014'}</td>;
          })}
        </tr>)}</tbody>
      </table></div>
    </details>
  </section>;
}


function CurrentSleeveDecisions({ rows }) {
  const decisions = Array.isArray(rows) ? rows : [];
  if (!decisions.length) return null;
  return (
    <section className="portfolio-panel allocation-panel">
      <div className="portfolio-section-head">
        <div>
          <h2>Current Sleeve Decisions</h2>
        </div>
      </div>
      <div className="portfolio-allocation-grid current-sleeves" role="table" aria-label="Current sleeve decisions">
        <div className="portfolio-allocation-grid-row header" role="row">
          <span role="columnheader">Current Sleeve</span>
          <span role="columnheader">Current</span>
          <span role="columnheader">Direction</span>
          <span role="columnheader">Related</span>
          <span role="columnheader">Rationale</span>
        </div>
        {decisions.map((row, idx) => {
          const action = String(row?.action || 'REVIEW').toUpperCase();
          return (
            <div className="portfolio-allocation-grid-row" role="row" key={`${row?.asset_class || idx}-current`}>
              <span role="cell">
                <strong>{assetLabel(row, 'Unnamed sleeve', { caps: true })}</strong>
              </span>
              <span role="cell">{formatPct(row?.current_pct)}</span>
              <span role="cell"><mark className={`portfolio-action ${toneForAction(action)}`}>{action}</mark></span>
              <span role="cell">{sentence(row?.related_or_substitute_exposure, 'n/a')}</span>
              <div role="cell" className="markdown-content"><ReactMarkdown remarkPlugins={[remarkGfm]}>{sentence(row?.allocator_commentary || row?.rationale, 'No final assessment recorded.')}</ReactMarkdown></div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RunList({ runs, selectedRunId, onSelect, onRefresh, isLoading }) {
  return (
    <aside className="portfolio-run-list">
      <div className="portfolio-run-list-head">
        <div>
          <h2>Saved Memos</h2>
          <p>{runs.length} saved runs</p>
        </div>
        <button type="button" onClick={onRefresh} disabled={isLoading}>Refresh</button>
      </div>
      <div className="portfolio-run-scroll">
        {runs.length ? runs.map((run) => (
          <button
            type="button"
            key={run.id}
            className={`portfolio-run-card ${run.id === selectedRunId ? 'active' : ''}`}
            aria-pressed={run.id === selectedRunId}
            onClick={() => onSelect(run.id)}
          >
            <strong>{cleanRunLabel(run.label)}</strong>
            <span>{formatDate(run.updated_at)}</span>
            {run.analysis_health?.status === 'incomplete' && <span>Analysis incomplete</span>}
          </button>
        )) : (
          <div className="portfolio-empty-list">No portfolio positioning memos found yet.</div>
        )}
      </div>
    </aside>
  );
}

export default function PortfolioPositioningLab() {
  const [theme, setTheme] = useState(getInitialTheme);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(getInitialRunId);
  const [loadedPayload, setPayload] = useState(null);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [isLoadingRun, setIsLoadingRun] = useState(false);
  const [error, setError] = useState('');
  const listRequest = useRef(0);
  const payload = loadedPayload?.id === selectedRunId ? loadedPayload : null;

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Theme switching still works when browser storage is unavailable.
    }
  }, [theme]);

  const loadRuns = useCallback(async () => {
    const request = ++listRequest.current;
    setIsLoadingRuns(true);
    setError('');
    try {
      const response = await api.listPortfolioPositioningRuns(50);
      if (request !== listRequest.current) return;
      const nextRuns = Array.isArray(response?.runs) ? response.runs : [];
      setRuns(nextRuns);
    } catch (err) {
      if (request === listRequest.current) setError(err instanceof Error ? err.message : 'Failed to load portfolio memo list');
    } finally {
      if (request === listRequest.current) setIsLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
    return () => { listRequest.current += 1; };
  }, [loadRuns]);

  useEffect(() => {
    if (!selectedRunId && runs[0]?.id) {
      setSelectedRunId(runs[0].id);
      navigateToRun(runs[0].id);
    }
  }, [selectedRunId, runs]);

  useEffect(() => {
    if (!selectedRunId) return undefined;
    const controller = new AbortController();
    const load = async () => {
      setIsLoadingRun(true);
      setError('');
      try {
        const response = await api.getPortfolioMemo(selectedRunId, { signal: controller.signal });
        if (!controller.signal.aborted) setPayload(response);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Failed to load portfolio memo');
          setPayload(null);
        }
      } finally {
        if (!controller.signal.aborted) setIsLoadingRun(false);
      }
    };
    load();
    return () => controller.abort();
  }, [selectedRunId]);

  const structured = payload?.structured_data || {};
  const independent = Number(payload?.workflow_version || structured.workflow_version) >= 3;
  const diagnosis = structured.portfolio_diagnosis || {};
  const strategic = structured.strategic_view || {};
  const themeView = investmentTheme(strategic);
  const macro = structured.macro_scorecard || {};
  const memoMarkdown = payload?.memo_markdown || payload?.chairman_memo_markdown || payload?.analyst_memo_markdown || '';

  const marketSummaryParts = [];
  for (const [label, value] of [['Growth', macro.growth], ['Inflation', macro.inflation],
    ['Rates', macro.rates || macro.interest_rates_and_yield_curve], ['Liquidity', macro.liquidity]]) {
    const assessment = sentence(value, '');
    if (assessment) marketSummaryParts.push(`${label}: ${assessment}`);
  }
  const marketSummary = marketSummaryParts.join(' · ');

  const handleSelectRun = useCallback((runId) => {
    setSelectedRunId(runId);
    navigateToRun(runId);
    if (runId && !runs.some((run) => run.id === runId)) loadRuns();
  }, [runs, loadRuns]);

  const handleDelete = async () => {
    if (!selectedRunId) return;
    const ok = window.confirm('Delete this portfolio positioning memo?');
    if (!ok) return;
    try {
      await api.deletePortfolioPositioningRun(selectedRunId);
      setRuns((current) => current.filter((run) => run.id !== selectedRunId));
      setPayload(null);
      setIsLoadingRun(false);
      setSelectedRunId('');
      navigateToRun('');
      await loadRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete portfolio memo');
    }
  };

  return (
    <div className="portfolio-lab-root" data-theme={theme}>
      <header className="portfolio-lab-header">
        <div>
          <p className="portfolio-kicker">Alpha Edge Intelligence</p>
          <h1>Portfolio Analysis</h1>
          <p>Top-down portfolio analysis and durable Portfolio Memo review.</p>
        </div>
        <div className="portfolio-header-actions">
          <div className="portfolio-theme-switch" role="group" aria-label="Portfolio color theme">
            <button type="button" aria-pressed={theme === 'light'} onClick={() => setTheme('light')}>Light</button>
            <button type="button" aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}>Dark</button>
          </div>
          <button type="button" onClick={() => window.history.back()}>Back</button>
          <button type="button" onClick={handleDelete} disabled={!selectedRunId}>Delete Memo</button>
        </div>
      </header>

      {error ? <div className="portfolio-error">{error}</div> : null}

      <main className="portfolio-lab-shell">
        <RunList
          runs={runs}
          selectedRunId={selectedRunId}
          onSelect={handleSelectRun}
          onRefresh={loadRuns}
          isLoading={isLoadingRuns}
        />

        <section className="portfolio-workspace">
          <ActivePortfolioRuns onOpen={handleSelectRun} />
          {isLoadingRun ? <div className="portfolio-loading">Loading selected memo...</div> : null}
          {!payload && !isLoadingRun ? (
            <div className="portfolio-empty-state">
              <h2>No portfolio memo selected</h2>
              <p>Select a saved portfolio positioning memo from the list.</p>
            </div>
          ) : null}

          {payload ? (
            <>
              <section className="portfolio-hero-card">
                <div>
                  <p className="portfolio-kicker">{formatDate(payload.updated_at)}</p>
                  <h2>{cleanRunLabel(payload.label)}</h2>
                  <Synopsis value={structured.executive_summary} />
                </div>
                <div className="portfolio-hero-meta" role="list" aria-label="Portfolio memo key metrics">
                  <StatCard label="Cash Now" value={formatPct(diagnosis.current_cash_pct)} />
                  {!structured.is_partial && <>
                    <StatCard label="Proposed Cash" value={formatPct(structured.decision?.funding?.rows?.find((row) => row.asset_class?.toLowerCase() === 'cash')?.target_pct)} />
                    <StatCard label="Primary Theme" value={themeView.title} />
                  </>}
                </div>
                {!structured.is_partial && (themeView.paragraphs.length > 0 || themeView.alternative) &&
                  <details className="portfolio-theme-rationale" key={payload.id}>
                    <summary>Investment rationale<ChevronDown size={16} aria-hidden="true" /></summary>
                    <div className="markdown-content portfolio-theme-rationale-body">
                      {themeView.paragraphs.map((paragraph, index) => <ReactMarkdown key={index} remarkPlugins={[remarkGfm]}>{paragraph}</ReactMarkdown>)}
                      {themeView.alternative && <div className="portfolio-theme-alternative">
                        <h3>Alternative scenario</h3>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{themeView.alternative}</ReactMarkdown>
                      </div>}
                    </div>
                  </details>}
              </section>

              {!structured.is_partial && <div className="portfolio-grid two">
                <section className="portfolio-panel">
                  <h3>Current Shape</h3>
                  <p>{sentence(diagnosis.current_structure, 'No current-structure summary was saved.')}</p>
                  <div className="portfolio-chip-row">
                    {listFrom(diagnosis.dominant_asset_classes).slice(0, 6).map((item) => (
                      <span key={item}>{humanizeAssetLabel(item)}</span>
                    ))}
                  </div>
                </section>
                <section className="portfolio-panel">
                  <h3>Strategic View</h3>
                  <p>{sentence(strategic.notes?.[0] || structured.confidence_note, 'No strategic note was saved.')}</p>
                  {marketSummary ? <p className="portfolio-muted">{marketSummary}</p> : null}
                </section>
              </div>}

              {independent && <PortfolioShapes views={structured.portfolio_shapes} />}
              {!structured.is_partial && <>
                <CurrentSleeveDecisions rows={structured.current_sleeve_decisions} />
                <AllocationTable rows={structured.asset_class_targets} funded={structured.decision?.funding?.status === 'balanced'} independent={independent} />
              </>}
              <section className="portfolio-panel memo-panel" data-partial={structured.is_partial || undefined} aria-label="Portfolio memo">
                <div className="portfolio-section-head"><h2>Memo Text</h2></div>
                {memoMarkdown ? <PortfolioMemoContent markdown={memoMarkdown} independent={independent} executiveSummary={structured.executive_summary}
                  allocationTables={independent && !structured.is_partial && structured.asset_class_targets?.length > 0} /> : <p className="portfolio-muted">No memo markdown was saved.</p>}
              </section>
              <PortfolioMemoAppendix key={payload.id} runId={payload.id} onRecovered={handleSelectRun} />
            </>
          ) : null}
        </section>
      </main>
    </div>
  );
}
