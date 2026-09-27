/**
 * Structural assertions for every page × width × theme combination.
 *
 * The pixel comparison is the second layer and is off unless
 * `VISUAL_PIXEL=1` (see `fixtures/pixels.ts`). What always runs is the set of
 * structural checks, because those produce a readable failure and a measured
 * number; a pixel diff on top of an empty page produces neither.
 */

import { test, expect } from '@playwright/test';
import { installApiFixtures, sessionMessagesFor, type FixtureHandle } from './fixtures/routes';
import { applyTheme, expectThemeApplied, pinColorScheme, type Theme, type ThemeProof } from './fixtures/theme';
import {
  assertAriaCurrentUniqueness,
  assertClickable,
  probeClickable,
  assertNoHorizontalOverflow,
  assertNoOverlap,
  assertTouchTargets,
  collectGeometry,
  type GeometryReport,
  type HitTestResult,
} from './fixtures/geometry';
import { findKnownDefect } from './fixtures/defects';
import { maybeScreenshot, screenshotIsEnabled } from './fixtures/pixels';
import { freezeHmr } from './fixtures/preview';
import { flushReport, record, recordFailure, recordKnownDefect, resetReport } from './report';
import {
  buildMatrix,
  expectedHashFor,
  isMobileWidth,
  WIDTHS,
  HEIGHTS,
  type ChatState,
} from './matrix';

export type { ChatState } from './matrix';

/** Landmark selectors per surface, resolved at runtime. */
const DESKTOP_SIDEBAR = 'aside[aria-label="Main navigation"]';
const DESKTOP_MAIN = 'main#main-content';
const MOBILE_BOTTOM_NAV = 'nav.mobile-bottom-nav';
/** Touch-target scope on mobile: the whole shell, header and nav included. */
const MOBILE_CONTENT_SCOPE = '.mobile-workspace-shell';

/** The composer's send control. Desktop uses the i18n label, mobile a fixed one. */
const SEND_SELECTORS = [
  'button[aria-label="Send"]',
  'button[aria-label="发送消息"]',
  'button[type="submit"][aria-label]',
];
const COMPOSER_SELECTORS = [
  'textarea',
  'input[placeholder]',
  '[contenteditable="true"]',
];

/** Narrow the matrix while iterating: `VISUAL_ONLY=agents,chat` */
const ONLY = process.env.VISUAL_ONLY
  ? process.env.VISUAL_ONLY.split(',').map(s => s.trim()).filter(Boolean)
  : null;
const SKIP_PIXEL = process.env.VISUAL_SKIP_PIXEL === '1';

/** Chat states need a different fixture set; everything else uses the default. */
function fixtureOptionsFor(state: ChatState | null) {
  switch (state) {
    case 'empty':
      return { overrides: { '/sessions/:id/messages': sessionMessagesFor('empty') } };
    case 'streaming':
      // Held open so `isStreaming` is observable when the shot is taken. The
      // hold is short because teardown releases it; a long one would only slow
      // the matrix down.
      return { streamDelayMs: 3_000 };
    case 'error':
      return { statusOverrides: { '/sessions/:id/chat': 503 } };
    default:
      return {};
  }
}

/**
 * Wait for the lazy route to actually resolve and paint its own content.
 *
 * `App.tsx` suspends on a dynamic import and shows a `Loading` fallback while it
 * is pending. A screenshot taken during that window looks like a legitimately
 * empty page, which is how the previous baselines ended up blank. So readiness
 * is defined as "the fallback is gone and the main region has text", asserted
 * before any measurement or capture.
 *
 * Uses polling rather than `requestAnimationFrame` on purpose: a headless page
 * that is not the foreground tab throttles rAF to never firing, which would hang
 * the whole test.
 */
async function waitForRenderedPage(page: import('@playwright/test').Page, label: string) {
  await page.waitForLoadState('domcontentloaded');

  await expect
    .poll(
      async () => {
        const state = await page.evaluate(() => {
          const main = document.querySelector('main#main-content');
          const text = (main?.textContent ?? '').trim();
          return {
            loading: text === 'Loading' || text === '加载中' || text.length === 0,
            length: text.length,
          };
        });
        return state;
      },
      {
        message: `${label}: the lazy route never resolved; the main region is still the Loading fallback`,
        // Generous because the machine is shared: a slow dynamic import under
        // load is not a defect, and a genuinely broken route never renders at
        // all, so this still fails rather than absorbing anything.
        timeout: 30_000,
        intervals: [100, 150, 250, 400],
      },
    )
    .toMatchObject({ loading: false });

  const text = await page.evaluate(() => (document.querySelector('main#main-content')?.textContent ?? '').trim());
  expect(text.length, `${label}: the rendered main region must contain text`).toBeGreaterThan(0);
}

/**
 * `networkidle` is only meaningful when nothing is intentionally held open. The
 * streaming rows keep a response pending on purpose, so they skip the wait
 * instead of burning the full action timeout on every one of the 40 rows.
 */
async function settle(page: import('@playwright/test').Page, options: { skipNetworkIdle?: boolean } = {}) {
  await page.waitForLoadState('domcontentloaded');
  if (options.skipNetworkIdle) return;
  await page.waitForLoadState('networkidle').catch(() => undefined);
}

async function firstVisible(page: import('@playwright/test').Page, selectors: string[]): Promise<string | null> {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) === 0) continue;
    if (await locator.isVisible().catch(() => false)) return selector;
  }
  return null;
}

test.describe('visual matrix: structure + optional pixels', () => {
  test.beforeAll(() => {
    resetReport('matrix');
  });

  // Installed before any navigation, and before the theme script, so it applies
  // to the very first document the browser builds.
  test.beforeEach(async ({ page }) => {
    await freezeHmr(page);
  });

  // A failing combination must still land in the numeric report, so the failure
  // is captured here rather than only in the Playwright output.
  test.afterEach(async ({}, testInfo) => {
    const status = testInfo.status;
    if (status === testInfo.expectedStatus) return;
    const error = testInfo.errors
      .map(e => e.message ?? String(e))
      .join('\n---\n')
      .slice(0, 4000);
    recordFailure(testInfo.title, error);
  });

  test.afterAll(() => {
    flushReport({
    spec: 'matrix',
      pixelLayerEnabled: screenshotIsEnabled(),
      widths: WIDTHS,
      heights: HEIGHTS,
    });
  });

  for (const width of WIDTHS) {
    for (const theme of ['light', 'dark'] as Theme[]) {
      for (const entry of buildMatrix()) {
        if (ONLY && !ONLY.includes(entry.page)) continue;
        const mobile = isMobileWidth(width);
        const stateLabel = entry.state ? `[${entry.state}] ` : '';
        const title = `${stateLabel}${entry.page} @ ${width}px ${theme}${mobile ? ' (mobile)' : ''}`;

        test(title, async ({ page }) => {
          const started = Date.now();
          await page.setViewportSize({ width, height: HEIGHTS[width] });

          // 1. Theme, installed before app code runs.
          await pinColorScheme(page, theme);
          await applyTheme(page, theme);

          // 2. Deterministic backend fixtures.
          const fixtures: FixtureHandle = await installApiFixtures(page, fixtureOptionsFor(entry.state));

          // 3. Navigate to the page under test.
          await page.goto(`/#${entry.page}`);
          await waitForRenderedPage(page, title);
          await settle(page, { skipNetworkIdle: entry.state === 'streaming' });

          // 4. The theme must be in effect, proven at the cascade level.
          const themeProof: ThemeProof = await expectThemeApplied(page, theme);

          // 5. The page actually rendered its own surface.
          const expectedHash = expectedHashFor(entry.page, width);
          await expect
            .poll(() => page.evaluate(() => window.location.hash.replace(/^#\/?/, '')), {
              message: `expected hash "${expectedHash}" (mobile fallback resolves ${entry.page} → ${expectedHash})`,
            })
            .toBe(expectedHash);

          // 6. Fixtures were consumed, so the screenshot shows real content.
          expect(
            [...fixtures.unfulfilled],
            `${title}: these API paths had no fixture and fell back to an empty body — the baseline would be blank`,
          ).toEqual([]);

          // --- structural assertions -----------------------------------
          const overflow = await assertNoHorizontalOverflow(page, title);
          const ariaCurrentCount = await assertAriaCurrentUniqueness(page, { label: title });

          const overlaps = mobile
            ? // The bottom navigation is `position: fixed` (index.css:751-763),
              // so the scroll container behind it deliberately spans the full
              // height — its box is expected to extend under the nav, and the
              // `padding-bottom` reserve is what keeps the last row clear.
              // Pairing the nav with the composer asserts the thing that
              // matters: no input is trapped underneath it.
              await assertNoOverlap(page, [[MOBILE_BOTTOM_NAV, COMPOSER_SELECTORS[0]!]], { label: title })
            : await assertNoOverlap(page, [[DESKTOP_SIDEBAR, DESKTOP_MAIN]], { label: title });

          // The 44px floor is a hard requirement on touch surfaces and on the
          // collapsed sidebar; a wide desktop with an expanded sidebar keeps the
          // product's existing density, so the check is scoped to the controls
          // that are reachable by touch there.
          const smallTargets = await assertTouchTargets(page, {
            label: title,
            min: 44,
            scope: mobile ? MOBILE_CONTENT_SCOPE : DESKTOP_SIDEBAR,
          });

          // The composer must be reachable, and provably so through a real hit
          // test. A control that a known defect covers is probed and written
          // into the report with its measurements instead of being asserted, so
          // the finding carries numbers and disappears once it is fixed.
          const hitTests: HitTestResult[] = [];
          const knownDefectIds: string[] = [];

          // Send first (it is the control the requirement names), then the
          // message input. Each is probed by every candidate selector so a
          // localised label change cannot silently skip the check.
          const candidates = [...SEND_SELECTORS, ...COMPOSER_SELECTORS];
          const asserted: string[] = [];
          for (const selector of candidates) {
            const probe = await probeClickable(page, selector);
            if (!probe) continue;
            if (asserted.includes(probe.targetName)) continue;
            asserted.push(probe.targetName);

            if (probe.reachable) {
              hitTests.push(probe);
              continue;
            }

            const defect = findKnownDefect({ page: entry.page, width, control: selector });
            if (defect) {
              recordKnownDefect({
                ...defect,
                title,
                width,
                height: HEIGHTS[width],
                theme,
                state: entry.state,
                evidence: {
                  centerX: probe.centerX,
                  centerY: probe.centerY,
                  topmost: probe.topmost,
                  targetName: probe.targetName,
                },
              });
              if (!knownDefectIds.includes(defect.id)) knownDefectIds.push(defect.id);
              continue;
            }

            // No known cause: this is a new finding and it has to fail loudly.
            expect(
              probe.reachable,
              `${title}: "${selector}" (${probe.targetName}) is covered at its centre ` +
                `(${probe.centerX},${probe.centerY}) by ${probe.topmost} — it is visible but not clickable`,
            ).toBe(true);
          }
          expect(
            asserted.length,
            `${title}: neither a Send control nor a composer input was found, so reachability went unchecked`,
          ).toBeGreaterThan(0);

          // --- optional pixel layer --------------------------------------
          const screenshot = SKIP_PIXEL || !screenshotIsEnabled()
            ? null
            : await maybeScreenshot(page, { page: entry.page, state: entry.state, width, theme });

          const geometry: GeometryReport = await collectGeometry(page, page.url(), {
            overlaps,
            smallTargets,
            ariaCurrentCount,
            hitTests,
            durationMs: Date.now() - started,
          });

          record({
            title,
            page: entry.page,
            state: entry.state,
            width,
            height: HEIGHTS[width],
            theme,
            themeProof,
            geometry,
            fixturesRequested: [...fixtures.requested].sort(),
            fixturesUnfulfilled: [...fixtures.unfulfilled].sort(),
            screenshot: screenshot?.path ?? null,
            pixelsCompared: Boolean(screenshot?.compared),
            ...(knownDefectIds.length > 0 ? { knownDefects: knownDefectIds } : {}),
          });

          expect(
            await page.locator('body').isVisible(),
            `${title}: body must be rendered`,
          ).toBe(true);
        });
      }
    }
  }
});
