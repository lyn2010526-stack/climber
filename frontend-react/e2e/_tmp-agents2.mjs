import { chromium } from 'playwright';
const BASE = 'https://5173-1822695f51232c6b.monkeycode-ai.online';
const b = await chromium.launch({ executablePath: "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
p.on('response', async r => {
  if (r.request().method()==='POST' && r.url().includes('agents')) {
    console.log('POST', r.url().split('agents').pop(), r.status(), (await r.text().catch(()=>'')).slice(0,200));
  }
});
p.on('console', m => { if (m.type()==='error') console.log('console.error:', m.text().slice(0,150)); });
await p.goto(`${BASE}/#agents`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
await p.waitForSelector('[data-testid="agents-runtime-params"]', { timeout: 15000 });
console.log('params card ok');

const temp = p.locator('[data-testid="agents-params"] input[type=range]').first();
await temp.evaluate((el, v) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}, '0.9');

const name = `pw-runtime-${Date.now()}`;
await p.getByRole('button', { name: /new agent/i }).click();
console.log('form visible:', await p.getByPlaceholder('My Agent').count() > 0);
await p.getByPlaceholder('My Agent').fill(name);
await p.getByPlaceholder('sk-...').fill('sk-test-placeholder');
const nextBtn = p.getByRole('button', { name: /next/i });
console.log('next disabled:', await nextBtn.isDisabled().catch(()=>'err'));
await nextBtn.click();
console.log('after next1, step2 skills selectors count:', await p.getByText(/select skills/i).count());
await p.waitForTimeout(300);
await p.getByRole('button', { name: /next/i }).click();
console.log('after next2, step3 tools count:', await p.getByText(/select tools/i).count());
await p.waitForTimeout(300);
const createBtn = p.getByRole('button', { name: /create agent/i });
console.log('create btn count:', await createBtn.count());
await createBtn.click();
await p.waitForTimeout(2000);
const body = await p.locator('body').innerText();
console.log('name in body:', body.includes(name));
console.log('list ctx:', body.slice(body.indexOf('Agents') , body.indexOf('Agents')+120).replace(/\n/g,' | '));
await b.close();
