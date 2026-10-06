import assert from 'node:assert/strict';
import { chromium } from 'playwright';

// Real entry and geometry, with local API fixtures to isolate layout from backend availability.
const browser = await chromium.launch({ headless: true, ...(process.env.RESPONSIVE_CHROMIUM_PATH ? { executablePath: process.env.RESPONSIVE_CHROMIUM_PATH } : {}) });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('climber.privacy.skipped', '1');
    localStorage.setItem('i18next_lng', 'en');
  });
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname;
    const body = path.endsWith('/sessions') && route.request().method() === 'POST'
      ? { id: 'responsive-session', title: 'Responsive verification', status: 'idle' }
      : path.endsWith('/messages') || path.endsWith('/skills') || path.endsWith('/sessions') ? []
        : path.endsWith('/auth/me') ? { name: 'Layout test' }
          : path.endsWith('/chat-commands') ? { commands: [] } : {};
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
  });
  for (const width of [390, 768, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('http://localhost:5173/#chat');
    const workspace = page.getByTestId('anchored-workspace');
    await workspace.waitFor();
    await page.locator('.boot-splash').waitFor({ state: 'hidden' });
    await page.waitForTimeout(500);
    assert.equal(await page.getByTestId('anchored-chat-column').count(), 1);
    assert.equal(await page.locator('.mobile-bottom-nav').count(), 0);
    const geometry = await page.evaluate(() => {
      const rect = selector => {
        const node = document.querySelector(selector);
        return node ? Math.round(node.getBoundingClientRect().width) : null;
      };
      return {
        layout: document.querySelector('[data-testid="anchored-workspace"]').dataset.layout,
        chat: rect('[data-testid="anchored-chat-column"]'),
        left: rect('[data-testid="anchored-left-nav"]'),
        right: rect('#anchored-right'),
        overflow: document.documentElement.scrollWidth > innerWidth,
      };
    });
    assert.equal(geometry.overflow, false);
    if (width < 1162) {
      assert.equal(geometry.layout, 'drawers');
      assert.equal(geometry.chat, width);
      const trigger = page.getByRole('button', { name: 'Expand navigation' });
      await trigger.click();
      const dialog = page.getByRole('dialog');
      await dialog.waitFor();
      assert.equal(await dialog.getAttribute('aria-modal'), 'true');
      assert.ok((await dialog.boundingBox()).width < width);
      await page.keyboard.press('Shift+Tab');
      assert.equal(await dialog.evaluate(node => node.contains(document.activeElement)), true);
      await page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'hidden' });
      assert.equal(await trigger.evaluate(node => node === document.activeElement), true);
      await page.getByRole('button', { name: 'Info panel', exact: true }).click();
      await dialog.waitFor();
      await page.mouse.click(2, 400);
      await dialog.waitFor({ state: 'hidden' });
      await trigger.click();
      // The settings submenu ships collapsed, so expand it before using the anchor
      // that carries the hash.
      await page.getByRole('button', { name: 'Settings', exact: true }).click();
      await page.getByRole('link', { name: 'Open settings', exact: true }).click();
      await workspace.waitFor({ state: 'hidden' });
      assert.equal(new URL(page.url()).hash, '#settings');
      assert.equal(await page.locator('.mobile-content').count(), width === 390 ? 1 : 0);
      assert.ok((await page.locator('#main-content').innerText()).length > 0);
    } else {
      assert.equal(geometry.layout, 'three-column');
      assert.ok(geometry.chat >= 600);
      assert.ok(Math.abs(geometry.left - 240) <= 2);
      // The info panel ships collapsed so the chat keeps the width on first
      // load, then the chat column toggle opens it to its 320px default.
      assert.ok(geometry.right <= 2, `expected a collapsed info panel, got ${geometry.right}`);
      await page.getByRole('button', { name: 'Info panel', exact: true }).click();
      await page.waitForFunction(() => {
        const node = document.querySelector('#anchored-right');
        return node ? node.getBoundingClientRect().width > 200 : false;
      });
      const expanded = await page.evaluate(() => Math.round(document.querySelector('#anchored-right').getBoundingClientRect().width));
      assert.ok(Math.abs(expanded - 320) <= 2, `expected a 320px info panel, got ${expanded}`);
      assert.equal(await page.getByTestId('anchored-workspace').getAttribute('data-inspect-open'), 'true');
    }
    console.log(JSON.stringify({ width, ...geometry, drawersAndSettings: width < 1162 ? 'passed' : 'desktop' }));
  }
  await page.goto('http://localhost:5173/#chat');
  const composer = page.locator('[data-testid="anchored-chat-column"] textarea');
  await composer.fill('draft survives responsive layout');
  await composer.evaluate(node => { node.dataset.responsiveIdentity = 'original'; });
  for (const width of [768, 390, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    await page.waitForTimeout(150);
    assert.equal(await composer.inputValue(), 'draft survives responsive layout');
    assert.equal(await composer.getAttribute('data-responsive-identity'), 'original');
  }
  console.log('Live 1280 -> 768 -> 390 -> 1280 resize preserves the actual composer and draft.');
  assert.deepEqual(errors, []);
  console.log('Actual App entry and responsive browser checks passed (local API fixtures).');
} finally {
  await browser.close();
}
