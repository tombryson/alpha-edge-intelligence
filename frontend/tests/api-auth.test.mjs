import test from 'node:test';
import assert from 'node:assert/strict';

const key = 'LLM_COUNCIL_API_TOKEN';
let instance = 0;
async function setup(stored = '') {
  const storage = new Map(stored ? [[key, stored]] : []);
  globalThis.window = { location: { origin: 'https://alpha-edge.test' },
    prompt() { throw new Error('prompt() is not supported'); },
    localStorage: { getItem: (k) => storage.get(k), setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) } };
  const auth = await import(`../src/apiAuth.js?instance=${++instance}`);
  return { auth, storage };
}
const accepted = () => new Response(JSON.stringify({ authenticated: true }), { status: 200 });
const rejected = () => new Response('{}', { status: 401 });

test('checks stored access once, including concurrent StrictMode checks', async () => {
  const { auth } = await setup('existing-test-token');
  let calls = 0;
  globalThis.fetch = async (url, init) => {
    calls += 1;
    assert.equal(url, 'https://alpha-edge.test/api/auth/status');
    assert.equal(init.headers.get('Authorization'), 'Bearer existing-test-token');
    return accepted();
  };
  await Promise.all([auth.checkApiAccess(), auth.checkApiAccess()]);
  assert.equal(calls, 1);
  assert.equal(auth.getApiAuthState().status, 'authenticated');
});

test('missing or expired stored access needs an in-page sign-in, never prompt', async () => {
  const { auth, storage } = await setup('expired-test-token');
  globalThis.fetch = async () => rejected();
  await auth.checkApiAccess();
  assert.equal(auth.getApiAuthState().status, 'required');
  assert.equal(storage.has(key), false);
});

test('invalid credentials are not saved and remain editable', async () => {
  const { auth, storage } = await setup();
  globalThis.fetch = async () => rejected();
  assert.equal(await auth.signInApiToken('wrong-test-token', true), false);
  assert.equal(storage.has(key), false);
  assert.equal(auth.getApiAuthState().submitting, false);
  assert.match(auth.getApiAuthState().error, /wasn't accepted/);
});

test('sign-in validates first, masks persistence by default, and keeps a session token', async () => {
  const { auth, storage } = await setup();
  globalThis.fetch = async (_url, init) => {
    assert.equal(init.headers.get('Authorization'), 'Bearer session-test-token');
    return accepted();
  };
  assert.equal(await auth.signInApiToken(' session-test-token '), true);
  assert.equal(storage.has(key), false);
  assert.equal((await auth.authFetch('/api/templates')).status, 200);
});

test('remembering a verified token uses the existing storage key', async () => {
  const { auth, storage } = await setup();
  globalThis.fetch = async () => accepted();
  await auth.signInApiToken('remembered-test-token', true);
  assert.equal(storage.get(key), 'remembered-test-token');
});

test('unavailable local storage still permits session access', async () => {
  const { auth } = await setup();
  Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } });
  globalThis.fetch = async () => accepted();
  assert.equal(await auth.signInApiToken('private-test-token', true), true);
  globalThis.fetch = async (_url, init) => {
    assert.equal(init.headers.get('Authorization'), 'Bearer private-test-token');
    return accepted();
  };
  await auth.authFetch('/api/templates');
});

test('connection and server errors never masquerade as authenticated access', async () => {
  const { auth, storage } = await setup();
  globalThis.fetch = async () => { throw new TypeError('Offline'); };
  await auth.checkApiAccess();
  assert.equal(auth.getApiAuthState().status, 'unavailable');
  globalThis.fetch = async () => new Response('{}', { status: 503 });
  assert.equal(await auth.signInApiToken('test-token', true), false);
  assert.equal(auth.getApiAuthState().status, 'required');
  assert.equal(storage.has(key), false);
});

test('a misleading 200 response does not authenticate', async () => {
  const { auth } = await setup();
  globalThis.fetch = async () => new Response('{}', { status: 200 });
  await auth.checkApiAccess();
  assert.equal(auth.getApiAuthState().status, 'unavailable');
});

test('expired access returns to sign-in without replaying a write', async () => {
  const { auth, storage } = await setup();
  globalThis.fetch = async () => accepted();
  await auth.signInApiToken('test-token', true);
  let calls = 0;
  globalThis.fetch = async (_url, init) => { calls += 1; assert.equal(init.method, 'POST'); return rejected(); };
  assert.equal((await auth.authFetch('/api/analysis-jobs', { method: 'POST', body: '{}' })).status, 401);
  assert.equal(calls, 1);
  assert.equal(storage.has(key), false);
  assert.equal(auth.getApiAuthState().status, 'required');
});

test('an old 401 response cannot clear a newly verified token', async () => {
  const { auth } = await setup();
  globalThis.fetch = async () => accepted();
  await auth.signInApiToken('old-test-token');
  let finishOld;
  globalThis.fetch = () => new Promise((resolve) => { finishOld = resolve; });
  const pending = auth.authFetch('/api/templates');
  globalThis.fetch = async () => accepted();
  await auth.signInApiToken('new-test-token');
  finishOld(rejected());
  assert.equal((await pending).status, 200);
  assert.equal(auth.getApiAuthState().status, 'authenticated');
});

test('late concurrent failures do not interrupt an in-progress sign-in', async () => {
  const { auth } = await setup();
  globalThis.fetch = async () => accepted();
  await auth.signInApiToken('old-test-token');
  const pendingResponses = [];
  globalThis.fetch = () => new Promise((resolve) => pendingResponses.push(resolve));
  const requests = [auth.authFetch('/api/one'), auth.authFetch('/api/two')];
  pendingResponses[0](rejected());
  await requests[0];
  let finishSignIn;
  globalThis.fetch = () => new Promise((resolve) => { finishSignIn = resolve; });
  const signIn = auth.signInApiToken('new-test-token');
  pendingResponses[1](rejected());
  await requests[1];
  assert.equal(auth.getApiAuthState().submitting, true);
  finishSignIn(accepted());
  assert.equal(await signIn, true);
});
