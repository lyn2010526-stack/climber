import assert from 'node:assert/strict';
import { chromium } from 'playwright';

// Browser acceptance with explicit API fixtures; no model execution is involved.
const browser = await chromium.launch({ headless: true, ...(process.argv[2] ? { executablePath: process.argv[2] } : {}) });
try {
  const page = await browser.newPage();
  const errors = [];
  const submissions = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('climber.privacy.skipped', '1');
    localStorage.setItem('i18next_lng', 'zh-CN');
  });
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body = {};
    if (path.endsWith('/sessions')) body = route.request().method() === 'POST'
      ? { id: 'input-session', title: 'Input acceptance', status: 'idle' } : [];
    else if (path.endsWith('/messages')) body = { messages: [] };
    else if (path.endsWith('/inputs/report')) body = { completed: [], executing: [], queued: [], risks: ['需要人工核实'] };
    else if (path.endsWith('/chat')) {
      // A legacy text-only fixture keeps the hook streaming until explicitly stopped.
      return route.fulfill({ contentType: 'text/event-stream', body: 'event: text\ndata: {"content":"working"}\n\nevent: runtime_report\ndata: {"completed":["已保存文件"],"executing":["正在检查"],"queued":["等待下一任务"],"risks":["需要人工核实"]}\n\n' });
    } else if (path.endsWith('/inputs')) {
      if (route.request().method() === 'POST') {
        const input = route.request().postDataJSON();
        submissions.push(input);
        body = { ...input, id: `input-${submissions.length}`, status: 'queued', sequence: submissions.length };
      } else body = { items: [] };
    } else if (path.endsWith('/chat-commands')) body = { commands: [] };
    else if (path.endsWith('/reasoning-level')) body = { level: 'medium' };
    else if (path.endsWith('/skills') || path.endsWith('/models')) body = [];
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/#chat');
  await page.getByTestId('anchored-composer').waitFor();
  await page.locator('.boot-splash').waitFor({ state: 'hidden' });
  const textbox = page.getByTestId('anchored-composer').locator('textarea');
  await textbox.fill('initial task');
  await textbox.press('Enter');
  const steering = page.getByRole('button', { name: '补充当前任务', exact: true });
  const followUp = page.getByRole('button', { name: '排队下一任务', exact: true });
  await steering.waitFor();
  for (const width of [1440, 768, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await textbox.fill(`correction ${width}`);
    await steering.click();
    await page.waitForFunction(() => document.querySelector('[data-testid="anchored-composer"] textarea').value === '');
    await textbox.fill(`next ${width}`);
    await followUp.click();
    await page.waitForFunction(() => document.querySelector('[data-testid="anchored-composer"] textarea').value === '');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.equal(await steering.isEnabled(), false);
    assert.equal(await page.locator('details').first().getAttribute('open'), null);
    const report = page.getByRole('region', { name: '运行报告' });
    assert.equal(await report.isVisible(), true);
    assert.equal(await report.locator('dt').count(), 4);
    assert.ok((await report.innerText()).includes('需要人工核实'));
    console.log(`Running input actions and collapsed queue passed at ${width}px.`);
  }
  assert.deepEqual(submissions.map(input => input.kind), ['steering', 'follow_up', 'steering', 'follow_up', 'steering', 'follow_up']);
  assert.equal(new Set(submissions.map(input => input.client_request_id)).size, 6);
  for (const input of submissions) assert.deepEqual(Object.keys(input).sort(), ['client_request_id', 'kind', 'message']);
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
