import { chromium } from 'playwright';

const b = await chromium.launch({ executablePath: process.env.RESPONSIVE_CHROMIUM_PATH, args: ['--no-sandbox'] });
const p = await b.newPage();
p.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 300)));
await p.goto('http://localhost:5173', { waitUntil: 'networkidle' }).catch(e => console.log('goto err', e.message));
await p.waitForTimeout(2500);
const url = p.url();
const body = await p.evaluate(() => document.body.innerText.slice(0, 800));
console.log('URL:', url);
console.log('BODY:', JSON.stringify(body));
const links = await p.evaluate(() => Array.from(document.querySelectorAll('a,button')).map(el => (el.textContent || '').trim()).filter(Boolean).slice(0, 40));
console.log('LINKS:', JSON.stringify(links));
await b.close();