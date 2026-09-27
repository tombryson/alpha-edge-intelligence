import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const full = JSON.parse(readFileSync('outputs/audits/portfolio-20260917-parallel-recovery/completed-memo.json', 'utf8'));
const light = JSON.parse(execFileSync('.venv/bin/python', ['-c', `
import json
from pathlib import Path
from backend.routers.runs import _build_portfolio_read_models
p=Path('outputs/audits/portfolio-20260917-parallel-recovery/completed-memo.json')
print(json.dumps(_build_portfolio_read_models(p,json.loads(p.read_text()))['memo']))
`]).toString());
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5192';
const output = 'outputs/audits/portfolio-reader/browser';
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let listRequests = 0, researchRequests = 0, reviewRequests = 0;
  let releaseList;
  const listGate = new Promise((resolve) => { releaseList = resolve; });
  let failResearch = true;
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    assert.equal(route.request().method(), 'GET', 'Reader tests must never create or modify analyses');
    if (url.pathname === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
    if (url.pathname === '/api/analysis-jobs') return route.fulfill({ json: { jobs: [] } });
    if (url.pathname === '/api/portfolio-positioning-runs') {
      listRequests += 1;
      await listGate;
      return route.fulfill({ json: { runs: ['Alpha', 'Beta'].map((label) => ({ id: `${label}.json`, label, updated_at: full.updated_at })) } });
    }
    if (url.pathname.endsWith('/reviews')) {
      reviewRequests += 1;
      return route.fulfill({ json: { reviews: [] } });
    }
    const id = url.pathname.split('/').pop();
    if (url.searchParams.get('view') === 'memo') {
      if (id === 'Beta.json') await new Promise((resolve) => setTimeout(resolve, 500));
      return route.fulfill({ json: { ...light, id, label: id.slice(0, -5),
        structured_data: { ...light.structured_data, executive_summary: `Summary for ${id}` } } });
    }
    assert.equal(url.searchParams.get('view'), 'research');
    researchRequests += 1;
    if (failResearch) return route.fulfill({ status: 503, json: { detail: 'Temporary supporting-analysis failure' } });
    return route.fulfill({ json: { ...full, id } });
  });
  await page.goto(`${origin}/portfolio-analysis?run_id=Alpha.json`);
  await page.getByText('Summary for Alpha.json', { exact: true }).waitFor();
  assert.equal(listRequests, 1);
  assert.equal(await page.locator('.portfolio-run-card').count(), 0, 'Memo is readable before a cold sidebar list finishes');
  assert.equal(researchRequests, 0);
  assert.equal(reviewRequests, 0);
  assert.equal(await page.getByRole('tab', { name: 'Evidence', exact: true }).count(), 0, 'Collapsed research is not mounted');
  assert.ok((await page.locator('.memo-panel .markdown-content').innerText()).length > 10000);
  releaseList();
  await page.locator('.portfolio-run-card').filter({ hasText: 'Beta' }).click();
  await page.locator('.portfolio-run-card').filter({ hasText: 'Alpha' }).click();
  await page.getByText('Summary for Alpha.json', { exact: true }).waitFor();
  await page.waitForTimeout(650); // Let the older deliberately slow response arrive.
  assert.equal(await page.getByText('Summary for Beta.json', { exact: true }).count(), 0);
  assert.equal(listRequests, 1, 'Selections do not refresh the saved-memo list');
  assert.equal(researchRequests, 0);
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  await page.getByText('Temporary supporting-analysis failure', { exact: false }).waitFor();
  assert.ok(await page.locator('.memo-panel').isVisible(), 'Supporting failure must not remove the memo');
  failResearch = false;
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await page.getByRole('tab', { name: 'Mandate', exact: true }).click();
  await page.getByRole('textbox', { name: 'Base currency', exact: true }).fill('AUD');
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  assert.equal(await page.getByRole('textbox', { name: 'Base currency', exact: true }).inputValue(), 'AUD');
  assert.equal(researchRequests, 2, 'Reopening keeps loaded research and unsaved edits');
  assert.equal(reviewRequests, 1);
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['Light', 'Dark']) {
      await page.getByRole('button', { name: theme, exact: true }).click();
      assert.ok(await page.locator('.portfolio-workspace').evaluate((element) => element.scrollWidth <= element.clientWidth + 2));
      await page.screenshot({ path: `${output}/reader-${width}-${theme}.png` });
    }
  }
  assert.deepEqual(errors, []);
  console.log('Reader: independent loading, compact response, lazy research, retry, rapid switching, retained edits, both themes and responsive layouts passed.');
} finally {
  await browser.close();
}
