/**
 * Optional page-level API overrides.
 *
 * Most scenarios are fully served by the fixture server, which is the single
 * source of app state. This module exists for the rare case where a scenario
 * needs a per-page response, and it deliberately uses a RegExp route: a
 * `**/api/v1/**` glob requires at least one path segment after `v1` and
 * silently lets some calls through to the server.
 */
import type { Page, Route } from '@playwright/test';

export interface RouteOverride {
  match: (pathname: string, method: string) => boolean;
  respond: (route: Route) => Promise<void> | void;
}

/**
 * Installs overrides on both the context and the page.
 *
 * Registering on the context as well as the page means a request issued during
 * the very first navigation, before the page-level handler is live, is still
 * covered.
 */
export async function installRouteOverrides(page: Page, overrides: RouteOverride[]) {
  const handler = async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    for (const override of overrides) {
      if (override.match(url.pathname, req.method())) {
        await override.respond(route);
        return;
      }
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  };

  await page.context().route(/\/api\/v1\//, handler);
  await page.route(/\/api\/v1\//, handler);
}
