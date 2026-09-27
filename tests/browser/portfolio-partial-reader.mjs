import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5194';
const output = 'outputs/audits/portfolio-research-led-review-20260919/updated-reader';
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
const results = [];
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => assert.equal(request.method(), 'GET', 'Reader tests cannot start an analysis'));
  for (const run of ['latest.json', 'august.json']) {
    await page.goto(`${origin}/portfolio-analysis?run_id=${run}`);
    const panel = page.locator('.memo-panel');
    await panel.waitFor();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const theme of ['Light', 'Dark']) {
        await page.getByRole('button', { name: theme, exact: true }).click();
        if (run === 'latest.json') {
          await panel.getByRole('heading', { name: 'Saved Draft Portfolios', exact: true }).waitFor();
          assert.ok(await panel.getByRole('heading', { name: 'Independent Ideal Portfolio', exact: true }).isVisible());
          assert.ok(await panel.getByRole('heading', { name: 'Assessment Of Your Portfolio', exact: true }).isVisible());
          assert.equal(await panel.getByRole('heading', { name: 'Reconciling The Two Views', exact: true }).count(), 0);
          assert.equal(await panel.getByRole('heading', { name: 'Recommended Portfolio', exact: true }).count(), 0);
          assert.match(await panel.innerText(), /additional API credit/);
          assert.equal(await panel.locator('table').count(), 2);
          for (const table of await panel.locator('.portfolio-memo-table').all()) {
            assert.ok(await table.evaluate(el => el.scrollWidth <= el.clientWidth + 2), 'Draft weights fit on mobile');
          }
          const research = panel.locator('details').filter({ has: page.locator('summary', { hasText: /^Supporting research$/ }) });
          assert.equal(await research.getAttribute('open'), null);
          await research.locator('summary').click();
          assert.ok(await panel.getByRole('heading', { name: 'Research Questions', exact: true }).isVisible());
          await research.locator('summary').click();
        } else {
          await panel.getByRole('heading', { name: 'Executive Summary', exact: true }).waitFor();
          assert.equal(await panel.getByRole('heading', { name: 'Saved Draft Portfolios', exact: true }).count(), 0);
        }
        assert.ok(await page.locator('.portfolio-workspace').evaluate(el => el.scrollWidth <= el.clientWidth + 2));
        assert.ok(await panel.evaluate(el => el.scrollWidth <= el.clientWidth + 2));
        await page.locator('.portfolio-lab-header').scrollIntoViewIfNeeded();
        await page.waitForTimeout(150);
        await page.screenshot({ path: `${output}/${run}-${width}-${theme}.png` });
        if (run === 'latest.json') {
          await panel.locator('table').first().scrollIntoViewIfNeeded();
          await page.screenshot({ path: `${output}/draft-table-${width}-${theme}.png` });
        }
        results.push({ run, width, theme, errors: [...errors] });
      }
    }
  }
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
writeFileSync(`${output}/checks.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify({ passed: results.length, errors: [], output }));
