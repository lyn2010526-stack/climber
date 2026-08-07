import { test, expect } from '@playwright/test';
import { gotoApp, navigateTo } from './helpers';

test.describe('Dashboard & Settings', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('stats page loads with content', async ({ page }) => {
    await navigateTo(page, 'stats');
    await page.waitForTimeout(1000);
    const hasContent = await page.locator('h1, h2, h3, p, span, div').first().isVisible().catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test('cost page shows content', async ({ page }) => {
    await navigateTo(page, 'cost');
    await page.waitForTimeout(1000);
    const bodyText = await page.locator('body').textContent();
    const hasContent = (bodyText?.trim().length ?? 0) > 50;
    expect(hasContent).toBeTruthy();
  });

  test('task monitor page loads', async ({ page }) => {
    await navigateTo(page, 'tasks');
    await page.waitForTimeout(1000);
    const bodyText = await page.locator('body').textContent();
    const hasContent = (bodyText?.trim().length ?? 0) > 50;
    expect(hasContent).toBeTruthy();
  });

  test('settings page has interactive elements', async ({ page }) => {
    await navigateTo(page, 'settings');
    const interactive = page.locator('button, input, [role="switch"], select, [class*="toggle"]').first();
    await expect(interactive).toBeVisible({ timeout: 10_000 });
  });
});
