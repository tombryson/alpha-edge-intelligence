import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = process.cwd();
const payload = JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-c', `
import asyncio, json
from pathlib import Path
from backend.routers import runs
path = Path('outputs/audits/portfolio-20260811/run.json').resolve()
runs._resolve_portfolio_positioning_artifact_path = lambda name: path
print(json.dumps(asyncio.run(runs.get_portfolio_positioning_run('historical.json'))))
`], { maxBuffer: 30 * 1024 * 1024 }).toString().trim());
payload.can_resume = true;
payload.id = 'historical.json';
payload.workload = { completed_tasks: 31, reused_tasks: 12, new_model_requests: 19,
  retry_requests: 1, reported_openrouter_usd: 2.345, unpriced_model_requests: 2 };
const output = `${root}/outputs/audits/portfolio-remediation/browser`;
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
let reviewBody;
let recoveryBody;
await page.route('**/api/**', async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  if (url.pathname === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
  let body = {};
  if (url.pathname.endsWith('/review')) {
    reviewBody = request.postDataJSON();
    body = { as_of: '2026-09-15T02:00:00Z', review_id: 'test-review', decision: payload.structured_data.decision,
      scenarios: [{ rows: [], method: 'Offline browser fixture', hold_return_pct: null, proposed_return_pct: null }],
      conditions: [], performance: { issues: ['Aligned return data required'] }, alternatives: [] };
  } else if (url.pathname.endsWith('/reviews')) body = { reviews: [] };
  else if (url.pathname === '/api/portfolio-positioning-runs') body = { runs: [{ id: payload.id, label: 'August portfolio memo', updated_at: payload.updated_at, analysis_health: payload.analysis_health }] };
  else if (url.pathname.startsWith('/api/portfolio-positioning-runs/')) body = payload;
  else if (url.pathname === '/api/analysis-jobs' && request.method() === 'POST') {
    recoveryBody = request.postDataJSON(); body = { job_id: 'test-recovery', status: 'queued' };
  } else if (url.pathname.includes('/api/analysis-jobs/test-recovery')) body = { job_id: 'test-recovery', status: 'failed', error: 'Offline recovery fixture', stage_message: 'Recovery fixture finished' };
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
});
await page.goto(process.env.PORTFOLIO_PREVIEW_URL || 'http://127.0.0.1:5184/portfolio-analysis');
await page.getByRole('heading', { name: 'Asset Class Targets' }).first().waitFor();
assert.equal(await page.locator('.portfolio-workspace > .portfolio-hero-card').count(), 1, 'Original summary leads the workspace');
assert.equal(await page.locator('.portfolio-allocation-rationales').count(), 1, 'Allocation rationales are retained');
assert.ok((await page.locator('.memo-panel .markdown-content').innerText()).length > 1000, 'Full memo is readable');
assert.equal(await page.locator('.portfolio-memo-appendix').getAttribute('open'), null, 'Supporting analysis starts collapsed');
assert.equal(await page.getByRole('tab', { name: 'Evidence', exact: true }).isVisible(), false);
for (const width of [1440, 390]) {
  await page.setViewportSize({ width, height: 900 });
  for (const theme of ['Light', 'Dark']) {
    await page.getByRole('button', { name: theme, exact: true }).click();
    await page.screenshot({ path: `${output}/memo-first-${width}-${theme}.png` });
    assert.ok(await page.locator('.memo-panel').evaluate((el) => el.scrollWidth <= el.clientWidth + 2));
  }
}
await page.getByText('Supporting analysis and review', { exact: true }).click();
const executionDetails = page.locator('.portfolio-health > details');
assert.equal(await executionDetails.getAttribute('open'), null, 'Execution diagnostics start collapsed');
await executionDetails.locator(':scope > summary').click();
await page.getByText('31 completed tasks · 12 reused · 19 new model requests · 1 retry', { exact: true }).waitFor();
await page.getByText('Reported OpenRouter cost for new requests: US$2.35. Other providers are not included. Cost unavailable for 2 model requests.', { exact: true }).waitFor();
await executionDetails.locator(':scope > summary').click();
await page.getByRole('heading', { name: 'Asset Class Targets' }).first().waitFor();
await page.getByRole('button', { name: 'Dark', exact: true }).click();
assert.equal(await page.locator('.portfolio-target-bar').count(), 0, 'Unfunded historical book must not appear normalized to 100%');
assert.equal(await page.locator('.current-sleeves').count(), payload.structured_data.current_sleeve_decisions?.length ? 1 : 0, 'Current sleeve decisions retain their original section');
assert.equal(await page.locator('.memo-panel details').count(), 0, 'Memo must not be collapsed');
await page.setViewportSize({ width: 1440, height: 1000 });
await page.screenshot({ path: `${output}/desktop-dark.png`, fullPage: true });
await page.locator('.allocation-panel').first().screenshot({ path: `${output}/allocation-dark.png` });
await page.getByRole('tab', { name: 'Mandate', exact: true }).click();
await page.getByRole('textbox', { name: 'Base currency', exact: true }).fill('AUD');
await page.getByRole('button', { name: 'Save review', exact: true }).click();
await page.getByRole('status').filter({ hasText: 'Reviewed' }).waitFor();
assert.equal(reviewBody.mandate.base_currency, 'AUD');
await page.getByRole('tab', { name: 'Scenarios', exact: true }).click();
await page.getByRole('spinbutton', { name: 'Equities (%)', exact: true }).fill('-10');
await page.getByRole('button', { name: 'Calculate comparison' }).click();
await page.getByText('Offline browser fixture').waitFor();
assert.equal(reviewBody.scenarios[0].shocks.equity_pct, -10);
await page.getByRole('tab', { name: 'Conditions', exact: true }).click();
await page.getByRole('tab', { name: 'Performance', exact: true }).click();
await page.getByRole('tab', { name: 'Evidence', exact: true }).click();
await page.getByRole('button', { name: 'Light', exact: true }).click();
await page.screenshot({ path: `${output}/desktop-light.png`, fullPage: true });
for (const width of [390, 768]) {
  await page.setViewportSize({ width, height: 844 });
  for (const tab of ['Evidence', 'Mandate', 'Scenarios', 'Conditions', 'Performance']) {
    await page.getByRole('tab', { name: tab, exact: true }).click();
    const overflow = await page.locator('.portfolio-workspace').evaluate((element) => element.scrollWidth - element.clientWidth);
    assert.ok(overflow <= 2, `${width}px ${tab}: workspace overflow ${overflow}`);
  }
  await page.screenshot({ path: `${output}/mobile-${width}.png`, fullPage: true });
  await page.locator('.portfolio-decision-review').screenshot({ path: `${output}/review-${width}.png` });
}
await page.getByRole('button', { name: 'Recover analysis' }).click();
try {
  await page.getByText('Recovery fixture finished').waitFor();
} catch (error) {
  await page.screenshot({ path: `${output}/recovery-error.png`, fullPage: true });
  console.error({ errors, recoveryBody, health: await page.locator('.portfolio-health').innerText() });
  throw error;
}
assert.equal(recoveryBody.resume_portfolio_run_id, 'historical.json');
assert.deepEqual(errors, []);
await browser.close();
console.log('Portfolio browser checks passed: historical funding, themes, responsive tabs, mandate, scenarios and recovery.');
