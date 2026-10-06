import { chromium } from 'playwright';

const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const results = [];

async function run() {
  const browser = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('console', m => { if (m.type() === 'error') results.push(`console-error: ${m.text().slice(0, 160)}`); });

  // 1) Composer clarification bubble on #chat
  await page.goto(`${BASE}/#chat`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1500);
  const locked = await page.locator('[role="dialog"]').count();
  const textarea = page.locator('textarea').first();
  if (await textarea.count()) {
    await textarea.fill('请重构这个模块。');
    await page.waitForTimeout(1400);
    const body = await page.locator('body').innerText();
    const hasBubble = /clarify before sending|ambiguous/i.test(body) && /模块|重构/.test(body);
    results.push(`clarify-bubble: ${hasBubble ? 'OK' : 'MISSING'}`);
  } else {
    results.push(`composer-textarea: MISSING (lockDialog=${locked})`);
  }

  // 2) EvalDashboard quick check + reports on #eval
  await page.goto(`${BASE}/#eval`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1800);
  const h2 = await page.locator('h2').first().innerText().catch(() => '');
  results.push(`eval-page-title: ${h2}`);
  const outBox = page.getByPlaceholder(/Paste the agent output/i).first();
  if (await outBox.count()) {
    await outBox.fill('完成，输出包含 result 与 summary 两个关键字。');
    const firstContains = page.getByPlaceholder(/Must contain/i).first();
    if (await firstContains.count()) await firstContains.fill('result');
    await page.getByRole('button', { name: /Run check/i }).click();
    await page.waitForTimeout(1500);
    const body = await page.locator('body').innerText();
    const passed = /Passed|Score 100%|PASS/.test(body);
    results.push(`quick-check-result: ${passed ? 'OK' : 'NOT-SHOWN'}`);
  } else {
    results.push('quick-check-textarea: MISSING');
  }
  const reportsText = await page.getByText(/No evaluation reports stored yet/i).count();
  results.push(`eval-reports-empty: ${reportsText ? 'OK' : 'MISSING'}`);

  await page.screenshot({ path: '/tmp/opencode/ui-check-final.png', fullPage: false });
  await browser.close();
}

run().then(() => { console.log(results.join('\n')); }).catch(e => { console.error('SCRIPT-FAIL', e); });
