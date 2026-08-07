import { test, expect } from '@playwright/test';
import { gotoApp, navigateTo, createAgent, deleteAgent } from './helpers';

test.describe('Chat & Task Execution', () => {
  test('chat input is visible on workspace page', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'chat');
    const input = page.locator('textarea, input[type="text"], [contenteditable="true"], [class*="chat-input"], [class*="message-input"]');
    await expect(input.first()).toBeVisible({ timeout: 10_000 });
  });

  test('can type a message in chat input', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'chat');
    const input = page.locator('textarea, input[type="text"], [contenteditable="true"]').first();
    await input.click();
    await input.fill('Hello, this is an E2E test message');
    await expect(input).toHaveValue('Hello, this is an E2E test message');
  });

  test('send button is present', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'chat');
    const sendButton = page.locator('button').filter({ hasText: /发送|Send|>/ }).or(page.locator('[class*="send"], [aria-label*="send"]'));
    await expect(sendButton.first()).toBeVisible({ timeout: 10_000 });
  });

  test('workspace area is visible', async ({ page }) => {
    await gotoApp(page);
    await navigateTo(page, 'chat');
    const workspace = page.locator('[class*="chat"], [class*="workspace"], [class*="panel"], main').first();
    await expect(workspace).toBeVisible({ timeout: 10_000 });
  });

  test('API: agent CRUD roundtrip', async ({ request }) => {
    const agent = await createAgent(request, 'E2E API Check', 'openai');
    expect(agent.id).toBeDefined();

    const res = await request.get('/api/v1/agents');
    expect(res.ok()).toBeTruthy();
    const agents = await res.json();
    const list = Array.isArray(agents) ? agents : agents.items || [];
    expect(list.some((a: any) => a.id === agent.id)).toBeTruthy();

    await deleteAgent(request, agent.id);

    const afterRes = await request.get('/api/v1/agents');
    const afterDelete = await afterRes.json();
    const afterList = Array.isArray(afterDelete) ? afterDelete : afterDelete.items || [];
    expect(afterList.some((a: any) => a.id === agent.id)).toBeFalsy();
  });
});
