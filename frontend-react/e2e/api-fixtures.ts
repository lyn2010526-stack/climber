import type { BrowserContext, Page, Route } from '@playwright/test';

/**
 * Deterministic stand-in for the Climber API.
 *
 * Every `/api/v1/**` request is answered from this table, so a route under
 * audit always renders the same markup and an axe diff means a real regression.
 * Endpoints the app polls (sessions, agents, keys) get a small non-empty
 * fixture, which is where most of the accessibility surface lives: a list row
 * with a status, a delete action and a disclosure.
 */

export interface FixtureOptions {
  /** Render list-bearing endpoints with rows instead of an empty list. */
  populated?: boolean;
}

const now = '2026-01-15T09:30:00.000Z';

const sessions = [
  { id: 'sess-1', title: 'Kubernetes 迁移排查', status: 'active', created_at: now, updated_at: now, message_count: 4 },
  { id: 'sess-2', title: '', status: 'idle', created_at: now, updated_at: now, message_count: 0 },
];

const agents = [
  { id: 'agent-1', name: '架构评审', provider: 'openai', model_id: 'gpt-4o-mini', enabled: true, system_prompt: '你是架构评审助手。', created_at: now },
];

const apiKeys = [{ id: 'key-1', name: '生产环境', provider: 'openai', masked_key: 'sk-****1234', created_at: now }];

const tasks = [
  { id: 'task-1', objective: '批量重构认证中间件', status: 'running', progress: 0.4, total_steps: 5, task_type: 'agent_run', created_at: now },
];

const models = [
  { id: 'gpt-4o-mini', name: 'gpt-4o-mini', provider: 'openai', owned: true },
];

type Json = unknown;

const list = (items: Json[]) => ({ items, total: items.length, page: 1, page_size: 50 });

/** Exact-path fixtures. First match wins; `GET` and other verbs share the entry. */
const ROUTES: Record<string, (populated: boolean) => Json> = {
  '/api/v1/sessions': p => list(p ? sessions : []),
  '/api/v1/agents': p => list(p ? agents : []),
  '/api/v1/api-keys': p => list(p ? apiKeys : []),
  '/api/v1/auth/keys': p => list(p ? apiKeys : []),
  '/api/v1/tasks': p => list(p ? tasks : []),
  '/api/v1/models': p => list(p ? models : []),
  '/api/v1/skills': p => list(p ? [{ id: 'skill-1', name: '代码检索', description: '在仓库中检索代码', enabled: true }] : []),
  '/api/v1/workflows': p => list(p ? [{ id: 'wf-1', name: '发布流水线', enabled: true, nodes: [], edges: [] }] : []),
  '/api/v1/scheduler/tasks': p => list(p ? [{ id: 'sch-1', name: '每日巡检', schedule: '0 9 * * *', enabled: true }] : []),
  '/api/v1/tools': p => list(p ? [] : []),
  '/api/v1/crews/': p => list(p ? [{ id: 'crew-1', name: '发布小队', member_ids: ['agent-1'] }] : []),
  '/api/v1/groups/': p => list(p ? [{ id: 'grp-1', name: '值班组' }] : []),
  '/api/v1/mcp/servers': p => list(p ? [{ id: 'mcp-1', name: 'filesystem', status: 'connected' }] : []),
  '/api/v1/mcp/categories': () => ({ categories: ['filesystem', 'git'] }),
  '/api/v1/plugins/marketplace': p => list(p ? [{ id: 'plg-1', name: 'markdown-tools', description: 'Markdown 工具集', installed: false }] : []),
  '/api/v1/plugins/categories': () => ({ categories: ['productivity'] }),
  '/api/v1/traces/': p => list(p ? [{ trace_id: 'tr-1', name: 'chat.completion', duration_ms: 812, status: 'ok' }] : []),
  '/api/v1/stats': () => ({
    totals: { requests: 128, tokens_in: 20480, tokens_out: 5120, cost: 1.42, errors: 2 },
    by_model: [{ model: 'gpt-4o-mini', requests: 128, cost: 1.42 }],
    timeline: [{ date: '2026-01-15', requests: 128, cost: 1.42 }],
  }),
  '/api/v1/cost/usage': () => ({ total: 1.42, currency: 'USD', by_day: [{ date: '2026-01-15', cost: 1.42 }] }),
  '/api/v1/cost/budget': () => ({ monthly_budget: 50, spent: 1.42, currency: 'USD' }),
  '/api/v1/doctor/': () => ({ checks: [{ name: 'backend', status: 'ok', message: '运行正常' }, { name: 'database', status: 'ok', message: '运行正常' }] }),
  '/api/v1/settings/': () => ({ settings: { theme: 'dark', locale: 'zh-CN' } }),
  '/api/v1/auth/me': () => ({ id: 'user-1', username: 'auditor', email: 'auditor@example.com', is_admin: true }),
  '/api/v1/auth/health': () => ({ status: 'ok', authenticated: false, requires_auth: false }),
  '/api/v1/health': () => ({ status: 'ok' }),
  '/api/v1/permissions/config': () => ({ mode: 'ask', rules: [], allowed_tools: [], denied_tools: [] }),
  '/api/v1/reason/modes': () => ({ modes: ['fast', 'balanced', 'deep'] }),
  '/api/v1/eval/datasets': p => list(p ? [{ id: 'ds-1', name: '回归集', size: 20 }] : []),
  '/api/v1/cluster/status': () => ({ healthy: true, members: 3, nodes: [] }),
  '/api/v1/arcbench/status': () => ({ running: false, progress: 1, phase: 'done' }),
  '/api/v1/feedback/stats': () => ({ total: 0, positive: 0, negative: 0 }),
  '/api/v1/documents/': p => list(p ? [] : []),
  '/api/v1/notifications/send': () => ({ sent: true }),
  '/api/v1/notifications/test': () => ({ sent: true }),
  '/api/v1/terminal/execute': () => ({ stdout: '', exit_code: 0 }),
};

const stripQuery = (url: string) => url.split('?')[0]!.replace(/\/+$/, '') || '/';

function json(route: Route, body: Json, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    headers: { 'access-control-allow-origin': '*' },
    body: JSON.stringify(body),
  });
}

/** Contexts that already carry the fixture handlers, and their current options. */
const INSTALLED = new WeakMap<BrowserContext, FixtureOptions>();

/**
 * Installs the fixture. Any unmatched API path resolves to an empty list, so
 * an unknown page still renders and the scan covers it instead of hanging.
 *
 * The handlers are registered on the browser context, once. Re-registering them
 * per route stacks another interceptor on every navigation, so 104 scans of one
 * page would each pay for 104 of them. Per-route options live in the map, so
 * changing them does not need a new registration.
 */
export async function installApiFixture(page: Page, options: FixtureOptions = {}): Promise<void> {
  const populated = options.populated ?? true;
  const context = page.context();
  const installed = INSTALLED.get(context);

  if (installed) {
    installed.populated = populated;
    return;
  }

  const state: FixtureOptions = { populated };
  INSTALLED.set(context, state);

  await context.route('**/api/v1/**', async route => {
    const path = stripQuery(new URL(route.request().url()).pathname);
    const factory = ROUTES[path];
    if (factory) return json(route, factory(state.populated));

    // Collection-ish paths answer with a list shape; everything else is an
    // empty object, which keeps `data.x` accesses from throwing at render time.
    if (/\/$/.test(new URL(route.request().url()).pathname) === false && path.split('/').length > 3) {
      return json(route, {});
    }
    return json(route, list([]));
  });

  await context.route('**/api/v1/sessions/**/messages', route => json(route, list([])));
  await context.route('**/health', route => json(route, { status: 'ok' }));

  // The chat surface opens a websocket. A short close keeps the console clean
  // and the stream in a settled state during the scan.
  await context.routeWebSocket('**/ws/**', ws => {
    ws.close();
  });
}

/**
 * Seeds the pieces of browser state the shell reads before first paint.
 *
 * The theme travels as a cookie, which the init script below reads. The init
 * script itself is registered once per page: `addInitScript` has no replace
 * option, so registering per route would leave 104 of them to run on every
 * navigation.
 */
export async function seedShellState(page: Page, theme: 'light' | 'dark'): Promise<void> {
  await page.context().addCookies([
    { name: THEME_COOKIE, value: theme, url: 'http://localhost:5173' },
  ]);

  if (SEEDED.has(page)) return;
  SEEDED.add(page);
  await page.addInitScript(cookieName => {
    localStorage.setItem('i18next_lng', 'zh-CN');
    const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${cookieName}=(light|dark)`));
    if (match) localStorage.setItem('climber-theme', match[1]!);
  }, THEME_COOKIE);
}

const THEME_COOKIE = 'climber-theme';

/** Pages that already carry the seeding init script. */
const SEEDED = new WeakSet<Page>();
