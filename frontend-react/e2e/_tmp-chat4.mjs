import { chromium } from 'playwright';
const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const b = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.on('response', async r => { if (r.url().includes('understand')) {
  const j = await r.json().catch(()=>null);
  console.log('RESP progress=', j?.progress, 'questions=', JSON.stringify(j?.clarification_questions));
}});
await p.goto(`${BASE}/#chat`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
await p.waitForSelector('textarea', { timeout: 15000 });
const ta = p.locator('textarea').first();
await ta.fill('请重构这个模块。');
await p.waitForTimeout(3500);
const body = await p.locator('body').innerText();
for (const probe of ['clarify before sending','指代','请明确','ambiguous']) {
  console.log(`probe '${probe}':`, body.includes(probe));
}
const idx = body.search(/指代|明确|clarify|ambiguous/i);
if (idx >= 0) console.log('ctx:', body.slice(idx-60, idx+120).replace(/\n/g,' | '));
await b.close();
