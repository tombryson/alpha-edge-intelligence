import { useEffect, useRef, useState } from 'react';
import { Activity, CheckCircle2, AlertTriangle, ArrowUpRight, Square } from 'lucide-react';
import { api } from '../api';
import './PortfolioRunProgress.css';

const running = (job) => ['running', 'queued', 'cancelling'].includes(job.status);
function elapsed(value, clock) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Unavailable';
  const seconds = Math.max(0, Math.floor((clock - Date.parse(value)) / 1000));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function PortfolioRunProgress({ job, error = '', onOpen, onCancel }) {
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState('');
  const stop = async () => {
    setStopping(true);
    setStopError('');
    try { await onCancel(job.job_id); }
    catch (err) { setStopError(err.message); }
    finally { setStopping(false); }
  };
  const [clock, setClock] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const progress = job.execution_progress;
  const checkpoint = progress?.checkpoint;
  const active = running(job);
  const Icon = active ? Activity : job.status === 'succeeded' ? CheckCircle2 : AlertTriangle;
  const title = job.status === 'cancelling' ? 'Stopping portfolio analysis' : active ? 'Portfolio analysis running' : job.status === 'succeeded' ? 'Portfolio analysis complete' : 'Portfolio analysis stopped';
  const end = !active && job.finished_at ? Date.parse(job.finished_at) : clock;
  return <section className="portfolio-run-progress" aria-label="Live portfolio progress">
    <div className="portfolio-progress-heading">
      <strong><Icon size={17} aria-hidden="true" />{title}</strong>
      {active && onCancel && <button type="button" onClick={stop} disabled={stopping || job.status === 'cancelling'}><Square size={14} aria-hidden="true" />{stopping || job.status === 'cancelling' ? 'Stopping...' : 'Stop analysis'}</button>}
      {!active && job.run_id && onOpen && <button type="button" onClick={() => onOpen(job.run_id)}>Open memo <ArrowUpRight size={16} /></button>}
    </div>
    <p className="portfolio-progress-phase" role="status">{progress?.message || job.stage_message || job.status}</p>
    {progress?.research_coverage?.total > 0 && <p className="portfolio-progress-heartbeat">
      Research: {progress.research_coverage.answered} of {progress.research_coverage.total} questions answered
      {progress.research_coverage.unresolved > 0 ? ` / ${progress.research_coverage.unresolved} still open` : ''}
    </p>}
    {progress?.research_budget?.parallel_funding?.status === 'insufficient' && <p role="alert" className="portfolio-progress-error">Parallel credit required. Completed research is saved; unanswered questions remain open.</p>}
    {error && <p role="alert" className="portfolio-progress-error">Updates unavailable: {error}. Showing the last received status.</p>}
    {stopError && <p role="alert" className="portfolio-progress-error">{stopError}</p>}
    {checkpoint?.status === 'failed' && <p role="alert" className="portfolio-progress-error">The latest checkpoint could not be saved. {checkpoint.saved_at || checkpoint.resumed ? 'Only the previous checkpoint is recoverable.' : 'No recovery checkpoint has been saved yet.'}</p>}
    {checkpoint?.artifact_status === 'failed' && <p role="alert" className="portfolio-progress-error">The memo preview could not be updated. The recovery checkpoint is saved.</p>}
    <dl className="portfolio-progress-times">
      <div><dt>Elapsed</dt><dd>{elapsed(job.started_at || job.created_at, end)}</dd></div>
      <div><dt>Last response</dt><dd>{progress?.last_result_at ? `${elapsed(progress.last_result_at, clock)} ago` : 'Not received yet'}</dd></div>
      <div><dt>Checkpoint saved</dt><dd>{checkpoint?.saved_at ? `${elapsed(checkpoint.saved_at, clock)} ago` : checkpoint?.resumed ? 'Earlier run' : 'Not saved yet'}{checkpoint?.completed_tasks > 0 && <span> / {checkpoint.completed_tasks} tasks</span>}</dd></div>
    </dl>
    <details className="portfolio-progress-details">
      <summary>Requests and phases{active && progress ? ` / ${progress.active_requests?.length || 0} active / ${progress.queued_count || 0} queued` : ''}</summary>
      <div className="portfolio-progress-scroll">
        {job.heartbeat_at && <p className="portfolio-progress-heartbeat">Last worker heartbeat: {elapsed(job.heartbeat_at, clock)} ago</p>}
        {!progress && <p>Detailed progress was not recorded for this run.</p>}
        {active && [...(progress?.active_requests || []), ...(progress?.queued_requests || [])].map((request) => <div className="portfolio-progress-request" key={request.id}>
          <div><strong>{request.label}</strong><code>{request.model || request.provider}</code>{request.retry_reason && <span className="portfolio-progress-retry">{request.retry_reason}</span>}</div>
          <div className="portfolio-progress-request-state">
            <span>{request.activity === 'saving_request' ? 'Saving before dispatch' : request.status === 'running' ? `Running ${elapsed(request.started_at, clock)}` : request.status === 'checking_credit' ? 'Checking credit' : request.status === 'saving' ? 'Saving checkpoint' : `Queued ${elapsed(request.queued_at, clock)}`}</span>
            {request.provider_run_id && <span title={request.provider_run_id}>Provider: {request.provider_status || 'submitted'}</span>}
            {request.attempt > 1 && <span>Attempt {request.attempt}</span>}
          </div>
        </div>)}
        {active && progress?.queued_count > (progress?.queued_requests?.length || 0) && <p>{progress.queued_count - (progress.queued_requests?.length || 0)} more requests queued</p>}
        {progress?.phases?.length > 0 && <div className="portfolio-progress-phases">
          {progress.phases.map((phase) => <div key={phase.id}>
            <span>{phase.label}{phase.facts > 0 && <small>{phase.facts} facts</small>}</span>
            <span>{phase.completed}/{phase.total} {phase.unit}{phase.reused > 0 ? ` / ${phase.reused} reused` : ''}{phase.failed > 0 ? ` / ${phase.failed} failed` : ''}</span>
          </div>)}
        </div>}
      </div>
    </details>
  </section>;
}

export default function ActivePortfolioRuns({ onOpen }) {
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState('');
  const seen = useRef(new Set());
  useEffect(() => {
    let disposed = false;
    let timer;
    const poll = async () => {
      try {
        const response = await api.listAnalysisJobs(100, 'portfolio_positioning');
        if (disposed) return;
        const rows = (response.jobs || []).filter((job) => job.request?.job_type === 'portfolio_positioning');
        rows.filter(running).forEach((job) => seen.current.add(job.job_id));
        setJobs(rows.filter((job) => seen.current.has(job.job_id)));
        setError('');
      } catch (err) { if (!disposed) setError(err.message); }
      if (!disposed) timer = setTimeout(poll, 5000);
    };
    poll();
    return () => { disposed = true; clearTimeout(timer); };
  }, []);
  return <>
    {!jobs.length && error && <p className="portfolio-progress-error" role="alert">Unable to check for running portfolio analyses: {error}</p>}
    {jobs.map((job) => <PortfolioRunProgress key={job.job_id} job={job} error={error} onOpen={onOpen} onCancel={async (id) => {
      const updated = await api.cancelAnalysisJob(id);
      setJobs((current) => current.map((row) => row.job_id === id ? updated : row));
    }} />)}
  </>;
}
