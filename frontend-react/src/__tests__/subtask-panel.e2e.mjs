import { chromium } from 'playwright';

const BASE = process.env.PREVIEW_URL || 'http://localhost:5173';

const browser = await chromium.launch({
  executablePath: process.env.RESPONSIVE_CHROMIUM_PATH || undefined,
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

await page.goto(`${BASE}/#/tasks`, { waitUntil: 'networkidle', timeout: 40000 });
await page.waitForTimeout(2500);

const body = await page.evaluate(() => document.body.innerText.slice(0, 700));
const hasMonitorHeading = await page.locator('text=任务监控').count().catch(() => 0);
const hasDemoTask = await page.locator('text=演示子任务拉取链路').count().catch(() => 0);

let hasSubtasksHeading = 0;
let clickedClaim = false;
let claimedCount = 0;
if (hasDemoTask) {
  await page.locator('text=演示子任务拉取链路').first().click();
  await page.waitForTimeout(1500);
  hasSubtasksHeading = await page.locator('text=子任务').count();
  const claimBtn = page.getByRole('button', { name: '拉取子任务' });
  if (await claimBtn.count()) {
    await claimBtn.first().click();
    await page.waitForTimeout(1000);
    clickedClaim = true;
  }
  const claimed = await page.locator('text=已认领').count();
  claimedCount = claimed;
}

console.log(JSON.stringify({ hasMonitorHeading, hasDemoTask, hasSubtasksHeading, clickedClaim, claimedCount, errors, body }, null, 2));
await page.screenshot({ path: '/tmp/subtask-panel.png', fullPage: false });
await browser.close();