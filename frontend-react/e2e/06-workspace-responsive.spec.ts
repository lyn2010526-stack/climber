import { expect, test } from '@playwright/test';

const viewports = [
  { name: 'desktop-1440', width: 1440, height: 1000, page: 'dashboard' },
  { name: 'tablet-768', width: 768, height: 1024, page: 'chat' },
  { name: 'mobile-375', width: 375, height: 812, page: 'settings' },
];

for (const viewport of viewports) {
  test(`${viewport.name} workspace acceptance`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(`/#${viewport.page}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('.app-shell')).toBeVisible();

    const dimensions = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.innerWidth);

    const currentNavigation = page.locator('[aria-current="page"]:visible').first();
    await expect(currentNavigation).toBeVisible();

    const visibleButtons = page.locator('button:visible');
    const buttonCount = await visibleButtons.count();
    expect(buttonCount).toBeGreaterThan(0);
    for (let index = 0; index < Math.min(buttonCount, 12); index += 1) {
      const box = await visibleButtons.nth(index).boundingBox();
      if (box) expect(box.height).toBeGreaterThanOrEqual(44);
    }

    await page.keyboard.press('Tab');
    const focusVisible = await page.evaluate(() => {
      const element = document.activeElement;
      return element instanceof HTMLElement && element !== document.body;
    });
    expect(focusVisible).toBe(true);

    await page.screenshot({
      path: `artifacts/ui-acceptance/${viewport.name}.png`,
      fullPage: true,
    });
  });
}
