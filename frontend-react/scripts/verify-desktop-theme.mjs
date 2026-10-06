import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';

const CHROME = process.env.ACCEPTANCE_CHROME
  ?? '/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome';
const BASE = process.env.ACCEPTANCE_BASE ?? 'http://localhost:5173';
const browser = await chromium.launch({ headless: true, executablePath: CHROME });
const report = { checks: {}, consoleErrors: [], pageErrors: [] };
const check = (name, passed, evidence) => { report.checks[name] = { passed, evidence }; };

const readTokens = () => {
  const styles = getComputedStyle(document.querySelector('[data-testid="anchored-workspace"]'));
  return {
    theme: document.documentElement.dataset.theme,
    page: styles.getPropertyValue('--color-bg-page').trim(),
    surface1: styles.getPropertyValue('--color-bg-surface-1').trim(),
    textPrimary: styles.getPropertyValue('--color-text-primary').trim(),
    background: getComputedStyle(document.querySelector('.workbench-desktop-canvas')).backgroundColor,
  };
};

try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN', colorScheme: 'light' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('console', (m) => { if (m.type() === 'error') report.consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => report.pageErrors.push(e.message));

  await page.addInitScript(() => {
    localStorage.setItem('i18next_lng', 'zh-CN');
    localStorage.setItem('climber-theme', 'light');
    localStorage.setItem('climber.privacy.skipped', '1');
  });
  // Only reads and the app's automatic empty-session POST are permitted.
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method()) && !(req.method() === 'POST' && /\/sessions\/?$/.test(path))) {
      await route.abort('blockedbyclient');
    } else await route.continue();
  });

  await page.goto(`${BASE}/#chat`, { waitUntil: 'domcontentloaded' });
  await page.getByTestId('anchored-workspace').waitFor();
  await page.locator('.boot-splash').waitFor({ state: 'hidden' });
  await page.waitForTimeout(2000);

  const light = await page.evaluate(readTokens);
  check('lightDefault', light.theme === 'light' && light.page === '#ffffff', light);

  // Flip the theme through the real toggle control in the navigation footer.
  const toggle = page.getByRole('button', { name: /模式/ });
  await toggle.click();
  await page.waitForTimeout(400);
  const dark = await page.evaluate(readTokens);
  check('darkSwitch', dark.theme === 'dark' && dark.page !== '#ffffff' && dark.background !== light.background, { light: light.background, dark: dark.background, darkTokens: dark });

  const stored = await page.evaluate(() => localStorage.getItem('climber-theme'));
  check('darkPersisted', stored === 'dark', { stored });

  await page.screenshot({ path: 'public/climber-desktop-dark.png', fullPage: false });

  await toggle.click();
  await page.waitForTimeout(400);
  const backToLight = await page.evaluate(readTokens);
  check('toggleBackToLight', backToLight.theme === 'light' && backToLight.page === '#ffffff', backToLight);
  await page.screenshot({ path: 'public/climber-desktop-light.png', fullPage: false });

  report.screenshots = ['public/climber-desktop-light.png', 'public/climber-desktop-dark.png'];
  check('console', report.consoleErrors.length === 0 && report.pageErrors.length === 0, {
    consoleErrorCount: report.consoleErrors.length,
    pageErrorCount: report.pageErrors.length,
  });
  const failed = Object.entries(report.checks).filter(([, r]) => r.passed === false).map(([n]) => n);
  if (failed.length) { report.failure = `Failed checks: ${failed.join(', ')}`; process.exitCode = 1; }
} catch (error) {
  report.failure = error.message;
  process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile('/tmp/opencode/climber-desktop-theme.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
