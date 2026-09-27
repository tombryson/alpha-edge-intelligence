import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5194';
const folder = 'outputs/audits/portfolio-r360-review-20260922/cancellation-browser';
mkdirSync(folder, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
const results = [];
try {
  for (const width of [1440, 390]) {
    for (const theme of ['Light', 'Dark']) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let job = { job_id: 'offline-cancel', status: 'running', request: { job_type: 'portfolio_positioning' },
        created_at: new Date(Date.now() - 60000).toISOString(), execution_progress: { status: 'running', message: 'Reviewing the investment cases', phases: [] } };
      let attempts = 0;
      await page.route('**/api/**', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (request.method() === 'POST') {
          assert.equal(url.pathname, '/api/analysis-jobs/offline-cancel/cancel', 'No real or new analysis may be submitted');
          if (++attempts === 1) {
            await route.fulfill({ status: 503, json: { detail: 'Cancellation temporarily unavailable' } });
          } else {
            await new Promise(resolve => setTimeout(resolve, 150));
            job = { ...job, status: 'cancelling', cancel_requested_at: new Date().toISOString(), execution_progress: { status: 'cancelling', message: 'Stopping analysis; saved research remains available' } };
            await route.fulfill({ json: job });
          }
        } else if (url.pathname === '/api/auth/status') {
          await route.fulfill({ json: { authenticated: true } });
        } else if (url.pathname === '/api/analysis-jobs') {
          await route.fulfill({ json: { jobs: [job] } });
        } else {
          await route.fulfill({ json: { runs: [] } });
        }
      });
      await page.goto(`${origin}/portfolio-analysis`);
      await page.getByRole('button', { name: theme, exact: true }).click();
      const panel = page.getByRole('region', { name: 'Live portfolio progress' });
      await panel.getByRole('button', { name: 'Stop analysis', exact: true }).click();
      await page.getByRole('alert').filter({ hasText: 'Cancellation temporarily unavailable' }).waitFor();
      await panel.getByRole('button', { name: 'Stop analysis', exact: true }).click();
      await panel.getByText('Stopping portfolio analysis', { exact: true }).waitFor();
      assert.ok(await panel.getByRole('button', { name: 'Stopping...' }).isDisabled());
      assert.ok(await panel.evaluate(el => el.scrollWidth <= el.clientWidth + 2));
      await panel.screenshot({ path: `${folder}/${width}-${theme}.png` });
      job = { ...job, status: 'cancelled', finished_at: new Date().toISOString(), execution_progress: { status: 'cancelled', message: 'Analysis cancelled; saved research remains available' } };
      await panel.getByText('Portfolio analysis stopped', { exact: true }).waitFor({ timeout: 8000 });
      assert.equal(await panel.getByRole('button', { name: /Stop/ }).count(), 0);
      assert.deepEqual(errors, []);
      results.push({ width, theme, cancelled: true, errors });
      await page.close();
    }
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify({ mockOnly: true, results }));
