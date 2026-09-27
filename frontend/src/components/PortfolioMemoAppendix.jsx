import { useEffect, useState } from 'react';
import { RotateCw } from 'lucide-react';
import { api } from '../api';
import PortfolioDecisionReview, { PortfolioHealth } from './PortfolioDecisionReview';
import { PortfolioUserAdjustment } from './PortfolioIdeas';

export default function PortfolioMemoAppendix({ runId, onRecovered }) {
  const [opened, setOpened] = useState(false);
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!opened) return undefined;
    const controller = new AbortController();
    api.getPortfolioSupportingAnalysis(runId, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setPayload(result); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [opened, runId, attempt]);
  return (
    <details className="portfolio-memo-appendix" onToggle={(event) => {
      if (event.target === event.currentTarget && event.currentTarget.open) setOpened(true);
    }}>
      <summary>Supporting analysis and review</summary>
      {opened && !payload && !error && <p role="status">Loading supporting analysis...</p>}
      {error && <div className="portfolio-error" role="alert">{error} <button type="button" onClick={() => {
        setError(''); setAttempt((value) => value + 1);
      }}><RotateCw size={14} />Retry</button></div>}
      {payload && <>
        <PortfolioUserAdjustment payload={payload} />
        <PortfolioHealth payload={payload} onRecovered={onRecovered} />
        <PortfolioDecisionReview payload={payload} />
      </>}
    </details>
  );
}
