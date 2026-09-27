import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Page } from '@playwright/test';
import { installApiFixture, seedShellState } from './api-fixtures';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const NAV_CONFIG = path.join(HERE, '..', 'src', 'navigation', 'navConfig.ts');

/**
 * The scan matrix, shared by the sweep and the gate.
 *
 * It lives here rather than in either spec because Playwright refuses to let one
 * test file import another, and because a private copy in the gate would be a
 * silent coverage gap the first time someone added a page: the sweep would show
 * 53 routes and the gate would still cover 52.
 */

/**
 * Route ids come from the nav config, so the scan can never drift from the app.
 * A page added to the sidebar gets scanned without anyone editing a test.
 */
export function navRouteIds(): string[] {
  const source = readFileSync(NAV_CONFIG, 'utf8');
  const ids = new Set<string>();
  for (const match of source.matchAll(/^\s*\{\s*id:\s*'([a-z-]+)',\s*icon:/gm)) ids.add(match[1]!);
  return [...ids];
}

export const ROUTES = navRouteIds();

export const VIEWPORTS = [
  { width: 1440, height: 900, label: 'desktop' },
  { width: 390, height: 844, label: 'mobile' },
] as const;

export const THEMES = ['light', 'dark'] as const;

export type Theme = (typeof THEMES)[number];

/** How long to let a lazy route settle before scanning it. */
const SETTLE_MS = 700;

/** The Suspense fallback spinner, used as the "still loading" signal. */
const LOADING_SELECTOR = '.animate-spin';

/** How long a lazy route gets to appear before the scan gives up on it. */
const ROUTE_READY_TIMEOUT_MS = 25_000;

async function waitForStablePaint(page: Page, theme: Theme): Promise<void> {
  await page
    .waitForFunction(
      expected => document.documentElement.getAttribute('data-theme') === expected,
      theme,
      { timeout: 10_000 },
    )
    .catch(() => {});
  await page
    .evaluate(async () => {
      const running = document.getAnimations().filter(animation => animation.playState === 'running');
      // A transition that never settles must not hang the suite.
      await Promise.all(running.map(animation => animation.finished.catch(() => undefined)));
    })
    .catch(() => {});
}

/** Why a route was not scannable. `null` means it was scannable. */
export type Unscannable = 'overlay' | 'loading' | 'theme';

export function describeUnscannable(cause: Unscannable): string {
  switch (cause) {
    case 'overlay':
      return 'a dev-server error overlay was covering the app';
    case 'loading':
      return `the route was still showing its loading fallback after ${ROUTE_READY_TIMEOUT_MS}ms`;
    case 'theme':
      return 'the theme never reached the requested value';
  }
}

/**
 * Drives one route to a resting state with a real layout and real theme, backed
 * entirely by fixtures. Returns null when it is scannable, or the reason it is
 * not. Each reason would otherwise be scanned as if it were the app.
 */
export async function openRoute(
  page: Page,
  route: string,
  theme: Theme,
  width: number,
): Promise<Unscannable | null> {
  await page.setViewportSize({ width, height: width < 768 ? 844 : 900 });
  await installApiFixture(page, { populated: true });
  await seedShellState(page, theme);
  await page.goto(`/#${route}`);
  await page.waitForLoadState('domcontentloaded');

  // The route module is lazy, so the Suspense fallback is the honest signal
  // that there is nothing to scan yet. A fixed sleep races the module graph and
  // silently audits a spinner.
  await page.waitForSelector(LOADING_SELECTOR, { state: 'detached', timeout: ROUTE_READY_TIMEOUT_MS }).catch(() => {});
  await page.waitForTimeout(SETTLE_MS);
  await waitForStablePaint(page, theme);

  if ((await page.locator('vite-error-overlay').count()) > 0) return 'overlay';
  if ((await page.locator(LOADING_SELECTOR).count()) > 0) return 'loading';
  if ((await page.evaluate(() => document.documentElement.getAttribute('data-theme'))) !== theme) return 'theme';
  return null;
}
