import { chromium } from 'playwright';
const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const b = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const out = [];
await p.goto(`${BASE}/#chat`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
await p.waitForSelector('textarea', { timeout: 15000 }).catch(()=>out.push('textarea: MISSING'));
const ta = p.locator('textarea').first();
await ta.fill('请重构这个模块。');
await p.waitForTimeout(1400);
const body = await p.locator('body').innerText();
out.push(`clarify-bubble: ${/clarify before sending|ambiguous/i.test(body) ? 'OK' : 'MISSING'}`);
if (/clarify before sending/i.test(body)) {
  const qIdx = body.search(/clarify before sending/i);
  out.push(`bubble-text: ${body.slice(qIdx, qIdx + 120).replace(/\n/g, ' | ')}`);
}
await ta.fill('/');
await p.waitForTimeout(500);
const body2 = await p.locator('body').innerText();
out.push(`slash-menu: ${/^\/|commands|命令/i.test(body2.slice(body2.search('/')-10, body2.search('/')+200)) ? 'maybe' : 'n/a'}`);
const slashVisible = await p.getByRole('listbox').count().catch(()=>0);
out.push(`slash-listbox: ${slashVisible}`);
await p.screenshot({ path: '/tmp/opencode/chat-clarify.png' });
await b.close();
console.log(out.join('\n'));
