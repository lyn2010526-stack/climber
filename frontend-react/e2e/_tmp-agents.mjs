import { chromium } from 'playwright';
const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const b = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
p.on('response', r => { if (r.url().includes('/api/v1/agents') && r.request().method()==='POST') console.log('POST /agents status', r.status()); });
await p.goto(`${BASE}/#agents`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
await p.waitForSelector('[data-testid="agents-runtime-params"]', { timeout: 15000 });

const temp = p.locator('[data-testid="agents-params"] input[type=range]').first();
await temp.evaluate((el, v) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}, '0.9');
await p.waitForTimeout(300);

const name = `pw-runtime-${Date.now()}`;
await p.getByRole('button', { name: /new agent/i }).click();
await p.getByPlaceholder('My Agent').fill(name);
await p.getByPlaceholder('sk-...').fill('sk-test-placeholder');
await p.getByRole('button', { name: /next/i }).click();
await p.waitForTimeout(400);
await p.getByRole('button', { name: /next/i }).click();
await p.waitForTimeout(400);
await p.getByRole('button', { name: /create agent/i }).click();
await p.waitForTimeout(1500);

const card = p.locator(`[data-agent-id]`, { hasText: name }).last();
console.log('card found:', await card.count() > 0);
const cardText = await card.innerText();
console.log('card shows temp 0.9:', cardText.includes('T0.9'));
console.log('card ctx:', cardText.replace(/\n/g,' | ').slice(0,220));
await b.close();
