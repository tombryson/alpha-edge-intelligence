import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import './ModelRoutingConsole.css';

function modelIdentifier(value) {
  if (typeof value === 'string') return value;
  return typeof value?.model === 'string' ? value.model : '';
}

function isRoleRoute(route) {
  const value = route.effective_value;
  return route.kind === 'role' || Boolean(value && typeof value === 'object' && !Array.isArray(value) && 'model' in value);
}

function displayValue(value) {
  return Array.isArray(value) ? value.map(modelIdentifier).join(', ') : modelIdentifier(value);
}

function routeModels(route) {
  const value = route?.effective_value;
  return (Array.isArray(value) ? value : [value]).map(modelIdentifier);
}

function sourceLabel(source) {
  if (source === 'runtime_override') return 'Runtime override';
  if (source === 'environment') return 'Configured environment';
  if (source === 'migrated') return 'Initial assignment';
  if (source === 'mixed') return 'Multiple sources';
  return 'Code default';
}

function providerClassName(provider) {
  return String(provider || 'unknown')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-');
}

function formatAuditValue(value) {
  const text = displayValue(value);
  return text || 'No value';
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function formatReleaseDate(value) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return 'Release date unverified';
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  }).format(date);
}

function formatAge(ageDays) {
  if (!Number.isFinite(ageDays)) return '';
  if (ageDays === 0) return 'today';
  if (ageDays === 1) return '1 day ago';
  return `${ageDays} days ago`;
}

function freshnessLabel(freshness) {
  if (!freshness?.released_at) return 'Release date unverified';
  return (
    <>
      Released {formatReleaseDate(freshness.released_at)}
      <span className={freshness.age_days > 60 ? 'model-route-freshness-age is-overdue' : 'model-route-freshness-age'}>
        {' '}· {formatAge(freshness.age_days)}
      </span>
    </>
  );
}

function freshnessTitle(freshness) {
  if (!freshness?.released_at) return 'No reviewed provider release date is recorded for this model.';
  const verified = freshness.last_verified_at
    ? ` Last reviewed ${formatReleaseDate(freshness.last_verified_at)}.`
    : '';
  return `${freshness.date_basis}.${verified}`;
}

function RouteHeading({ route, description, collapsible }) {
  if (collapsible || route.kind === 'group') return (
    <details className="model-route-description">
      <summary><h3>{route.layer}</h3></summary>
      <p>{description}</p>
      {route.members && (
        <ul className="model-route-members" aria-label={`${route.layer} stages`}>
          {route.members.map((member) => (
            <li key={member.id}>
              <span>{member.layer}</span>
              {route.mixed && <code>{member.model || 'No model assigned'}</code>}
            </li>
          ))}
        </ul>
      )}
    </details>
  );
  return <div><h3>{route.layer}</h3><p>{description}</p></div>;
}

function RouteRow({ route, onSave, onReset, busy, collapseDescription }) {
  const [models, setModels] = useState(() => routeModels(route));
  const [editingIndex, setEditingIndex] = useState(null);
  const [draft, setDraft] = useState('');
  const listRoute = route.kind === 'list';
  const directXai = route.provider === 'xAI';
  const conventionId = `${route.id}-model-convention`;

  const beginEdit = (index) => {
    setDraft(models[index] || '');
    setEditingIndex(index);
  };

  const cancelEdit = () => {
    if (editingIndex !== null && !models[editingIndex]) {
      setModels((current) => current.filter((_, index) => index !== editingIndex));
    }
    setDraft('');
    setEditingIndex(null);
  };

  const saveModel = async () => {
    if (editingIndex === null) return;
    const savedModel = draft.trim();
    const nextModels = models.map((model, index) => (
      index === editingIndex ? savedModel : model
    ));
    if (!await onSave(route.id, listRoute ? nextModels : nextModels[0])) return;
    setDraft('');
    setEditingIndex(null);
  };

  const addModel = () => {
    const nextIndex = models.length;
    setModels((current) => [...current, '']);
    setDraft('');
    setEditingIndex(nextIndex);
  };

  const removeModel = async (index) => {
    const nextModels = models.filter((_, modelIndex) => modelIndex !== index);
    await onSave(route.id, nextModels);
  };

  const reset = async () => {
    if (!await onReset(route.id)) return;
    setEditingIndex(null);
  };

  return (
    <article className={`model-route-row${editingIndex !== null ? ' is-editing' : ''}`}>
      <div className="model-route-row-meta">
        <RouteHeading route={route} collapsible={collapseDescription} description={route.description} />
        <div className="model-route-provenance">
          <span className={`model-route-provider provider-${providerClassName(route.provider)}`}>{route.provider}</span>
          <em className={`model-route-source source-${route.source}`}>{sourceLabel(route.source)}</em>
        </div>
      </div>

      <div className="model-route-value" aria-label={`${route.layer} model assignments`}>
        <ol className="model-route-model-list">
          {models.map((model, index) => (
            <li key={`${route.id}-${index}`} className={editingIndex === index ? 'is-editing' : ''}>
              {listRoute && (
                <span className="model-route-model-index">{String(index + 1).padStart(2, '0')}</span>
              )}
              {editingIndex === index ? (
                <input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  aria-label={`${route.layer} model ${index + 1}`}
                  aria-describedby={directXai ? conventionId : undefined}
                  placeholder={directXai ? 'grok-4.6' : route.provider === 'Parallel' ? 'ultra4x' : undefined}
                  autoComplete="off"
                  spellCheck="false"
                />
              ) : (
                <code>{model}</code>
              )}
              {editingIndex !== index && (
                <span
                  className={`model-route-freshness freshness-${route.model_freshness?.[model]?.status || 'unverified'}`}
                  title={freshnessTitle(route.model_freshness?.[model])}
                >
                  <i aria-hidden="true" />
                  {freshnessLabel(route.model_freshness?.[model])}
                </span>
              )}
              <div className="model-route-line-actions">
                {editingIndex === index ? (
                  <>
                    <button type="button" className="model-route-save" onClick={saveModel} disabled={busy || !draft.trim()}>Save</button>
                    <button type="button" onClick={cancelEdit} disabled={busy}>Cancel</button>
                    {listRoute && models.length > 1 && (
                      <button type="button" className="model-route-remove" onClick={() => removeModel(index)} disabled={busy}>Remove</button>
                    )}
                  </>
                ) : (
                  <button type="button" className="model-route-edit" onClick={() => beginEdit(index)} disabled={busy}>Edit</button>
                )}
              </div>
            </li>
          ))}
        </ol>
        {directXai && (
          <p className="model-route-convention" id={conventionId}>
            Direct xAI: <code>grok-4.6</code> (no <code>x-ai/</code> prefix).
          </p>
        )}
        {listRoute && (
          <button type="button" className="model-route-add" onClick={addModel} disabled={busy}>Add model</button>
        )}
      </div>

      <div className="model-route-actions">
        {route.source === 'runtime_override' && (
          <button type="button" className="model-route-reset" onClick={reset} disabled={busy}>Reset</button>
        )}
      </div>
    </article>
  );
}

function RoleRouteRow({ route, onSave, onReset, busy, saveError, collapseDescription }) {
  const assignment = { model: modelIdentifier(route.effective_value) };
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(assignment.model);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const beginEdit = () => {
    setDraft(assignment.model);
    setError('');
    setEditing(true);
  };

  const save = async (event) => {
    event.preventDefault();
    if (!draft.trim()) {
      setError('A model is required.');
      inputRef.current?.focus();
      return;
    }
    if (await onSave(route.id, { model: draft.trim() })) setEditing(false);
  };

  const visibleError = error || saveError || route.validation_error;
  const freshness = route.model_freshness?.[assignment.model];

  return (
    <article aria-label={route.layer} className={`model-route-row model-route-role${route.kind === 'group' ? ' model-route-shared' : ''}${editing ? ' is-editing' : ''}`}>
      <div className="model-route-row-meta">
        <RouteHeading route={route} collapsible={collapseDescription} description={route.description} />
        <div className="model-route-provenance">
          <span className={`model-route-provider provider-${providerClassName(route.provider)}`}>{route.provider}</span>
          <em className={`model-route-source source-${route.source}`}>{sourceLabel(route.source)}</em>
        </div>
      </div>
      <form className="model-route-value" onSubmit={save} aria-label={`${route.layer} assignment`}>
        <ol className="model-route-model-list">
          <li className={editing ? 'is-editing' : ''}>
            {editing ? (
              <input
                ref={inputRef}
                value={draft}
                onChange={(event) => { setDraft(event.target.value); setError(''); }}
                aria-label={`${route.layer} model`}
                aria-invalid={Boolean(visibleError)}
                aria-describedby={visibleError ? `${route.id}-error` : undefined}
                autoComplete="off"
                spellCheck="false"
                disabled={busy}
              />
            ) : route.mixed ? (
              <span className="model-route-unassigned is-mixed">Multiple models assigned</span>
            ) : assignment.model ? (
              <code>{assignment.model}</code>
            ) : (
              <span className="model-route-unassigned">No model assigned</span>
            )}
            {!editing && assignment.model && (
              <span className={`model-route-freshness freshness-${freshness?.status || 'unverified'}`} title={freshnessTitle(freshness)}>
                <i aria-hidden="true" />{freshnessLabel(freshness)}
              </span>
            )}
            <div className="model-route-line-actions">
              {editing ? (
                <>
                  <button key="save" type="submit" className="model-route-save" disabled={busy || !draft.trim()}
                    title={route.members ? `Save for ${route.members.length} ${route.members.length === 1 ? 'stage' : 'stages'}` : undefined}>Save</button>
                  <button type="button" onClick={() => { setEditing(false); setError(''); }} disabled={busy}>Cancel</button>
                </>
              ) : (
                <button key="edit" type="button" className="model-route-edit" onClick={() => beginEdit()} disabled={busy}>Edit</button>
              )}
            </div>
          </li>
        </ol>
        {visibleError && <p className="model-route-role-error" role="alert" id={`${route.id}-error`}>{visibleError}</p>}
      </form>
      <div className="model-route-actions">
        {(route.has_override ?? route.source === 'runtime_override') && (
          <button type="button" className="model-route-reset" onClick={() => onReset(route.id)} disabled={busy}>Reset</button>
        )}
      </div>
    </article>
  );
}

export default function ModelRoutingConsole() {
  const [payload, setPayload] = useState({ routes: [], audit: [] });
  const [loading, setLoading] = useState(true);
  const [busyRoute, setBusyRoute] = useState('');
  const [error, setError] = useState('');
  const [errorRoute, setErrorRoute] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    setErrorRoute('');
    try {
      setPayload(await api.listModelRoutes());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model routing');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const groups = useMemo(() => {
    const grouped = new Map();
    const sharedGroups = payload.route_groups || [];
    const memberIds = new Set(sharedGroups.flatMap((group) => group.members.map((member) => member.id)));
    (payload.routes || []).forEach((route) => {
      const rows = grouped.get(route.app) || [];
      if (!memberIds.has(route.id)) rows.push(route);
      grouped.set(route.app, rows);
    });
    sharedGroups.forEach((route) => {
      const rows = grouped.get(route.app) || [];
      rows.push(route);
      grouped.set(route.app, rows);
    });
    return Array.from(grouped.entries());
  }, [payload.routes, payload.route_groups]);

  const save = async (routeId, value) => {
    setBusyRoute(routeId);
    setError('');
    setErrorRoute('');
    try {
      setPayload(await api.updateModelRoute(routeId, value));
      return true;
    } catch (err) {
      setErrorRoute(routeId);
      setError(err instanceof Error ? err.message : 'Failed to update model route');
      return false;
    } finally {
      setBusyRoute('');
    }
  };

  const reset = async (routeId) => {
    setBusyRoute(routeId);
    setError('');
    setErrorRoute('');
    try {
      setPayload(await api.clearModelRoute(routeId));
      return true;
    } catch (err) {
      setErrorRoute(routeId);
      setError(err instanceof Error ? err.message : 'Failed to reset model route');
      return false;
    } finally {
      setBusyRoute('');
    }
  };

  return (
    <main className="model-routing-console">
      <header className="model-routing-header">
        <div>
          <span className="model-routing-kicker">System Configuration</span>
          <h1>Model Routing</h1>
          <p>Current model assignments across the Alpha Edge runtime.</p>
        </div>
        <div className="model-routing-header-actions">
          <span>New work uses saved overrides</span>
          <button type="button" onClick={load} disabled={loading || Boolean(busyRoute)}>Refresh</button>
        </div>
      </header>

      {error && <div className="model-routing-error" role="alert">{error}</div>}

      {loading ? (
        <div className="model-routing-loading">Loading model assignments...</div>
      ) : (
        <div className="model-routing-groups">
          {groups.map(([app, routes], groupIndex) => (
            <section className="model-routing-group" key={app} aria-labelledby={`routing-${app.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>
              <header>
                <h2 id={`routing-${app.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>{app}</h2>
                <span>{routes.length} {routes.every((route) => route.kind === 'group') ? 'model groups' : 'assignments'}</span>
              </header>
              {(payload.configuration_errors || []).filter((item) => item.app === app).map((item) => (
                <div className="model-routing-error" role="alert" key={item.detail}>
                  Portfolio runs cannot start: {item.detail}
                </div>
              ))}
              <div className="model-routing-rows">
                {routes.map((route) => {
                  const Row = isRoleRoute(route) ? RoleRouteRow : RouteRow;
                  return <Row
                    key={`${route.id}:${JSON.stringify(route.effective_value)}:${Boolean(route.mixed)}`}
                    route={route}
                    collapseDescription={groups.findIndex(([name]) => name === 'Portfolio Analysis') >= 0 && groupIndex >= groups.findIndex(([name]) => name === 'Portfolio Analysis')}
                    onSave={save}
                    onReset={reset}
                    busy={Boolean(busyRoute)}
                    saveError={errorRoute === route.id ? error : ''}
                  />;
                })}
              </div>
            </section>
          ))}
        </div>
      )}

      {!loading && Boolean(payload.audit?.length) && (
        <section className="model-routing-audit" aria-labelledby="routing-audit-title">
          <header>
            <h2 id="routing-audit-title">Recent Changes</h2>
          </header>
          <div>
            {payload.audit.slice(0, 8).map((entry, index) => (
              <p key={`${entry.at}-${entry.route_id}-${index}`}>
                <time>{formatTime(entry.at)}</time>
                <span>{entry.action === 'clear_override' ? 'Reset' : entry.action === 'migrate_role' ? 'Initialised' : 'Set'} {entry.label || entry.route_id}</span>
                <code>{formatAuditValue(entry.effective_value)}</code>
              </p>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
