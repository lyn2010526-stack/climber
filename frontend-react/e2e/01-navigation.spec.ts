import { test, expect } from '@playwright/test';
import { gotoApp, navigateTo } from './helpers';

test.describe('Navigation & Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('loads the main workspace page', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();
    const brand = page.locator('span').filter({ hasText: 'Climber' });
    await expect(brand.first()).toBeVisible();
  });

  test('navigates to Agents page via hash', async ({ page }) => {
    await navigateTo(page, 'agents');
    await expect(page).toHaveURL(/#agents/);
    const heading = page.getByRole('heading', { name: /Agents/ });
    await expect(heading).toBeVisible();
  });

  test('navigates to all core pages', async ({ page }) => {
    const pages = [
      { id: 'chat', label: '工作台' },
      { id: 'agents', label: '智能体' },
      { id: 'factory', label: '自主执行' },
      { id: 'tasks', label: '任务监控' },
      { id: 'settings', label: '设置' },
    ];

    for (const p of pages) {
      await navigateTo(page, p.id);
      await expect(page).toHaveURL(new RegExp(`#${p.id}$`));
    }
  });

  test('sidebar is visible with navigation items', async ({ page }) => {
    const sidebar = page.getByRole('complementary').first();
    await expect(sidebar).toBeVisible();

    const navLabels = ['Chat', 'Agents', 'Settings'];
    for (const label of navLabels) {
      await expect(sidebar.getByText(label).first()).toBeVisible();
    }
  });

  test('page transitions without critical console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      if (msg.type() === 'error'
        && !text.includes('favicon')
        && !text.includes('404')
        && !text.includes('Failed to load resource')) {
        errors.push(text);
      }
    });

    await navigateTo(page, 'agents');
    await page.waitForTimeout(500);
    await navigateTo(page, 'settings');
    await page.waitForTimeout(500);
    await navigateTo(page, 'chat');
    await page.waitForTimeout(500);

    expect(errors).toHaveLength(0);
  });
});
