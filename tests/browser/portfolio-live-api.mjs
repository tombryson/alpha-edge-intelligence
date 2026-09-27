import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync, rmSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5184';
const directory = `${process.cwd()}/outputs/audits/portfolio-remediation/local-data/jobs/portfolio_positioning`;
const id = 'offline-regression-fixture.json';
const mandate = { base_currency: 'AUD', benchmark: 'cash', horizon_months: 12, max_drawdown_pct: 20,
  liquidity_min_pct: 10, tax_cost_policy: 'Review tax before trading', currency_hedge_policy: 'Fully hedged' };
const proposal = { analysis_kind: 'portfolio_positioning', analysis_date: '2026-08-11', executive_summary: 'Offline regression fixture',
  asset_class_targets: [{ asset_class: 'equity', min_pct: 60, target_pct: 60, max_pct: 60 },
    { asset_class: 'cash', min_pct: 40, target_pct: 40, max_pct: 40 }] };
mkdirSync(directory, { recursive: true });
writeFileSync(`${directory}/${id}`, JSON.stringify({ updated_at: '2026-08-11T00:00:00Z', analysis_kind: 'portfolio_positioning',
  portfolio_snapshot: { as_of: '2026-08-11', portfolio: { cash_pct: 20, total_value: 100000 },
    asset_classes: [{ asset_class: 'equity', portfolio_pct: 80 }], mandate },
  macro_positioning: proposal, structured_data: proposal }));
const api = async (path, data) => {
  const response = await fetch(`${origin}/api/${path}`, data ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) } : {});
  return { status: response.status, body: await response.json() };
};
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const run = await api(`portfolio-positioning-runs/${id}`);
  assert.equal(run.status, 200);
  assert.equal(run.body.structured_data.decision.funding.status, 'balanced');
  const records = ['equity', 'cash'].map((asset) => ({ asset_class: asset, total_return_pct: asset === 'cash' ? 1 : 10,
    currency: 'AUD', transaction_cost_bps: 0, from: '2026-08-12', to: '2026-09-11', source_url: 'https://example.org/fixture' }));
  const measured = await api(`portfolio-positioning-runs/${id}/review`, { mandate, total_returns: records });
  assert.equal(measured.body.performance.status, 'measured');
  assert.equal(measured.body.performance.benchmark.return_pct, 1);
  assert.equal(measured.body.performance.benchmark.excess_return_pp, 5.4);
  const future = await api(`portfolio-positioning-runs/${id}/review`, { mandate, total_returns: records.map((row) => ({ ...row, from: '2030-01-01', to: '2030-02-01' })) });
  assert.equal(future.body.performance.status, 'incomplete');
  const invalid = await api(`portfolio-positioning-runs/${id}/review`, { mandate: { ...mandate, horizon_months: -12 } });
  assert.equal(invalid.status, 422);
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(`${origin}/portfolio-analysis`);
  await page.getByText('Supporting analysis and review', { exact: true }).click();
  await page.getByRole('heading', { name: 'Asset Class Targets' }).first().waitFor();
  await page.getByRole('tab', { name: 'Mandate', exact: true }).click();
  await page.getByRole('textbox', { name: 'Base currency', exact: true }).fill('AUD');
  const savedReview = page.waitForResponse((response) => response.url().endsWith('/review') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Save review', exact: true }).click();
  assert.equal((await savedReview).status(), 200);
  await page.getByRole('status').filter({ hasText: 'Reviewed' }).waitFor();
  await page.getByRole('textbox', { name: 'Base currency', exact: true }).fill('USD');
  await page.getByRole('status').filter({ hasText: 'Unsaved changes' }).waitFor();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ['Light', 'Dark']) {
      await page.getByRole('button', { name: theme, exact: true }).click();
      const overflow = await page.locator('.portfolio-workspace').evaluate((element) => element.scrollWidth - element.clientWidth);
      assert.ok(overflow <= 2);
      await page.screenshot({ path: `${process.cwd()}/outputs/audits/portfolio-remediation/browser/live-${width}-${theme.toLowerCase()}.png`, fullPage: true });
      await page.locator('.portfolio-decision-review').scrollIntoViewIfNeeded();
      await page.locator('.portfolio-decision-review').screenshot({ path: `${process.cwd()}/outputs/audits/portfolio-remediation/browser/live-review-${width}-${theme.toLowerCase()}.png` });
    }
  }
  assert.deepEqual(errors, []);
  console.log('Live API checks passed: sourced performance, benchmark comparison, invalid dates, mandate validation, saved review, dirty state and responsive themes. No mocked HTTP responses.');
} finally {
  await browser.close();
  rmSync(`${directory}/${id}`, { force: true });
  rmSync(`${directory}/portfolio_reviews/offline-regression-fixture`, { recursive: true, force: true });
}
