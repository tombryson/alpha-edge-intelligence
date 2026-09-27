import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5194';
const fixture = 'outputs/audits/portfolio-independent-uplift/preview-fixtures/independent.json';
const full = JSON.parse(readFileSync(fixture, 'utf8'));
full.id = 'independent.json';
full.macro_positioning = { ...full.macro_positioning,
  judgment_audit: { contributors: [], unresolved_findings: [], comparison_issues: [], exposure_mapping_issues: [] },
  implementation_comparison: { issues: ['The alternative has greater turnover (50%) than the destination (10%).'] },
  decision_reconsideration: { issues: ['The affected investment decision remains unresolved.'] },
};
const before = JSON.stringify(full);
const memo = JSON.parse(execFileSync('.venv/bin/python', ['-c', `
import json
from pathlib import Path
from backend.routers.runs import _build_portfolio_read_models
p=Path('${fixture}')
print(json.dumps(_build_portfolio_read_models(p,json.loads(p.read_text()))['memo']))
`]).toString());
const output = 'outputs/audits/portfolio-independent-uplift/browser';
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], starts = [], adjustments = [];
  let supportingReads = 0;
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
    if (path === '/api/analysis-jobs' && route.request().method() === 'GET') return route.fulfill({ json: { jobs: [] } });
    if (path === '/api/portfolio-positioning-runs') return route.fulfill({ json: { runs: [{ id: full.id, label: 'Independent test memo', updated_at: full.updated_at }] } });
    if (path.endsWith('/reviews')) return route.fulfill({ json: { reviews: adjustments } });
    if (path.endsWith('/review')) {
      const request = route.request().postDataJSON();
      assert.equal(request.user_adjustment, true);
      const saved = { review_id: 'user-alternative', as_of: new Date().toISOString(), user_adjustment: true,
        alternatives: [{ name: request.alternatives[0].name, funding: { status: 'unresolved', rows: request.alternatives[0].asset_class_targets } }] };
      adjustments.push(saved);
      return route.fulfill({ json: saved });
    }
    if (path === '/api/portfolio-positioning/preflight') return route.fulfill({ json: {
      status: 'ready', message: 'Offline funding check', estimate: { low_usd: 1, high_usd: 4 },
    } });
    if (path === '/api/analysis-jobs') {
      starts.push(route.request().postDataJSON());
      return route.fulfill({ json: { job_id: 'offline-job', status: 'queued' } });
    }
    if (url.searchParams.get('view') === 'memo') return route.fulfill({ json: memo });
    if (url.searchParams.get('view') === 'research') { supportingReads += 1; return route.fulfill({ json: full }); }
    throw new Error(`Unexpected request ${route.request().method()} ${url}`);
  });
  await page.goto(`${origin}/portfolio-analysis?run_id=independent.json`);
  await page.getByRole('heading', { name: 'Independent Ideal Portfolio', exact: true }).waitFor();
  assert.equal(supportingReads, 0, 'Opening a memo must not load raw supporting artifacts');
  assert.equal(await page.locator('.portfolio-memo-table table').count(), 2, 'Distinct ideal and recommended tables');
  assert.equal(await page.locator('.allocation-panel').count(), 0, 'No duplicated pre-memo tables in the new workflow');
  assert.ok((await page.locator('.portfolio-memo-table').first().innerText()).includes('15%'));
  assert.ok((await page.locator('.portfolio-memo-table').last().innerText()).includes('5%'));
  assert.ok((await page.locator('.memo-panel').innerText()).includes('STRONG'));
  assert.equal(await page.locator('.portfolio-memo-sources').getAttribute('open'), null);
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['Light', 'Dark']) {
      await page.getByRole('button', { name: theme, exact: true }).click();
      await page.getByRole('heading', { name: 'Independent Ideal Portfolio', exact: true }).scrollIntoViewIfNeeded();
      assert.ok(await page.locator('.portfolio-workspace').evaluate((el) => el.scrollWidth <= el.clientWidth + 2));
      assert.equal(await page.locator('.portfolio-memo-table table').first().evaluate((el) => getComputedStyle(el).display), 'table');
      await page.waitForTimeout(350); // Let the responsive table layer repaint after viewport/theme changes.
      await page.screenshot({ path: `${output}/memo-${width}-${theme}.png` });
    }
  }
  assert.equal(await page.getByRole('button', { name: 'Add play', exact: true }).count(), 0, 'Plays are entered in the Trading Terminal before submission');
  assert.equal(starts.length, 0, 'Reading a memo cannot launch an analysis');
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  await page.getByText('Decision review', { exact: true }).click();
  assert.ok(await page.getByText('The alternative has greater turnover (50%) than the destination (10%).', { exact: true }).isVisible());
  assert.ok(await page.getByText('The affected investment decision remains unresolved.', { exact: true }).isVisible());
  await page.getByText('User adjustment', { exact: true }).click();
  await page.getByRole('button', { name: 'Add exposure', exact: true }).click();
  const exposures = page.getByRole('textbox', { name: /^Exposure / });
  const count = await exposures.count();
  await exposures.last().fill('New economic exposure');
  await page.getByRole('spinbutton', { name: `Target ${count} percent`, exact: true }).fill('5');
  await page.getByRole('button', { name: 'Save alternative', exact: true }).click();
  await page.getByText('Saved separately.', { exact: false }).waitFor();
  assert.equal(adjustments.length, 1);
  assert.equal(JSON.stringify(full), before, 'Editing must not mutate the saved model memo');
  assert.deepEqual(errors, []);
  console.log('Independent reader, 2 distinct tables, preserved conviction, lazy sources, 6 responsive theme checks, no misplaced launch editor, separate user adjustments: passed.');
} finally { await browser.close(); }
