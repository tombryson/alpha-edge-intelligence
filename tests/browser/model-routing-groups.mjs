import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.PORTFOLIO_PREVIEW_ORIGIN || 'http://127.0.0.1:5195';
const folder = 'outputs/audits/model-routing-groups';
mkdirSync(folder, { recursive: true });
const temporary = mkdtempSync(join(tmpdir(), 'routing-groups-'));
const env = { ...process.env, MODEL_ROUTING_STORE: join(temporary, 'routing.json') };
const bridge = `import json,sys
from backend import model_routing as r
action, identifier, value = sys.argv[1:]
try:
    result = r.update_model_route(identifier, json.loads(value)) if action == 'PUT' else r.clear_model_route_override(identifier) if action == 'DELETE' else r.list_model_routes()
    print(json.dumps({'status':200, 'payload':result}))
except (ValueError, KeyError) as exc:
    print(json.dumps({'status':422, 'payload':{'detail':str(exc)}}))
`;
function api(action = 'GET', identifier = '', value = null) {
  return JSON.parse(execFileSync('.venv/bin/python', ['-c', bridge, action, identifier, JSON.stringify(value)], { env, encoding: 'utf8' }));
}
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
const results = [];
try {
  for (const width of [1440, 1024, 390]) {
    for (const name of ['research', 'evidence', 'analysis', 'decision']) {
      assert.equal(api('PUT', `portfolio.group-${name}`, name === 'research' ? 'ultra2x' : '~deepseek/deepseek-flash-latest').status, 200);
    }
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [];
    const saves = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path === '/api/auth/status') return route.fulfill({ json: { authenticated: true } });
      if (path.startsWith('/api/model-routing')) {
        const identifier = decodeURIComponent(path.split('/')[3] || '');
        const value = request.method() === 'PUT' ? request.postDataJSON().value : null;
        if (request.method() === 'PUT') saves.push(identifier);
        const result = api(request.method(), identifier, value);
        return route.fulfill({ status: result.status, json: result.payload });
      }
      assert.equal(request.method(), 'GET', 'No analysis or paid request allowed');
      return route.fulfill({ json: { runs: [], jobs: [] } });
    });
    await page.goto(`${origin}/model-routing`);
    const section = page.getByRole('region', { name: 'Portfolio Analysis', exact: true });
    await section.getByText('4 model groups', { exact: true }).waitFor();
    assert.equal(await section.getByRole('article').count(), 4);
    assert.equal(await section.getByRole('button', { name: 'Edit', exact: true }).count(), 4);
    assert.equal(await section.locator('details[open]').count(), 0);
    assert.equal(await section.locator('.model-route-model-list code').count(), 4);
    assert.equal(await section.getByRole('checkbox').count(), 0);
    const analysis = section.getByRole('article', { name: 'Allocation & Review', exact: true });
    await analysis.locator('summary').click();
    assert.equal(await analysis.locator('.model-route-members li').count(), 4);
    await analysis.locator('summary').press('Enter');
    await analysis.getByRole('button', { name: 'Edit', exact: true }).click();
    const input = analysis.getByRole('textbox');
    await input.fill('bad identifier');
    await analysis.getByRole('button', { name: 'Save', exact: true }).click();
    await analysis.getByRole('alert').waitFor();
    assert.equal(await input.inputValue(), 'bad identifier');
    await input.fill('provider/replacement:free');
    await input.press('Enter');
    await analysis.getByText('provider/replacement:free', { exact: true }).waitFor();
    const saved = api().payload.route_groups.find(group => group.id === 'portfolio.group-analysis');
    assert.ok(saved.members.every(member => member.model === 'provider/replacement:free'));
    assert.ok(saves.every(identifier => identifier === 'portfolio.group-analysis'));
    await analysis.getByRole('button', { name: 'Reset', exact: true }).click();
    await analysis.getByText('Multiple models assigned', { exact: true }).waitFor();
    assert.equal(await analysis.getByRole('button', { name: 'Reset', exact: true }).count(), 0);
    await analysis.locator('summary').click();
    assert.equal(await analysis.locator('.model-route-members code').count(), 4);
    assert.ok(await section.evaluate(element => element.scrollWidth <= element.clientWidth + 2));
    assert.ok(await analysis.evaluate(element => element.scrollWidth <= element.clientWidth + 2));
    await analysis.screenshot({ path: `${folder}/mixed-${width}.png` });
    await analysis.locator('summary').click();
    await analysis.getByRole('button', { name: 'Edit', exact: true }).click();
    await analysis.getByRole('textbox').fill('~deepseek/deepseek-flash-latest');
    await analysis.getByRole('button', { name: 'Save', exact: true }).click();
    await analysis.getByText('~deepseek/deepseek-flash-latest', { exact: true }).waitFor();
    for (const row of await section.getByRole('article').all()) {
      const model = await row.locator('.model-route-model-list code').boundingBox();
      const edit = await row.getByRole('button', { name: 'Edit', exact: true }).boundingBox();
      if (width > 1024) {
        const heading = await row.locator('h3').boundingBox();
        assert.ok(Math.abs(heading.y + heading.height / 2 - model.y - model.height / 2) < 3);
        assert.ok(Math.abs(edit.y + edit.height / 2 - model.y - model.height / 2) < 3);
      }
      assert.ok(await row.evaluate(element => element.scrollWidth <= element.clientWidth + 2));
    }
    await section.screenshot({ path: `${folder}/groups-${width}.png` });
    assert.deepEqual(errors, []);
    results.push({ width, rows: 4, groupEdit: true, groupReset: true, mixedVisible: true, errors });
    await page.close();
  }
} finally {
  await browser.close();
  rmSync(temporary, { recursive: true, force: true });
}
console.log(JSON.stringify({ isolatedStore: true, results }));
