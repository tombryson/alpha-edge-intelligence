import { createRequire } from 'node:module';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5184';
const routes = [
  ['Macro-first allocator', 'openai/gpt-5.5', 'role'],
  ['Portfolio-aware allocator', 'google/gemini-3.8-flash', 'single'],
  ['Exposure-equivalence reviewer', 'x-ai/grok-4.6', undefined],
  ['Defensive-regime reviewer', 'openai/gpt-5.5', 'role'],
].map(([layer, model, kind], index) => ({
  id: `portfolio.role-${index}`, app: 'Portfolio Analysis', layer, kind,
  provider: 'OpenRouter', source: 'migrated', effective_value: { model }, editable: true,
  description: `Description for ${layer}`,
}));
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  const errors = [];
  const saves = [];
  let macroModel = 'ultra4x';
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/api/**', async (route) => {
    if (new URL(route.request().url()).pathname === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
    if (route.request().method() === 'PUT') {
      const value = route.request().postDataJSON().value;
      saves.push(value);
      if (route.request().url().endsWith('portfolio.macro-news')) macroModel = value;
      else routes.find((item) => route.request().url().endsWith(item.id)).effective_value = value;
    }
    await route.fulfill({ json: { routes: [...routes, {
      id: 'router.semantic', app: 'Announcement Router', layer: 'Semantic adjudicator',
      description: 'Evidence-bounds ambiguous watchlist and thesis-condition matches.',
      kind: 'single', provider: 'OpenRouter', source: 'environment', effective_value: 'provider/research',
    }, ...[
      ['portfolio.macro-news', 'Portfolio Analysis', 'Macro and news retrieval'],
      ['market.core-asset-resolver', 'Market Intelligence', 'Commodity exposure resolver'],
    ].map(([id, app, layer]) => ({ id, app, layer, kind: 'single',
      provider: id === 'portfolio.macro-news' ? 'Parallel' : 'xAI',
      source: 'environment', effective_value: id === 'portfolio.macro-news' ? macroModel : 'grok-4.6',
      description: id === 'portfolio.macro-news' ? 'Current market context and initial sources.' : 'Native search' }))], audit: [], configuration_errors: [] } });
  });
  await page.goto(`${origin}/model-routing`);
  await page.getByRole('heading', { name: 'Macro-first allocator' }).waitFor();
  assert.equal(await page.locator('.model-route-role').count(), 4);
  assert.equal(await page.getByText('[object Object]', { exact: false }).count(), 0);
  assert.equal(await page.locator('.model-route-convention').count(), 1);
  assert.equal(await page.getByText('Grok model recommended', { exact: true }).count(), 0);
  for (const title of ['Macro and news retrieval', 'Commodity exposure resolver']) {
    const row = page.locator('article').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
    const parallel = title === 'Macro and news retrieval';
    assert.equal(await row.locator('.model-route-provider').innerText(), parallel ? 'Parallel' : 'xAI');
    assert.equal(await row.locator('.model-route-convention').count(), parallel ? 0 : 1);
    await row.getByRole('button', { name: 'Edit', exact: true }).click();
    const input = row.getByRole('textbox');
    assert.equal(await input.getAttribute('placeholder'), parallel ? 'ultra4x' : 'grok-4.6');
    assert.equal(await input.getAttribute('aria-describedby'), parallel ? null : await row.locator('.model-route-convention').getAttribute('id'));
    if (parallel) {
      await input.fill('  ultra4x  ');
      await row.getByRole('button', { name: 'Save', exact: true }).click();
      await row.getByRole('button', { name: 'Edit', exact: true }).waitFor();
      assert.equal(saves[0], 'ultra4x');
    } else await row.getByRole('button', { name: 'Cancel', exact: true }).click();
  }
  const tip = page.getByText('Evidence-bounds ambiguous watchlist and thesis-condition matches.', { exact: true });
  assert.equal(await tip.isVisible(), false);
  await page.locator('summary').filter({ hasText: 'Semantic adjudicator' }).click();
  assert.equal(await tip.isVisible(), true);
  await page.locator('summary').filter({ hasText: 'Semantic adjudicator' }).press('Enter');
  assert.equal(await tip.isVisible(), false);
  assert.equal(await page.getByText('provider/research', { exact: true }).isVisible(), true);
  for (const item of routes) {
    const row = page.locator('article').filter({ has: page.getByRole('heading', { name: item.layer, exact: true }) });
    assert.equal(await row.locator('code').innerText(), item.effective_value.model);
    const description = row.getByText(item.description, { exact: true });
    assert.equal(await description.isVisible(), false);
    await row.locator('summary').click();
    assert.equal(await description.isVisible(), true);
    await row.locator('summary').click();
    const headingBox = await row.locator('h3').boundingBox();
    const modelBox = await row.locator('code').boundingBox();
    assert.ok(Math.abs(headingBox.y + headingBox.height / 2 - modelBox.y - modelBox.height / 2) < 2, 'Model and title share a horizontal centre line');
    await row.getByRole('button', { name: 'Edit', exact: true }).click();
    const input = row.getByRole('textbox');
    assert.equal(await input.inputValue(), item.effective_value.model);
    await input.fill('provider/replacement-model');
    await row.getByRole('button', { name: 'Save', exact: true }).click();
    await row.getByText('provider/replacement-model', { exact: true }).waitFor();
  }
  assert.deepEqual(saves, ['ultra4x', ...Array.from({ length: 4 }, () => ({ model: 'provider/replacement-model' }))]);
  assert.deepEqual(errors, []);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const row = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Macro and news retrieval', exact: true }) });
    assert.ok(await row.evaluate((element) => element.scrollWidth <= element.clientWidth + 2));
    await row.screenshot({ path: `/tmp/model-routing-convention-${width}.png` });
  }
  console.log('Role rendering and editing passed, including missing/legacy route kinds.');
} finally {
  await browser.close();
}
