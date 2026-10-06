import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

// Reuses existing servers. Local slash commands are real backend SSE, not model runs.
const origin = process.env.ACCEPTANCE_ORIGIN || 'http://localhost:5173';
const output = process.env.ACCEPTANCE_OUTPUT || '/tmp/opencode/climber-protocol-live';
const browser = await chromium.launch({ headless: true, ...(process.env.ACCEPTANCE_CHROME ? { executablePath: process.env.ACCEPTANCE_CHROME } : {}) });
const report = { origin, recordedAt: new Date().toISOString(), checks: [], recordings: [], browser: [], limitations: ['Local slash SSE does not validate model execution or engine queue consumption.', 'Browser checks use DOM geometry and real HTTP; no visual/brand assessment.'] };
const clean = value => String(value).replace(/Bearer\s+\S+/gi, 'Bearer [REDACTED]').replace(/\b(?:sk-|ghp_|glpat-)[A-Za-z0-9_-]+/g, '[REDACTED]');
const check = async (name, source, action) => {
  try { report.checks.push({ name, source, passed: true, evidence: await action() }); }
  catch (error) { report.checks.push({ name, source, passed: false, error: clean(error.message) }); }
  await writeFile(`${output}/recordings.json`, JSON.stringify(report.recordings, null, 2));
  await writeFile(`${output}/report.json`, JSON.stringify(report, null, 2));
  console.log(`${name}: ${report.checks.at(-1).passed ? 'PASS' : 'FAIL'}`);
};
// Respect the shared backend's 30/minute window between acceptance phases.
const cooldown = () => new Promise(resolve => setTimeout(resolve, 65000));
await mkdir(output, { recursive: true });
try {
  if (process.env.ACCEPTANCE_MODE !== 'smoke') {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  await context.addInitScript(() => {
    localStorage.setItem('i18next_lng', 'zh-CN');
    localStorage.setItem('climber.privacy.skipped', '1');
  });
  const page = await context.newPage();
  await check('running backend exposes final queue routes', 'live OpenAPI', async () => {
    // The frontend proxy exposes /api only, so read the backend schema directly.
    const backendOrigin = process.env.ACCEPTANCE_BACKEND_ORIGIN || 'http://localhost:8000';
    const schemaResponse = await page.request.get(`${backendOrigin}/openapi.json`, { timeout: 10000 });
    assert.equal(schemaResponse.status(), 200);
    const schema = await schemaResponse.json();
    const required = ['/api/v1/sessions/{session_id}/inputs', '/api/v1/sessions/{session_id}/inputs/report', '/api/v1/sessions/{session_id}/inputs/resume'];
    const missing = required.filter(path => !schema.paths[path]);
    assert.deepEqual(missing, [], `Missing queue paths: ${missing.join(', ')}`);
    return { backendOrigin, required };
  });
  await page.goto(`${origin}/#chat`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await cooldown();
  // An isolated new session keeps acceptance queue writes away from user sessions.
  let sessionId;
  await check('create isolated acceptance session', 'live HTTP', async () => {
    const response = await page.request.post(`${origin}/api/v1/sessions`, { data: { title: 'Protocol acceptance (no model execution)' }, timeout: 10000 });
    assert.equal(response.status(), 200);
    sessionId = (await response.json()).id;
    assert.equal(typeof sessionId, 'string');
    return { sessionId, status: response.status(), retained: true };
  });
  if (sessionId) {
    for (const [label, message, expected] of [['help', '/help', ['text', 'done']], ['command-error', '/level acceptance_invalid', ['error']]]) {
      await check(`record/replay ${label} SSE`, 'live backend recording replayed through production api.chatStream', async () => {
        const response = await page.request.post(`${origin}/api/v1/sessions/${sessionId}/slash`, { data: { message }, timeout: 10000 });
        assert.equal(response.status(), 200);
        assert.match(response.headers()['content-type'], /text\/event-stream/);
        const raw = await response.text();
        const result = await page.evaluate(async ({ raw, sessionId }) => {
          const { api } = await import('/src/api.ts');
          const { normalizeChatEvent } = await import('/src/types/chatEvents.ts');
          const frames = raw.trim().split('\n\n').map(block => {
            const lines = block.split('\n');
            return { event: lines.find(line => line.startsWith('event:'))?.slice(6).trim() || '', data: JSON.parse(lines.find(line => line.startsWith('data:')).slice(5)) };
          });
          const original = window.fetch;
          const events = [];
          let request;
          let stop;
          try {
            window.fetch = async (url, options) => {
              if (!String(url).endsWith(`/sessions/${sessionId}/chat`)) return original(url, options);
              request = { url: String(url), method: options.method, body: JSON.parse(options.body) };
              const bytes = new TextEncoder().encode(raw);
              return new Response(new ReadableStream({ start(controller) {
                for (let index = 0; index < bytes.length; index += 7) controller.enqueue(bytes.slice(index, index + 7));
                controller.close();
              } }), { headers: { 'Content-Type': 'text/event-stream' } });
            };
            await new Promise((resolve, reject) => {
              const timer = setTimeout(() => reject(new Error('Replay timed out')), 5000);
              stop = api.chatStream(sessionId, 'recording replay', event => {
                events.push(event);
                if (event.type === 'done' || event.type === 'error') { clearTimeout(timer); resolve(); }
              });
            });
            await new Promise(resolve => setTimeout(resolve, 20));
            return { events, normalized: frames.map(normalizeChatEvent), request };
          } finally { stop?.(); window.fetch = original; }
        }, { raw, sessionId });
        const recording = { label, source: 'live-backend-local-slash', endpoint: `/api/v1/sessions/${sessionId}/slash`, message, status: response.status(), contentType: response.headers()['content-type'], raw, expected: result.normalized, sha256: createHash('sha256').update(raw).digest('hex') };
        report.recordings.push(recording);
        assert.deepEqual(result.events, result.normalized);
        assert.deepEqual(result.events.map(event => event.type), expected);
        assert.deepEqual(result.request.body, { message: 'recording replay' });
        return { label, sha256: recording.sha256, eventTypes: expected, splitBytes: 7 };
      });
    }
    await cooldown();
    await check('queue idempotency, conflict, snapshot, report and review', 'live production API against isolated backend session', async () => {
      const result = await page.evaluate(async sessionId => {
        const { api } = await import('/src/api.ts');
        const steering = { client_request_id: 'acceptance-steering-1', kind: 'steering', message: 'Acceptance steering text' };
        const followUp = { client_request_id: 'acceptance-follow-up-1', kind: 'follow_up', message: 'Acceptance follow-up text' };
        const first = await api.submitSessionInput(sessionId, steering);
        const repeat = await api.submitSessionInput(sessionId, steering);
        const second = await api.submitSessionInput(sessionId, followUp);
        let conflict;
        try { await api.submitSessionInput(sessionId, { ...steering, message: 'different text' }); }
        catch (error) { conflict = { status: error.status, message: error.message }; }
        const snapshot = await api.getSessionInputs(sessionId);
        const report = await api.getSessionInputReport(sessionId);
        const unconfirmed = await fetch(`/api/v1/sessions/${sessionId}/inputs/resume`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ review_confirmed: false }) });
        const resumed = await api.resumeSessionInputs(sessionId, true);
        return { first, repeat, second, conflict, snapshot, report, unconfirmedStatus: unconfirmed.status, resumed };
      }, sessionId);
      assert.deepEqual(result.first, result.repeat);
      assert.equal(result.conflict.status, 409);
      assert.equal(result.unconfirmedStatus, 422);
      assert.equal(result.second.sequence, result.first.sequence + 1);
      assert.deepEqual(result.snapshot.map(item => item.kind), ['steering', 'follow_up']);
      assert.ok(result.snapshot.every(item => item.status === 'queued'));
      assert.deepEqual(result.report, { completed: [], executing: [], queued: [result.first.message, result.second.message], risks: [] });
      assert.deepEqual(result.resumed, result.snapshot);
      return result;
    });
  }
  await context.close();
  }
  for (const viewport of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
    await cooldown();
    await check(`actual page smoke ${viewport.width}px`, 'live page + live backend (no routes mocked)', async () => {
      const context = await browser.newContext({ viewport, locale: 'zh-CN', isMobile: viewport.width < 600, hasTouch: viewport.width < 600 });
      try {
        await context.addInitScript(() => {
          localStorage.setItem('i18next_lng', 'zh-CN');
          localStorage.setItem('climber.privacy.skipped', '1');
        });
        const page = await context.newPage();
        const evidence = { viewport, pageErrors: [], consoleErrors: [], failedHTTP: [], apiResponses: [] };
        page.on('pageerror', error => evidence.pageErrors.push(clean(error.message)));
        page.on('console', message => { if (message.type() === 'error') evidence.consoleErrors.push(clean(message.text())); });
        page.on('response', response => {
          if (new URL(response.url()).pathname.startsWith('/api/')) {
            const entry = { path: new URL(response.url()).pathname, status: response.status() };
            evidence.apiResponses.push(entry);
            if (response.status() >= 400) evidence.failedHTTP.push(entry);
          }
        });
        report.browser.push(evidence);
        await page.goto(`${origin}/#chat`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        const textarea = viewport.width < 600 ? page.locator('textarea').first() : page.getByTestId('anchored-composer').locator('textarea');
        await textarea.waitFor({ timeout: 15000 });
        await page.locator('.boot-splash').waitFor({ state: 'hidden', timeout: 15000 });
        // Session binding resets drafts on mount; wait for initial real HTTP to settle.
        await page.waitForTimeout(2000);
        await textarea.fill('Acceptance draft (never submitted)');
        assert.equal(await textarea.inputValue(), 'Acceptance draft (never submitted)');
        await textarea.fill('');
        evidence.draftInteraction = { entered: true, cleared: true, submitted: false };
        await page.waitForTimeout(1000);
        evidence.geometry = await textarea.evaluate(element => {
          const rect = element.getBoundingClientRect();
          return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, viewportWidth: innerWidth, viewportHeight: innerHeight, overflow: document.documentElement.scrollWidth > innerWidth };
        });
        assert.equal(evidence.geometry.overflow, false);
        assert.ok(evidence.geometry.x >= 0 && evidence.geometry.x + evidence.geometry.width <= viewport.width + 1);
        assert.ok(evidence.geometry.y >= 0 && evidence.geometry.y + evidence.geometry.height <= viewport.height + 1);
        assert.deepEqual(evidence.pageErrors, []);
        assert.deepEqual(evidence.consoleErrors, []);
        assert.deepEqual(evidence.failedHTTP, []);
        assert.ok(evidence.apiResponses.length > 0);
        return evidence;
      } finally { await context.close(); }
    });
  }
} finally {
  await browser.close();
  await writeFile(`${output}/recordings.json`, JSON.stringify(report.recordings, null, 2));
  await writeFile(`${output}/report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (report.checks.some(check => !check.passed)) process.exitCode = 1;
}
