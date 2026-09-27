import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output = `${process.cwd()}/outputs/audits/portfolio-progress/browser`;
mkdirSync(output, { recursive: true });
const at = (seconds) => new Date(Date.now() - seconds * 1000).toISOString();
const request = (index, status) => ({ id: String(index), label: `Source review / batch ${index + 51}`,
  model: '~deepseek/deepseek-flash-latest', status, started_at: at(45), queued_at: at(600),
  attempt: status === 'retry_queued' ? 2 : 1, retry_reason: status === 'retry_queued' ? 'Completing missing or invalid fields' : '' });
const job = { job_id: 'offline-progress', request: { job_type: 'portfolio_positioning' },
  status: 'running', started_at: at(3240), heartbeat_at: at(3),
  execution_progress: { status: 'running', last_result_at: at(30),
    message: 'Checking facts against sources: 50/67 batches saved; 4 running; 13 queued (9 retries)',
    checkpoint: { status: 'saved', saved_at: at(28), completed_tasks: 95 },
    active_requests: Array.from({ length: 4 }, (_, i) => request(i, 'running')),
    queued_requests: Array.from({ length: 8 }, (_, i) => request(i + 4, 'retry_queued')), queued_count: 13,
    phases: [{ id: 'research', label: 'Gathering macro and market research', completed: 9, total: 9, unit: 'requests' },
      { id: 'extraction', label: 'Extracting source-linked facts', completed: 32, total: 32, unit: 'batches' },
      { id: 'source_review', label: 'Checking facts against sources', completed: 50, total: 67, unit: 'batches', facts: 529 }] } };
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
let unavailable = false;
let listRequests = 0;
await page.route('**/api/**', async (route) => {
  const url = new URL(route.request().url());
  if (url.pathname === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
  if (url.pathname === '/api/analysis-jobs') {
    assert.equal(route.request().method(), 'GET', 'This fixture must never create a real run');
    assert.equal(url.searchParams.get('job_type'), 'portfolio_positioning');
    listRequests += 1;
    return route.fulfill({ status: unavailable ? 503 : 200, contentType: 'application/json', body: JSON.stringify({ jobs: [job] }) });
  }
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ runs: [] }) });
});
await page.goto(process.env.PORTFOLIO_PREVIEW_URL || 'http://127.0.0.1:5184/portfolio-analysis');
const panel = page.getByRole('region', { name: 'Live portfolio progress' });
await panel.getByText(job.execution_progress.message, { exact: true }).waitFor();
assert.equal(await panel.locator('details').getAttribute('open'), null);
assert.ok((await panel.innerText()).includes('95 tasks'));
assert.ok(!(await panel.innerText()).includes('%'), 'No invented total percentage');
await panel.locator('summary').click();
await panel.getByText('529 facts', { exact: true }).waitFor();
assert.equal(await panel.getByText('Attempt 2', { exact: true }).count(), 8);
const runningTime = await panel.locator('.portfolio-progress-request-state').first().innerText();
assert.match(runningTime, /^Running (\d+s|[0-2]m \d+s)$/, `Running time excludes the ten-minute queue: ${runningTime}`);
await panel.getByText('5 more requests queued', { exact: true }).waitFor();
for (const width of [1440, 390]) {
  await page.setViewportSize({ width, height: 1000 });
  for (const theme of ['Light', 'Dark']) {
    await page.getByRole('button', { name: theme, exact: true }).click();
    assert.ok(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth + 2));
    assert.ok(await panel.locator('.portfolio-progress-scroll').evaluate((el) => el.clientHeight <= 341 && el.scrollHeight > el.clientHeight));
    assert.equal(await panel.locator('details').evaluate((el) => getComputedStyle(el).backgroundColor), 'rgba(0, 0, 0, 0)', 'Progress must not inherit the global dark details background');
    await panel.screenshot({ path: `${output}/progress-${width}-${theme}.png` });
  }
}
await page.reload();
await panel.getByText(job.execution_progress.message, { exact: true }).waitFor();
assert.ok(listRequests >= 2, 'Refreshing reconnects to the running job');
assert.equal(await panel.locator('details').getAttribute('open'), null);
unavailable = true;
await panel.getByRole('alert').waitFor({ timeout: 12000 });
await panel.getByText(job.execution_progress.message, { exact: true }).waitFor();
unavailable = false;
job.status = 'failed';
job.finished_at = at(0);
job.execution_progress = { ...job.execution_progress, status: 'interrupted', message: 'Analysis interrupted; saved research remains available', active_requests: [], queued_requests: [], queued_count: 0 };
await panel.getByText('Portfolio analysis stopped', { exact: true }).waitFor({ timeout: 12000 });
assert.equal(await panel.getByRole('alert').count(), 0, 'Polling recovers after a transient failure');
await panel.locator('summary').click();
assert.equal(await panel.locator('.portfolio-progress-request').count(), 0, 'Stopped jobs must not show active requests');
assert.ok((await panel.innerText()).includes('95 tasks'), 'Checkpoint remains visible after interruption');
assert.deepEqual(errors, []);
await browser.close();
console.log('Portfolio progress: desktop/mobile, both themes, reconnect, stalled updates, interruption passed.');
