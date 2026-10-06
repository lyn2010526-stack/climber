import { chromium } from 'playwright';
const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const b = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
p.on('response', async r => {
  if (r.url().includes('/api/v1/agents') && r.request().method()==='POST') {
    console.log('POST body captured status', r.status());
    try { const j = await r.json(); console.log('resp json:', JSON.stringify(j).slice(0,400)); } catch(e){}
  }
});
await p.goto(`${BASE}/#agents`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
await p.waitForSelector('[data-testid="agents-runtime-params"]', { timeout: 20000 }).catch(()=>console.log('params card missing'));
const name = `pw-runtime-${Date.now()}`;
const nb = p.getByRole('button', { name: /new agent/i });
console.log('new agent btn:', await nb.count());
await nb.click();
await p.getByPlaceholder('My Agent').fill(name).catch(()=>console.log('name input missing'));
await p.getByPlaceholder('sk-...').fill('sk-test-placeholder').catch(()=>console.log('key input missing'));
await p.getByRole('button', { name: /next/i }).click();
await p.waitForTimeout(300);
await p.getByRole('button', { name: /next/i }).click();
await p.waitForTimeout(300);
await p.getByRole('button', { name: /create agent/i }).click();
await p.waitForTimeout(2000);
await b.close();
