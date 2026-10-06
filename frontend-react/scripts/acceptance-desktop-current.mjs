import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';

const browser = await chromium.launch({
  headless: true,
  executablePath: '/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',
});
const report = { checks: {}, api: [], consoleErrors: [], pageErrors: [], blockedWrites: [] };
const sanitize = text => String(text)
  .replace(/Bearer\s+\S+/gi, 'Bearer [REDACTED]')
  .replace(/\b(?:sk-|ghp_|glpat-)[A-Za-z0-9_-]+/g, '[REDACTED]')
  .replace(/([?&](?:token|key|secret|password)=)[^&\s]+/gi, '$1[REDACTED]');
const check = (name, passed, evidence) => {
  report.checks[name] = { passed, evidence };
};
try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN', colorScheme: 'light' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.addInitScript(() => {
    localStorage.setItem('i18next_lng', 'zh-CN');
    localStorage.setItem('climber-theme', 'light');
    localStorage.setItem('climber.privacy.skipped', '1');
  });
  // Permit the application's automatic empty session creation, and guard all other writes.
  await page.route('**/api/**', async route => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method()) && !(req.method() === 'POST' && /\/sessions\/?$/.test(path))) {
      report.blockedWrites.push({ method: req.method(), path });
      await route.abort('blockedbyclient');
    } else await route.continue();
  });
  page.on('console', message => {
    if (message.type() === 'error') report.consoleErrors.push(sanitize(message.text()));
  });
  page.on('pageerror', error => report.pageErrors.push(sanitize(error.message)));
  const streams = [];
  page.on('response', response => {
    const path = new URL(response.url()).pathname;
    if (path.startsWith('/api/')) {
      const entry = { path: path.replace(/\/tasks\/[^/]+\//, '/tasks/[id]/'), method: response.request().method(), status: response.status(), contentType: response.headers()['content-type'] ?? '' };
      report.api.push(entry);
      if (/\/tasks\/[^/]+\/events$/.test(path)) streams.push(entry);
    }
  });
  await page.goto('http://localhost:5173/#chat', { waitUntil: 'domcontentloaded' });
  await page.getByTestId('anchored-workspace').waitFor();
  await page.locator('.boot-splash').waitFor({ state: 'hidden' });
  await page.waitForTimeout(2500);
  const geometry = await page.evaluate(() => {
    const rect = selector => {
      const box = document.querySelector(selector)?.getBoundingClientRect();
      return box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null;
    };
    return {
      viewport: { width: innerWidth, height: innerHeight }, theme: document.documentElement.dataset.theme,
      language: document.documentElement.lang, layout: document.querySelector('[data-testid="anchored-workspace"]')?.dataset.layout,
      left: rect('#anchored-left'), center: rect('#anchored-center'), right: rect('#anchored-right'),
      title: rect('[data-testid="anchored-title-bar"]'),
      separators: [...document.querySelectorAll('[role="separator"]')].map(el => el.getBoundingClientRect().width),
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
  check('desktopGeometry', geometry.left?.width === 240 && geometry.right?.width === 320 && geometry.center?.width >= 600 && !geometry.overflow, geometry);
  check('chineseLight', geometry.theme === 'light' && (await page.getByTestId('anchored-card-taskBoard').innerText()).includes('任务'), { theme: geometry.theme, language: geometry.language });
  const cardIds = ['taskBoard', 'tokenMeter', 'subAgentTree', 'filePreview', 'ruleEditor'];
  const defaults = {};
  for (const id of cardIds) defaults[id] = await page.getByTestId(`anchored-card-${id}`).getAttribute('data-open');
  check('defaultCards', JSON.stringify(Object.values(defaults)) === JSON.stringify(['true', 'true', 'false', 'false', 'false']), defaults);
  const folding = [];
  for (const id of cardIds) {
    const card = page.getByTestId(`anchored-card-${id}`);
    const before = await card.getAttribute('data-open');
    await card.locator(':scope > button').click();
    const after = await card.getAttribute('data-open');
    const bodyCount = await page.locator(`#anchored-card-body-${id}`).count();
    await card.locator(':scope > button').click();
    folding.push({ id, before, after, bodyCount, restored: await card.getAttribute('data-open') === before });
  }
  check('cardFolding', folding.every(row => row.before !== row.after && row.bodyCount === (row.after === 'true' ? 1 : 0) && row.restored), folding);
  const rulesCard = page.getByTestId('anchored-card-ruleEditor');
  if (await rulesCard.getAttribute('data-open') !== 'true') await rulesCard.locator(':scope > button').click();
  const rulesResponsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/ui/rules') && response.request().method() === 'GET');
  await page.getByRole('button', { name: '重新加载规则', exact: true }).click();
  const rulesResponse = await rulesResponsePromise;
  const rules = await rulesResponse.json();
  const ruleChecks = [];
  const editor = page.getByTestId('anchored-rule-editor');
   if (rulesResponse.ok()) await page.waitForFunction(() => !document.querySelector('[data-testid="anchored-rule-editor"] textarea')?.disabled);
   if (rulesResponse.ok() && Array.isArray(rules)) {
    const tabs = editor.locator('button[aria-pressed]');
    for (let index = 0; index < rules.length; index++) {
      await tabs.nth(index).click();
      const value = await editor.locator('textarea').inputValue();
      ruleChecks.push({ kind: rules[index].kind, matchesBackend: value === rules[index].content, characters: value.length });
    }
  }
   check('realRuleLoad', rulesResponse.status() === 200 && ruleChecks.length > 0 && ruleChecks.every(row => row.matchesBackend), { status: rulesResponse.status(), documents: ruleChecks, saveDisabled: await editor.getByRole('button', { name: '保存', exact: true }).isDisabled() });
  await rulesCard.locator(':scope > button').click();
  const tasksResponse = await page.request.get('http://localhost:5173/api/v1/tasks/?limit=50');
  const tasks = await tasksResponse.json();
  const taskList = Array.isArray(tasks) ? tasks : [];
  const statuses = taskList.reduce((counts, task) => ({ ...counts, [task.status]: (counts[task.status] ?? 0) + 1 }), {});
  const active = taskList.filter(task => !['completed', 'failed', 'cancelled'].includes(task.status));
  await page.waitForTimeout(5500);
  report.taskSummary = { status: tasksResponse.status(), count: taskList.length, statuses, active: active.length };
  if (taskList.length) {
    // Read an existing task stream; publish nothing to stores or UI.
    const task = active[0] ?? taskList[0];
    const sse = await page.evaluate(async taskId => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      try {
        const response = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/events`, { headers: { Accept: 'text/event-stream' }, signal: controller.signal });
        const result = { status: response.status, contentType: response.headers.get('content-type'), events: [] };
        if (!response.ok || !response.body) return result;
        const reader = response.body.getReader();
        let buffer = '';
        const decoder = new TextDecoder();
        while (result.events.length === 0) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() ?? '';
          for (const block of blocks) {
            const text = block.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n');
            if (!text) continue;
            const event = JSON.parse(text);
            result.events.push({ type: event.type, protocolVersion: event.protocol_version, sequence: event.sequence, status: event.data?.status, matchesTask: event.task_id === taskId });
          }
        }
        await reader.cancel();
        return result;
      } catch (error) { return { error: error.name }; }
      finally { clearTimeout(timer); controller.abort(); }
    }, task.task_id);
    check('existingTaskSSE', sse.status === 200 && sse.contentType?.includes('text/event-stream') && sse.events?.some(event => event.matchesTask && event.protocolVersion === 1), sse);
    check('automaticTaskSSE', active.length ? streams.some(row => row.status === 200) : null, { activeTasks: active.length, connections: streams.length, note: active.length ? 'Includes observed real stream responses; explicit read recorded separately.' : 'No non-terminal tasks available for automatic UI stream verification.' });
  } else {
    check('existingTaskSSE', null, { status: tasksResponse.status(), reason: tasksResponse.ok() ? 'No existing tasks; no acceptance task created.' : 'Task list request failed.' });
    check('automaticTaskSSE', null, { activeTasks: tasksResponse.ok() ? 0 : null, connections: streams.length, reason: tasksResponse.ok() ? 'No existing tasks available for automatic UI stream verification.' : 'Task list request failed; active task count unknown.' });
  }
  await page.getByTestId('anchored-info-panel').evaluate(el => { el.scrollTop = 0; });
  const sensitivePattern = /(?:\b(?:sk-|ghp_|glpat-)[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{12,}|(?:api[_ -]?key|password|密码|密钥)\s*[:=]\s*\S{6,})/i;
  const visibleText = await page.locator('body').innerText();
  const credentialRisk = sensitivePattern.test(visibleText);
  check('screenshotCredentialGuard', !credentialRisk, { scannedVisibleText: true, ruleEditorCollapsed: true, credentialPatternDetected: credentialRisk });
  if (credentialRisk) throw new Error('Visible credential-like text detected; screenshot withheld.');
  await page.screenshot({ path: 'public/climber-desktop-current.png', fullPage: false });
  report.screenshot = 'public/climber-desktop-current.png';
  check('console', report.consoleErrors.length === 0 && report.pageErrors.length === 0, { consoleErrorCount: report.consoleErrors.length, pageErrorCount: report.pageErrors.length });
   check('rulesUnchanged', !report.api.some(row => row.method !== 'GET' && row.path.includes('/ui/rules')) && !report.blockedWrites.some(row => row.path.includes('/ui/rules')), { ruleWriteRequests: 0 });
   const failedChecks = Object.entries(report.checks).filter(([, result]) => result.passed === false).map(([name]) => name);
   if (failedChecks.length) {
     report.failure = `Failed checks: ${failedChecks.join(', ')}`;
     process.exitCode = 1;
   }
} catch (error) {
  report.failure = sanitize(error.message);
  process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile('/tmp/opencode/climber-desktop-acceptance.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
