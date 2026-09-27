import { useEffect, useState, useSyncExternalStore } from 'react';
import { KeyRound, LoaderCircle } from 'lucide-react';
import { checkApiAccess, getApiAuthState, signInApiToken, subscribeApiAuth } from '../apiAuth';
import './ApiAccessGate.css';

function SignInForm({ state }) {
  const [token, setToken] = useState('');
  const [remember, setRemember] = useState(false);
  async function submit(event) {
    event.preventDefault();
    await signInApiToken(token, remember);
  }
  return (
    <form className="api-access-form" onSubmit={submit} aria-label="Sign in to Alpha Edge">
      <label htmlFor="api-access-token">API token</label>
      <input id="api-access-token" name="api_token" type="password" autoComplete="off" autoCapitalize="none"
        spellCheck={false} autoFocus required value={token} onChange={(event) => setToken(event.target.value)}
        disabled={state.submitting} aria-describedby={state.error ? 'api-access-error' : undefined}
        aria-invalid={Boolean(state.error)} />
      <label className="api-access-remember">
        <input type="checkbox" checked={remember} disabled={state.submitting} onChange={(event) => setRemember(event.target.checked)} />
        Remember on this device
      </label>
      {state.error && <p id="api-access-error" className="api-access-error" role="alert">{state.error}</p>}
      <button type="submit" disabled={state.submitting}>
        {state.submitting && <LoaderCircle className="api-access-spinner" size={16} aria-hidden="true" />}
        {state.submitting ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  );
}

export default function ApiAccessGate({ children }) {
  const state = useSyncExternalStore(subscribeApiAuth, getApiAuthState, getApiAuthState);
  useEffect(() => { checkApiAccess(); }, []);
  if (state.status === 'authenticated') return children;
  return (
    <main className="api-access-page">
      <section className="api-access-panel" aria-labelledby="api-access-heading" aria-busy={state.status === 'checking' || state.submitting}>
        <KeyRound size={24} className="api-access-icon" aria-hidden="true" />
        <h1 id="api-access-heading">Alpha Edge Intelligence</h1>
        {state.status === 'checking' ? (
          <p className="api-access-status" role="status"><LoaderCircle size={16} className="api-access-spinner" aria-hidden="true" />Connecting...</p>
        ) : state.status === 'unavailable' ? (
          <><p className="api-access-error" role="alert">{state.error}</p><button type="button" onClick={checkApiAccess}>Try again</button></>
        ) : <SignInForm state={state} />}
      </section>
    </main>
  );
}
