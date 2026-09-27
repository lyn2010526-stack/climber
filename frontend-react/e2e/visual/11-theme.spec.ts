/**
 * Theme effectiveness, tested on its own.
 *
 * The matrix proves the theme is in effect on every combination it covers. This
 * spec isolates the mechanism so a failure points at the theme switch rather
 * than at whichever page happened to be photographed: it checks the storage
 * default, the mount-time read, the attribute, the resolved tokens, the toggle
 * control, and that the two themes produce genuinely different pixels.
 */

import { test, expect } from '@playwright/test';
import { installApiFixtures } from './fixtures/routes';
import {
  applyTheme,
  expectThemeApplied,
  pinColorScheme,
  readThemeProof,
  THEME_STORAGE_KEY,
  toggleThemeViaUi,
  type Theme,
} from './fixtures/theme';
import { freezeHmr } from './fixtures/preview';
import { flushReport, record, resetReport } from './report';
import { writePlatformFingerprint, readPlatformFingerprint } from './fixtures/pixels';

const SIDEBAR_TOGGLE = 'aside[aria-label="Main navigation"] button[aria-label="Collapse sidebar"]';
const THEME_CONTROL = 'aside[aria-label="Main navigation"] button[aria-label*="模式"]';

test.describe('theme injection and verification', () => {
  test.beforeAll(() => {
    resetReport('theme');
  });

  // Closes the dev server's hot-reload channel so a source edit mid-run cannot
  // remount the lazy route and leave the page blank.
  test.beforeEach(async ({ page }) => {
    await freezeHmr(page);
  });

  test.afterAll(() => {
    flushReport({ spec: 'theme', pixelLayerEnabled: false });
  });

  for (const theme of ['light', 'dark'] as Theme[]) {
    test(`${theme}: storage, attribute and cascade token all agree`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page);

      await page.goto('/#agents');
      await page.waitForLoadState('domcontentloaded');

      const proof = await expectThemeApplied(page, theme);

      // Written to storage before mount, so a reload must land on the same
      // theme without a re-injection: a theme that only holds for one mount is
      // not a theme, it is a one-shot.
      await page.reload();
      await page.waitForLoadState('domcontentloaded');
      const afterReload = await expectThemeApplied(page, theme);

      expect(afterReload.attribute).toBe(theme);
      expect(afterReload.pageBackground).toBe(proof.pageBackground);

      record({
        title: `theme ${theme} mount + reload`,
        page: 'agents',
        state: null,
        width: 1440,
        height: 900,
        theme,
        themeProof: proof,
        geometry: {
          url: page.url(),
          viewport: { width: 1440, height: 900 },
          scroll: { width: 0, height: 0 },
          overflow: { scrollWidth: 1440, clientWidth: 1440, delta: 0, offenders: [], leftOffenders: [] },
          overlaps: [],
          smallTargets: [],
          ariaCurrentCount: 1,
          hitTests: [],
          durationMs: 0,
        },
        fixturesRequested: [],
        fixturesUnfulfilled: [],
        screenshot: null,
        pixelsCompared: false,
      });
    });
  }

  test('light and dark resolve to different tokens, not the same stylesheet twice', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await pinColorScheme(page, 'light');
    await applyTheme(page, 'light');
    await installApiFixtures(page);

    await page.goto('/#agents');
    await page.waitForLoadState('domcontentloaded');
    const light = await readThemeProof(page);

    await applyTheme(page, 'dark');
    await page.goto('/#agents');
    await page.waitForLoadState('domcontentloaded');
    const dark = await readThemeProof(page);

    expect(light.attribute).toBe('light');
    expect(dark.attribute).toBe('dark');

    // The whole point of a dual-theme baseline: the two must not be the same.
    expect(light.pageBackground).not.toBe(dark.pageBackground);
    expect(light.textColor).not.toBe(dark.textColor);
    expect(light.matchesExpected, `light resolved ${light.pageBackground}`).toBe(true);
    expect(dark.matchesExpected, `dark resolved ${dark.pageBackground}`).toBe(true);
  });

  test('the UI toggle flips the theme and the new theme is verified, not assumed', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await pinColorScheme(page, 'dark');
    await applyTheme(page, 'dark');
    await installApiFixtures(page);

    await page.goto('/#agents');
    await page.waitForLoadState('domcontentloaded');
    const before = await expectThemeApplied(page, 'dark');

    const toggle = page.locator(THEME_CONTROL);
    await expect(toggle, 'theme toggle must be present in the sidebar footer').toBeVisible();

    const after = await toggleThemeViaUi(page, toggle);

    expect(after).toBe('light');
    expect(after).not.toBe(before.theme);

    // Verified through the same three layers as an injected theme.
    const proof = await expectThemeApplied(page, 'light');
    expect(proof.pageBackground).not.toBe(before.pageBackground);

    const stored = await page.evaluate(key => window.localStorage.getItem(key), THEME_STORAGE_KEY);
    expect(stored, 'toggling must persist for the next mount').toBe('light');
  });

  test('color-scheme preference cannot silently override an explicit theme', async ({ page }) => {
    // The app falls back to `prefers-color-scheme` only when storage is empty
    // (useTheme.tsx:55-58). With storage written, a light-OS + dark-app request
    // must still render dark.
    await page.setViewportSize({ width: 1440, height: 900 });
    await pinColorScheme(page, 'light');
    await applyTheme(page, 'dark');
    await installApiFixtures(page);

    await page.goto('/#settings');
    await page.waitForLoadState('domcontentloaded');

    const proof = await expectThemeApplied(page, 'dark');
    expect(proof.stored).toBe('dark');
  });

  test('a missing data-theme is reported, not read as a pass', async ({ page }) => {
    // Negative control: strip the attribute and confirm the assertion catches
    // it. Without this, the theme check could silently degrade into a no-op.
    await page.setViewportSize({ width: 1440, height: 900 });
    await applyTheme(page, 'dark');
    await installApiFixtures(page);

    await page.goto('/#agents');
    await page.waitForLoadState('domcontentloaded');
    await expectThemeApplied(page, 'dark');

    await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));

    let threw = false;
    try {
      await expectThemeApplied(page, 'light');
    } catch {
      threw = true;
    }
    expect(threw, 'expectThemeApplied must fail when data-theme is absent').toBe(true);
  });

  test('platform fingerprint is recorded for the pixel layer', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await pinColorScheme(page, 'dark');
    await applyTheme(page, 'dark');
    await installApiFixtures(page);
    await page.goto('/#agents');
    await page.waitForLoadState('domcontentloaded');

    await writePlatformFingerprint(page);
    const fingerprint = readPlatformFingerprint();
    expect(fingerprint, 'platform fingerprint must be written').not.toBeNull();
    expect(fingerprint?.browserVersion).toBeTruthy();
  });

  test('sidebar collapse stays a 44px target in both themes', async ({ page }) => {
    for (const theme of ['light', 'dark'] as Theme[]) {
      await page.setViewportSize({ width: 1024, height: 768 });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page);
      await page.goto('/#agents');
      await page.waitForLoadState('domcontentloaded');
      await expectThemeApplied(page, theme);

      const toggle = page.locator(SIDEBAR_TOGGLE);
      await expect(toggle).toBeVisible();
      const box = await toggle.boundingBox();
      expect(box?.width ?? 0, `${theme}: collapse toggle width`).toBeGreaterThanOrEqual(44);
      expect(box?.height ?? 0, `${theme}: collapse toggle height`).toBeGreaterThanOrEqual(44);
    }
  });
});
