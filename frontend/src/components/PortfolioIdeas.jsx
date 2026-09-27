import { useEffect, useState } from 'react';
import { Plus, Trash2, Save } from 'lucide-react';
import { api } from '../api';
import './PortfolioIdeas.css';

export function PortfolioUserAdjustment({ payload }) {
  const [opened, setOpened] = useState(false);
  const [history, setHistory] = useState([]);
  const [rows, setRows] = useState(() => (payload.structured_data?.asset_class_targets || []).map((row) => ({
    asset_class: row.asset_class, display_name: row.display_name || row.asset_class, target_pct: row.target_pct ?? '',
  })));
  const [name, setName] = useState('My alternative');
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!opened) return undefined;
    let active = true;
    api.listPortfolioReviews(payload.id).then(({ reviews }) => {
      if (active) setHistory((reviews || []).filter((review) => review.user_adjustment));
    }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [opened, payload.id]);
  const total = rows.reduce((sum, row) => sum + (Number(row.target_pct) || 0), 0);
  const valid = name.trim() && rows.length && rows.every((row) => row.display_name.trim() && row.target_pct !== '' && Number.isFinite(Number(row.target_pct)) && Number(row.target_pct) >= 0 && Number(row.target_pct) <= 100);
  function update(next) { setRows(next); setSaved(null); }
  async function save() {
    setBusy(true); setError('');
    const targets = rows.map((row) => ({ ...row, asset_class: row.asset_class || `user_${row.display_name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')}`,
      target_pct: Number(row.target_pct), min_pct: Number(row.target_pct), max_pct: Number(row.target_pct) }));
    if (new Set(targets.map((row) => row.asset_class)).size !== targets.length) {
      setError('Each exposure must appear once.'); setBusy(false); return;
    }
    try {
      const result = await api.reviewPortfolioRun(payload.id, { user_adjustment: true, alternatives: [{ name: name.trim(), asset_class_targets: targets,
        current_sleeve_actions: (payload.portfolio_snapshot?.asset_classes || []).map((row) => ({
          asset_class: row.asset_class, target_pct: targets.find((target) => target.asset_class === row.asset_class)?.target_pct ?? 0,
          action: targets.some((target) => target.asset_class === row.asset_class) ? 'REVIEW' : 'EXIT',
        })) }] });
      setSaved(result);
      setHistory((previous) => [result, ...previous]);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <details className="portfolio-ideas portfolio-adjustment" onToggle={(event) => {
    if (event.target === event.currentTarget && event.currentTarget.open) setOpened(true);
  }}><summary>User adjustment</summary>
    <p>Personal alternative, not a model recommendation. Recorded holdings and the original memo remain unchanged.</p>
    <label>Name<input value={name} onChange={(event) => { setName(event.target.value); setSaved(null); }} /></label>
    {rows.map((row, index) => <div className="portfolio-adjustment-row" key={index}>
      <input aria-label={`Exposure ${index + 1}`} value={row.display_name} disabled={busy || Boolean(row.asset_class)}
        onChange={(event) => update(rows.map((item, i) => i === index ? { ...item, display_name: event.target.value } : item))} />
      <input type="number" min="0" max="100" step="0.1" aria-label={`Target ${index + 1} percent`} value={row.target_pct} disabled={busy}
        onChange={(event) => update(rows.map((item, i) => i === index ? { ...item, target_pct: event.target.value } : item))} />
      <button type="button" className="portfolio-idea-icon" title={`Remove exposure ${index + 1}`} aria-label={`Remove exposure ${index + 1}`} disabled={busy}
        onClick={() => update(rows.filter((_, i) => i !== index))}><Trash2 size={16} /></button>
    </div>)}
    <p>Total: {total.toFixed(1)}%. {total > 100 ? `${(total - 100).toFixed(1)}% overallocated.` : `${(100 - total).toFixed(1)}% unallocated.`}</p>
    <div className="portfolio-idea-actions">
      <button type="button" disabled={busy} onClick={() => update([...rows, { asset_class: '', display_name: '', target_pct: '' }])}><Plus size={16} />Add exposure</button>
      <button type="button" disabled={!valid || busy} onClick={save}><Save size={16} />Save alternative</button>
    </div>
    {saved && <p role="status">Saved separately. {saved.alternatives?.[0]?.funding?.status === 'balanced' ? 'Reference weights balance.' : 'Funding remains unresolved.'} Not reviewed by a model.</p>}
    {history.map((review) => <details key={review.review_id || review.as_of} className="portfolio-saved-adjustment">
      <summary>{review.alternatives?.[0]?.name || 'User alternative'} · {new Date(review.as_of).toLocaleDateString()}</summary>
      <ul>{review.alternatives?.[0]?.funding?.rows?.map((row) => <li key={row.asset_class}>{row.display_name || row.asset_class}: {row.target_pct ?? 'Unresolved'}%</li>)}</ul>
    </details>)}
    {error && <p className="portfolio-error" role="alert">{error}</p>}
  </details>;
}
