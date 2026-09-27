const DEFAULT_API_BASE = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8001';
export const API_BASE = import.meta.env?.VITE_API_BASE || DEFAULT_API_BASE;
const TOKEN_KEY = 'LLM_COUNCIL_API_TOKEN';
let memoryToken;
let snapshot = { status: 'checking', submitting: false, error: '' };
let checkPromise;
let revision = 0;
const listeners = new Set();

export const getApiAuthState = () => snapshot;
export function subscribeApiAuth(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function update(state) {
  snapshot = state;
  listeners.forEach((listener) => listener());
}

function storedToken() {
  if (memoryToken !== undefined) return memoryToken;
  try {
    return window.localStorage.getItem(TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

function saveToken(token, remember = false) {
  memoryToken = token;
  try {
    if (remember) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Session access still works when persistent storage is unavailable.
  }
}

function withAuthHeaders(init, token) {
  const headers = new Headers(init.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

async function verifyToken(token) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_BASE}/api/auth/status`, withAuthHeaders({ signal: controller.signal, cache: 'no-store' }, token));
    if (response.status === 401) return false;
    if (!response.ok || (await response.json()).authenticated !== true) throw new Error('Authentication check unavailable');
    return true;
  } finally {
    clearTimeout(timeout);
  }
}

export function checkApiAccess() {
  if (checkPromise) return checkPromise;
  const attempt = ++revision;
  update({ status: 'checking', submitting: false, error: '' });
  checkPromise = (async () => {
    try {
      const accepted = await verifyToken(storedToken());
      if (attempt !== revision) return;
      if (!accepted) saveToken('');
      update({ status: accepted ? 'authenticated' : 'required', submitting: false, error: '' });
    } catch {
      if (attempt === revision) update({ status: 'unavailable', submitting: false, error: 'Unable to connect to Alpha Edge. Please try again.' });
    } finally {
      checkPromise = null;
    }
  })();
  return checkPromise;
}

export async function signInApiToken(value, remember = false) {
  if (snapshot.submitting) return false;
  const token = String(value || '').trim();
  if (!token) {
    update({ status: 'required', submitting: false, error: 'Enter your API token.' });
    return false;
  }
  const attempt = ++revision;
  update({ status: 'required', submitting: true, error: '' });
  try {
    const accepted = await verifyToken(token);
    if (attempt !== revision) return false;
    if (!accepted) {
      update({ status: 'required', submitting: false, error: "That token wasn't accepted. Please try again." });
      return false;
    }
    saveToken(token, remember);
    update({ status: 'authenticated', submitting: false, error: '' });
    return true;
  } catch {
    if (attempt === revision) update({ status: 'required', submitting: false, error: 'Unable to connect to Alpha Edge. Please try again.' });
    return false;
  }
}

export async function authFetch(url, init = {}) {
  let token = storedToken();
  let response = await fetch(url, withAuthHeaders(init, token));
  // A late response from an old session must not invalidate a newer sign-in.
  if (response.status === 401 && storedToken() && storedToken() !== token) {
    token = storedToken();
    response = await fetch(url, withAuthHeaders(init, token));
  }
  if (response.status === 401 && storedToken() === token && snapshot.status === 'authenticated') {
    revision += 1;
    saveToken('');
    update({ status: 'required', submitting: false, error: 'Your session has expired. Sign in again.' });
  }
  return response;
}
