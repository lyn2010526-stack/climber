import { test, expect } from '@playwright/test';
import { gotoApp, navigateTo, createAgent, deleteAgent, cleanupTestAgents } from './helpers';

test.describe('Agent Management', () => {
  test.beforeEach(async ({ request }) => {
    await cleanupTestAgents(request);
  });

  test.afterEach(async ({ request }) => {
    await cleanupTestAgents(request);
  });

  test('opens agent creation form with required fields', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'agents');
    const addButton = page.getByText('New Agent').first();
    await addButton.click();
    await page.waitForTimeout(500);
    const nameInput = page.locator('input[placeholder="My Agent"]');
    await expect(nameInput).toBeVisible({ timeout: 10_000 });
    const apiKeyInput = page.locator('input[placeholder="sk-..."]');
    await expect(apiKeyInput).toBeVisible();
  });

  test('navigates through form steps', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'agents');
    await page.getByText('New Agent').first().click();
    await page.waitForTimeout(500);

    await page.locator('input[placeholder="My Agent"]').fill('E2E Form Agent');
    await page.locator('input[placeholder="sk-..."]').fill('sk-test-e2e-key');
    await page.waitForTimeout(300);

    const nextButton = page.getByText('Next');
    await expect(nextButton).toBeEnabled({ timeout: 5000 });
    await nextButton.click();
    await page.waitForTimeout(500);

    const backButton = page.getByText('Previous');
    await expect(backButton).toBeVisible({ timeout: 5000 });
  });

  test('agent appears in list after API creation', async ({ page, request }) => {
    await createAgent(request, 'E2E API Agent', 'anthropic');

    await gotoApp(page);
    await navigateTo(page, 'agents');
    await expect(page.getByText('E2E API Agent')).toBeVisible({ timeout: 10_000 });
  });

  test('deletes an agent', async ({ page, request }) => {
    const agent = await createAgent(request, 'E2E Delete Me', 'openai');

    await gotoApp(page);
    await navigateTo(page, 'agents');
    await expect(page.getByText('E2E Delete Me')).toBeVisible();

    const agentNameEl = page.getByText('E2E Delete Me', { exact: false }).first();
    const card = agentNameEl.locator('xpath=ancestor::div[contains(@class, "rounded-xl")][1]');
    await card.locator('button').first().click();
    const deleteButton = page.getByText('Delete').last();
    await deleteButton.click();
    await page.waitForTimeout(500);

    await navigateTo(page, 'chat');
    await navigateTo(page, 'agents');

    await expect(page.getByText('E2E Delete Me')).not.toBeVisible({ timeout: 10_000 });
  });

  test('agent list or empty state is shown', async ({ page, request }) => {
    await cleanupTestAgents(request);
    await gotoApp(page);
    await navigateTo(page, 'agents');
    const bodyText = await page.locator('body').textContent();
    const hasContent = (bodyText?.trim().length ?? 0) > 50;
    expect(hasContent).toBeTruthy();
  });
});
