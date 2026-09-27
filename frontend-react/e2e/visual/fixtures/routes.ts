/**
 * `page.route` fixture layer.
 *
 * Every backend call the app can make during a visual test is answered from
 * `./contracts`. This is what makes a baseline readable: the page renders real
 * rows, so a layout defect shows up as a defect instead of as an empty shell
 * that happens to look the same in both themes.
 *
 * The router also records which paths were requested, so a spec can assert that
 * the page it is photographing actually loaded its data (see
 * `unfulfilledRequests`). Unmatched API paths are answered with a shape-matched
 * empty body and reported, never silently swallowed.
 */

import type { Page, Route } from '@playwright/test';
import * as fixtures from './contracts';

const API_PREFIX = /\/api\/v1(?:\/|$)/;
const HEALTH_PATH = /\/api\/v1\/health$/;

export interface FixtureOptions {
  /**
   * Overrides one or more responses, keyed by the same route table below. Use
   * it to drive a single page into a specific state (error, empty, streaming)
   * without forking the whole fixture set.
   */
  overrides?: Record<string, unknown>;
  /** Force a status code for a route table key, e.g. `{ '/doctor/': 500 }`. */
  statusOverrides?: Record<string, number>;
  /**
   * Holds the chat SSE response open for this long before completing, so the
   * streaming state is observable. `null` completes immediately.
   */
  streamDelayMs?: number | null;
}

export interface FixtureHandle {
  /** Paths (queries stripped) the page requested and the router answered. */
  readonly requested: Set<string>;
  /** Route-table keys that a request fell through to the default handler. */
  readonly unfulfilled: Set<string>;
  /** Release a held-open SSE response. Safe to call more than once. */
  releaseStreams: () => void;
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  });
}

/** Sse body in the wire format `readSSEStream` parses (api.ts:190-224). */
function sseBody(chunks: string[]): string {
  return chunks.map(chunk => `event: ${chunk}\n\n`).join('');
}

/**
 * Route table. Ordered most-specific first: the patterns are tested in order,
 * so `/sessions/:id/messages` is checked before `/sessions`.
 */
const ROUTES: Array<{ key: string; match: RegExp; resolve: () => unknown }> = [
  // --- health / auth ------------------------------------------------------
  { key: '/health', match: HEALTH_PATH, resolve: () => fixtures.healthCheck },
  { key: '/auth/health', match: /\/api\/v1\/auth\/health$/, resolve: () => fixtures.authHealth },
  { key: '/auth/me', match: /\/api\/v1\/auth\/me$/, resolve: () => fixtures.currentUser },
  { key: '/auth/keys', match: /\/api\/v1\/auth\/keys$/, resolve: () => fixtures.authApiKeys },

  // --- chat / sessions ----------------------------------------------------
  {
    key: '/sessions/:id/messages',
    match: /\/api\/v1\/sessions\/[^/]+\/messages$/,
    resolve: () => ({ messages: fixtures.sessionMessages }),
  },
  { key: '/sessions', match: /\/api\/v1\/sessions$/, resolve: () => fixtures.sessions },
  {
    key: '/sessions/:id/chat',
    match: /\/api\/v1\/sessions\/[^/]+\/chat$/,
    resolve: () => sseBody(['token: {"delta":"Hello from fixture"}', 'done']),
  },

  // --- agents / tools / models -------------------------------------------
  { key: '/agents', match: /\/api\/v1\/agents$/, resolve: () => fixtures.agents },
  { key: '/tools', match: /\/api\/v1\/tools$/, resolve: () => fixtures.tools },
  { key: '/models', match: /\/api\/v1\/models$/, resolve: () => fixtures.models },
  {
    key: '/models/discover',
    match: /\/api\/v1\/models\/discover$/,
    resolve: () => fixtures.modelDiscovery,
  },

  // --- skills / mcp / plugins --------------------------------------------
  { key: '/skills', match: /\/api\/v1\/skills$/, resolve: () => fixtures.skills },
  { key: '/mcp/servers', match: /\/api\/v1\/mcp\/servers$/, resolve: () => fixtures.mcpServers },
  { key: '/mcp/categories', match: /\/api\/v1\/mcp\/categories$/, resolve: () => fixtures.mcpCategories },
  { key: '/plugins', match: /\/api\/v1\/plugins$/, resolve: () => fixtures.plugins },
  {
    key: '/plugins/marketplace',
    match: /\/api\/v1\/plugins\/marketplace$/,
    resolve: () => fixtures.marketplace,
  },
  {
    key: '/plugins/categories',
    match: /\/api\/v1\/plugins\/categories$/,
    resolve: () => fixtures.pluginCategories,
  },

  // --- workflows / crews / groups ----------------------------------------
  { key: '/workflows', match: /\/api\/v1\/workflows\/?$/, resolve: () => fixtures.workflows },
  { key: '/crews', match: /\/api\/v1\/crews\/?$/, resolve: () => fixtures.crews },
  { key: '/groups', match: /\/api\/v1\/groups\/?$/, resolve: () => fixtures.groups },
  { key: '/documents', match: /\/api\/v1\/documents\/?$/, resolve: () => fixtures.documents },

  // --- observability ------------------------------------------------------
  { key: '/traces', match: /\/api\/v1\/traces\/?$/, resolve: () => fixtures.traces },
  {
    key: '/traces/:id',
    match: /\/api\/v1\/traces\/[^/]+$/,
    resolve: () => fixtures.traceDetail,
  },
  { key: '/doctor', match: /\/api\/v1\/doctor\/?$/, resolve: () => fixtures.doctorReport },
  { key: '/stats', match: /\/api\/v1\/stats$/, resolve: () => fixtures.stats },
  { key: '/cost/usage', match: /\/api\/v1\/cost\/usage$/, resolve: () => fixtures.costUsage },
  { key: '/cost/budget', match: /\/api\/v1\/cost\/budget$/, resolve: () => fixtures.costBudget },
  { key: '/cluster/status', match: /\/api\/v1\/cluster\/status$/, resolve: () => fixtures.clusterStatus },
  {
    key: '/arcbench/status',
    match: /\/api\/v1\/arcbench\/status$/,
    resolve: () => fixtures.arcbenchStatus,
  },
  { key: '/eval/datasets', match: /\/api\/v1\/eval\/datasets$/, resolve: () => fixtures.evalDatasets },

  // --- reasoning ----------------------------------------------------------
  { key: '/reason/modes', match: /\/api\/v1\/reason\/modes$/, resolve: () => fixtures.reasoningModes },
  {
    key: '/reason/history',
    match: /\/api\/v1\/reason\/history$/,
    resolve: () => fixtures.reasoningHistory,
  },
  {
    key: '/feedback/stats',
    match: /\/api\/v1\/feedback\/stats$/,
    resolve: () => fixtures.feedbackStats,
  },

  // --- tasks / scheduler / factory ---------------------------------------
  { key: '/tasks', match: /\/api\/v1\/tasks\/?$/, resolve: () => fixtures.tasks },
  {
    key: '/tasks/:id',
    match: /\/api\/v1\/tasks\/[^/]+$/,
    resolve: () => fixtures.taskDetail,
  },
  {
    key: '/scheduler/tasks',
    match: /\/api\/v1\/scheduler\/tasks$/,
    resolve: () => fixtures.schedulerTasks,
  },

  // --- config -------------------------------------------------------------
  { key: '/settings', match: /\/api\/v1\/settings\/?$/, resolve: () => fixtures.settings },
  { key: '/api-keys', match: /\/api\/v1\/api-keys$/, resolve: () => fixtures.apiKeys },
  {
    key: '/permissions/config',
    match: /\/api\/v1\/permissions\/config$/,
    resolve: () => fixtures.permissionConfig,
  },
];

/** List endpoints answer `[]` when unknown; everything else answers `{}`. */
const LIST_KEYS = new Set([
  '/agents',
  '/tools',
  '/models',
  '/skills',
  '/mcp/servers',
  '/mcp/categories',
  '/plugins',
  '/plugins/categories',
  '/workflows',
  '/crews',
  '/groups',
  '/documents',
  '/traces',
  '/eval/datasets',
  '/reason/modes',
  '/reason/history',
  '/tasks',
  '/scheduler/tasks',
  '/sessions',
  '/auth/keys',
]);

/**
 * Install the fixture router. Call before the first navigation so every
 * request the app makes during load is already answered.
 */
export async function installApiFixtures(
  page: Page,
  options: FixtureOptions = {},
): Promise<FixtureHandle> {
  const overrides = options.overrides ?? {};
  const statusOverrides = options.statusOverrides ?? {};
  const requested = new Set<string>();
  const unfulfilled = new Set<string>();
  const openStreams: Array<() => void> = [];

  await page.route(API_PREFIX, async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    const entry = ROUTES.find(candidate => candidate.match.test(path));

    if (!entry) {
      unfulfilled.add(path);
      // Unknown endpoints still get a shape the client can parse, so the page
      // renders instead of tripping over `undefined.items`.
      return json(route, LIST_KEYS.has(path) ? [] : {});
    }

    requested.add(entry.key);

    const forcedStatus = statusOverrides[entry.key];
    if (forcedStatus && forcedStatus >= 400) {
      return json(route, { detail: `fixture forced status ${forcedStatus}` }, forcedStatus);
    }

    // `overrides` may replace the body or supply a factory for a dynamic case.
    if (entry.key in overrides) {
      const override = overrides[entry.key];
      const body = typeof override === 'function'
        ? (override as () => unknown)()
        : override;
      return json(route, body);
    }

    // A held-open stream keeps `isStreaming` true while the page is measured and
    // photographed. The hold is deliberately short: the test releases it as soon
    // as it is done, and teardown releases it regardless, so a long hold would
    // only multiply the wall-clock cost of the streaming rows.
    if (entry.key === '/sessions/:id/chat' && options.streamDelayMs) {
      return new Promise<void>(resolve => {
        const release = () => {
          void json(route, sseBody(['token: {"delta":"Hello from fixture"}', 'done']))
            .catch(() => undefined)
            .finally(resolve);
        };
        openStreams.push(release);
        setTimeout(release, options.streamDelayMs ?? 0);
      });
    }

    return json(route, entry.resolve());
  });

  return {
    requested,
    unfulfilled,
    releaseStreams: () => {
      while (openStreams.length > 0) openStreams.pop()?.();
    },
  };
}

/** Fixture-backed session list, keyed for the chat-state matrix. */
export function sessionMessagesFor(state: 'empty' | 'messages'): { messages: unknown[] } {
  return { messages: state === 'empty' ? [] : fixtures.sessionMessages };
}
