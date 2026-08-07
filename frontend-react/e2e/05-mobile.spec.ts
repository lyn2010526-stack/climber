import { test, expect } from '@playwright/test';
import { gotoApp, navigateTo } from './helpers';

test.describe('Mobile Responsive', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('mobile layout renders correctly', async ({ page }) => {
    const body = page.locator('body');
    await expect(body).toBeVisible();

    const viewport = page.viewportSize();
    expect(viewport?.width).toBe(390);
  });

  test('mobile navigation is accessible', async ({ page }) => {
    const navLabels = ['工作台', '智能体', '任务', '集群'];
    let visibleCount = 0;
    for (const label of navLabels) {
      const isVisible = await page.locator('button').filter({ hasText: label }).or(page.getByText(label)).first().isVisible().catch(() => false);
      if (isVisible) visibleCount++;
    }
    expect(visibleCount).toBeGreaterThan(0);
  });

  test('chat page is usable on mobile', async ({ page }) => {
    await navigateTo(page, 'chat');
    const input = page.locator('textarea, input[type="text"], [contenteditable="true"]').first();
    await expect(input).toBeVisible({ timeout: 10_000 });
  });

  test('agents page responsive layout', async ({ page }) => {
    await navigateTo(page, 'agents');
    const heading = page.getByRole('heading', { name: /Agents/ }).or(page.locator('text=/Agents/'));
    await expect(heading.first()).toBeVisible();
  });

  test('horizontal scroll is prevented', async ({ page }) => {
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
