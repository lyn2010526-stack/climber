import { Page, expect, APIRequestContext } from '@playwright/test';

export async function gotoApp(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('i18next_lng', 'en');
  });
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

export async function navigateTo(page: Page, pageId: string) {
  await page.evaluate((id) => {
    window.location.hash = id;
  }, pageId);
  await page.waitForTimeout(500);
}

export async function createAgent(request: APIRequestContext, name: string, provider = 'openai', modelId = 'gpt-4o-mini') {
  // Agent creation is rate limited, so a burst of suites can transiently hit
  // 429. Retry with a growing delay so a spec failure always means a real
  // contract break rather than a throttled request.
  let lastStatus = 0;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const res = await request.post('/api/v1/agents', { data: { name, provider, model_id: modelId } });
    if (res.ok()) return res.json();
    lastStatus = res.status();
    if (lastStatus !== 429) break;
    await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
  }
  throw new Error(`Create agent failed: ${lastStatus}`);
}

export async function deleteAgent(request: APIRequestContext, id: string) {
  const res = await request.delete(`/api/v1/agents/${id}`);
  if (!res.ok() && res.status() !== 404) throw new Error(`Delete agent failed: ${res.status()}`);
}

export async function cleanupTestAgents(request: APIRequestContext, prefix = 'E2E') {
  const res = await request.get('/api/v1/agents');
  if (!res.ok()) return;
  const agents = await res.json();
  const list = Array.isArray(agents) ? agents : agents.items || [];
  for (const agent of list) {
    if (agent.name?.startsWith(prefix)) {
      try { await deleteAgent(request, agent.id); } catch {}
    }
  }
}
