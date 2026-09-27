import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5194';
const fixture = process.env.PORTFOLIO_FIXTURE || 'outputs/audits/portfolio-remediation-review-20260919/latest.json';
// Re-render a saved artifact in memory to exercise long real-world prose, without changing that run.
const memo = JSON.parse(execFileSync('.venv/bin/python', ['-c', `
import json, sys
from pathlib import Path
from backend.portfolio_memo import render_portfolio_memo
from backend.routers.runs import _build_portfolio_read_models
p = Path(sys.argv[1])
run = json.loads(p.read_text())
run['workflow_version'] = 4
run['structured_data']['workflow_version'] = 4
run['analyst_memo_markdown'] = render_portfolio_memo(snapshot=run['portfolio_snapshot'],
    structured=run['structured_data'], evidence_brief=run['evidence_brief'], citations=run.get('source_citations', []))
run['chairman_memo_markdown'] = run['analyst_memo_markdown']
print(json.dumps(_build_portfolio_read_models(p, run)['memo']))
`, fixture], { maxBuffer: 16 * 1024 * 1024 }).toString());
memo.id = memo.file = 'research-led.json';
const output = 'outputs/audits/portfolio-research-led/browser';
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  let supportingReads = 0;
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/**', async route => {
    assert.equal(route.request().method(), 'GET', 'Reader QA must never launch paid work');
    const url = new URL(route.request().url());
    if (url.pathname === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
    if (url.pathname === '/api/analysis-jobs') return route.fulfill({ json: { jobs: [] } });
    if (url.pathname.endsWith('/reviews')) return route.fulfill({ json: { reviews: [] } });
    if (url.pathname === '/api/portfolio-positioning-runs') return route.fulfill({ json: { runs: [{ id: 'research-led.json', label: 'Presentation test', updated_at: memo.updated_at }] } });
    if (url.searchParams.get('view') === 'memo') return route.fulfill({ json: memo });
    supportingReads += 1;
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto(`${origin}/portfolio-analysis?run_id=research-led.json`);
  const panel = page.locator('.memo-panel');
  try {
    await page.getByRole('heading', { name: 'Asset Class Targets', exact: true }).waitFor({ timeout: 10000 });
  } catch (error) {
    console.log({ errors, memoStart: memo.memo_markdown?.slice(0, 300), body: await page.locator('body').innerText() });
    throw error;
  }
  const research = panel.locator('details').filter({ has: page.locator('summary', { hasText: /^Supporting research$/ }) });
  assert.equal(await research.getAttribute('open'), null);
  assert.equal(await panel.getByRole('heading', { name: 'Independent Ideal Portfolio', exact: true }).isVisible(), false);
  assert.equal(supportingReads, 0);
  assert.equal(await page.getByRole('heading', { name: 'Current Sleeve Decisions', exact: true }).count(), 1);
  assert.equal(await panel.getByRole('heading', { name: 'Recommended Portfolio', exact: true }).count(), 0);
  assert.equal(await panel.getByRole('heading', { name: 'Allocation Rationale', exact: true }).count(), 1);
  const sleeves = page.getByRole('table', { name: 'Current sleeve decisions' });
  assert.equal(await sleeves.getByRole('row').count(), memo.structured_data.current_sleeve_decisions.length + 1);
  const synopsis = page.locator('.portfolio-executive-summary');
  assert.equal(await synopsis.count(), 1, 'Show one complete synopsis');
  assert.equal(await synopsis.locator('details').count(), 0, 'The full synopsis is visible without expanding');
  const metrics = page.getByRole('list', { name: 'Portfolio memo key metrics' });
  assert.equal(await metrics.locator('.portfolio-stat-detail').count(), 0, 'Cash metrics have no explanatory filler');
  assert.ok(!(await metrics.innerText()).includes('portfolio snapshot'));
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['Light', 'Dark']) {
      await page.getByRole('button', { name: theme, exact: true }).click();
      await page.locator('.portfolio-lab-header').scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${output}/overview-${width}-${theme}.png` });
      const rationale = page.locator('.portfolio-theme-rationale');
      await rationale.locator('summary').click();
      const presentation = await rationale.evaluate((el) => {
        const body = el.querySelector('.portfolio-theme-rationale-body');
        return { open: el.open, background: getComputedStyle(el).backgroundColor,
          padding: parseFloat(getComputedStyle(body).paddingLeft),
          overflow: body.scrollWidth - body.clientWidth,
          inMetrics: Boolean(el.closest('.portfolio-hero-meta')),
          bullets: body.querySelectorAll('li').length };
      });
      assert.ok(presentation.open && !presentation.inMetrics);
      assert.equal(presentation.background, 'rgba(0, 0, 0, 0)');
      assert.ok(presentation.padding >= 12 && presentation.overflow <= 2);
      if (/^[-*] /m.test(memo.structured_data.strategic_view?.theme_explanation || '')) assert.ok(presentation.bullets > 0);
      await page.screenshot({ path: `${output}/rationale-${width}-${theme}.png` });
      await rationale.locator('summary').click();
      const shapes = page.getByRole('region', { name: 'Portfolio shapes' });
      await shapes.scrollIntoViewIfNeeded();
      assert.equal(await shapes.getByRole('img').count(), 4);
      assert.ok(await shapes.evaluate(el => el.scrollWidth <= el.clientWidth + 2));
      await page.screenshot({ path: `${output}/shapes-${width}-${theme}.png` });
      const allocation = page.getByRole('heading', { name: 'Asset Class Targets', exact: true });
      await allocation.scrollIntoViewIfNeeded();
      assert.ok(await page.locator('.portfolio-workspace').evaluate(el => el.scrollWidth <= el.clientWidth + 2));
      assert.ok(await panel.evaluate(el => el.scrollWidth <= el.clientWidth + 2));
      assert.equal(await page.getByRole('table', { name: 'Asset class target allocation' }).getByRole('columnheader', { name: 'Conviction', exact: true }).count(), 1);
      await page.waitForTimeout(350);
      await page.screenshot({ path: `${output}/allocation-${width}-${theme}.png` });
    }
  }
  await research.locator('summary').click();
  assert.ok(await panel.getByRole('heading', { name: 'Independent Ideal Portfolio', exact: true }).isVisible());
  await research.locator('summary').click();
  assert.equal(await research.getAttribute('open'), null);
  const text = await panel.innerText();
  const theme = page.locator('.portfolio-stat-card').filter({ hasText: 'Primary Theme' });
  assert.ok((await theme.locator('.portfolio-stat-value').innerText()).split(/\s+/).length <= 20, 'Theme title is compact, not an essay');
  assert.equal(await theme.locator('details').count(), 0, 'Long rationale must not live inside the compact metrics column');
  assert.ok(!/\bfact_[a-f0-9]{16,64}\b/.test(text), 'No internal fact IDs in the visible memo');
  assert.ok(!/\bquestion_[a-f0-9]{16,64}\b/.test(text), 'No internal question IDs in the visible memo');
  assert.ok(!(await page.locator('body').innerText()).includes('[object Object]'), 'Nested scorecard objects must render as assessments');
  memo.workflow_version = 3;
  memo.structured_data.executive_summary = 'A short historical investment abstract.';
  memo.memo_markdown = '# Portfolio memo\n\n## Recommended Portfolio\n\n| Exposure | Weight |\n| --- | --- |\n| Cash | 100% |\n\n- **Cash:** Retained older rationale and its qualification.\n\n## Risks\n\nRetained risk assessment.';
  await page.reload();
  await panel.getByText('Retained older rationale and its qualification.', { exact: false }).waitFor();
  assert.equal(await panel.locator('table').count(), 0, 'Only the duplicated table is removed, never adjacent older rationale');
  assert.equal(await synopsis.locator('details').count(), 0, 'Short abstracts stay fully visible');
  assert.ok(await panel.getByText('Retained risk assessment.').isVisible());
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ result: 'passed', themesAndViewports: 6, mainWords: text.split(/\s+/).length,
    supportingReads, screenshots: output }));
} finally {
  await browser.close();
}
