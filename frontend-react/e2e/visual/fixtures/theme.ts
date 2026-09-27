/**
 * Theme injection and verification.
 *
 * Setting `localStorage['climber-theme']` is only an intention — it says what
 * the app should do on its next mount. What the screenshot actually captures is
 * `document.documentElement[data-theme]` plus the CSS custom properties the
 * theme switch re-declares (`src/index.css:11` dark, `:222` light).
 *
 * So every themed assertion checks three independent layers, and a mismatch in
 * any one of them fails the test:
 *
 *   1. the stored preference the app reads on mount,
 *   2. the `data-theme` attribute the provider writes,
 *   3. a token that only resolves one way per theme — proof the cascade ran,
 *      which catches a theme applied to the attribute but not to the styles.
 */

import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

export const THEME_STORAGE_KEY = 'climber-theme';
export const THEMES = ['light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

/**
 * The token to sample. `--color-bg-page` is declared once per theme with
 * genuinely different values, so its computed value is a fingerprint of which
 * theme the cascade resolved — a `data-theme` attribute alone would not prove
 * that.
 */
const THEME_TOKEN = '--color-bg-page';

/** Resolved from `src/index.css`; a drift here is a product change, not a test bug. */
const EXPECTED_PAGE_BG: Record<Theme, string> = {
  light: 'rgb(246, 247, 249)',
  dark: 'rgb(24, 25, 28)',
};

export interface ThemeProof {
  theme: Theme;
  attribute: string | null;
  stored: string | null;
  pageBackground: string;
  textColor: string;
  matchesExpected: boolean;
}

function rgbToHex(rgb: string): string {
  const parts = rgb.match(/\d+(\.\d+)?/g);
  if (!parts || parts.length < 3) return rgb;
  return `#${parts.slice(0, 3)
    .map(part => Number(part).toString(16).padStart(2, '0'))
    .join('')}`;
}

/**
 * Install the theme before any application script runs. `addInitScript` is the
 * only way to win the race against the provider's mount effect, which reads
 * storage and writes the attribute in the same commit.
 */
export async function applyTheme(page: Page, theme: Theme): Promise<void> {
  await page.addInitScript(
    ([key, value]) => {
      window.localStorage.setItem(key as string, value as string);
    },
    [THEME_STORAGE_KEY, theme] as const,
  );
}

/** Force a colour-scheme so a UA preference cannot silently override the theme. */
export async function pinColorScheme(page: Page, theme: Theme): Promise<void> {
  await page.emulateMedia({ colorScheme: theme });
}

/** Read every layer that proves the theme is live. */
export async function readThemeProof(page: Page): Promise<ThemeProof> {
  const snapshot = await page.evaluate(
    ([token, storageKey]) => {
      const root = document.documentElement;
      const styles = getComputedStyle(root);
      const bodyStyles = getComputedStyle(document.body);
      return {
        attribute: root.getAttribute('data-theme'),
        stored: (() => {
          try {
            return window.localStorage.getItem(storageKey as string);
          } catch {
            return null;
          }
        })(),
        pageBackground: styles.getPropertyValue(token as string).trim(),
        textColor: (bodyStyles.color || styles.color).trim(),
      };
    },
    [THEME_TOKEN, THEME_STORAGE_KEY] as const,
  );

  const attribute = snapshot.attribute as Theme | null;
  const matchesExpected = attribute !== null
    && normalizeColor(snapshot.pageBackground) === EXPECTED_PAGE_BG[attribute];

  return {
    theme: attribute ?? 'light',
    attribute: snapshot.attribute,
    stored: snapshot.stored,
    pageBackground: snapshot.pageBackground,
    textColor: snapshot.textColor,
    matchesExpected,
  };
}

function normalizeColor(value: string): string {
  const trimmed = value.trim().toLowerCase();
  if (trimmed.startsWith('#')) {
    const hex = trimmed.length === 4
      ? trimmed.slice(1).split('').map(ch => ch + ch).join('')
      : trimmed.slice(1);
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return `rgb(${r}, ${g}, ${b})`;
  }
  // Collapse `rgb(24, 25, 28)` and `rgb(24 25 28 / 1)` to one spelling.
  const nums = trimmed.match(/\d+(\.\d+)?/g);
  return nums ? `rgb(${nums.slice(0, 3).map(Number).join(', ')})` : trimmed;
}

/**
 * Assert the theme is genuinely in effect. Returns the proof so the caller can
 * log the measured values into the report.
 */
export async function expectThemeApplied(page: Page, theme: Theme): Promise<ThemeProof> {
  await expect
    .poll(async () => (await readThemeProof(page)).attribute, {
      message: `data-theme should settle on "${theme}"`,
      timeout: 10_000,
    })
    .toBe(theme);

  const proof = await readThemeProof(page);

  expect(proof.attribute, 'data-theme must be present on <html>').toBe(theme);
  expect(proof.stored, 'theme preference must persist for the next mount').toBe(theme);

  // The cascade check: the token must resolve to this theme's value. Without
  // it, a provider that set the attribute but whose stylesheet failed to load
  // would still pass, and every baseline would be a single-theme baseline.
  expect(
    normalizeColor(proof.pageBackground),
    `${THEME_TOKEN} resolved to "${proof.pageBackground}", expected ${EXPECTED_PAGE_BG[theme]} for theme "${theme}"`,
  ).toBe(EXPECTED_PAGE_BG[theme]);
  // Text colour must differ from the page background — a legible baseline needs
  // foreground/background contrast, and this catches a theme that repainted the
  // page but left text on the old theme's value.
  expect(
    normalizeColor(proof.textColor),
    'body text colour must not equal the page background',
  ).not.toBe(normalizeColor(proof.pageBackground));

  return proof;
}

/** Flip the theme through the real UI control and re-verify. */
export async function toggleThemeViaUi(page: Page, toggle: Locator): Promise<Theme> {
  const before = await readThemeProof(page);
  await toggle.click();
  await expect
    .poll(async () => (await readThemeProof(page)).attribute, { timeout: 5_000 })
    .not.toBe(before.attribute);
  const after = await readThemeProof(page);
  return after.theme;
}

export function formatThemeProof(proof: ThemeProof): string {
  return [
    `theme=${proof.theme}`,
    `attr=${proof.attribute ?? 'null'}`,
    `stored=${proof.stored ?? 'null'}`,
    `--color-bg-page=${proof.pageBackground} (${rgbToHex(proof.pageBackground)})`,
    `color=${proof.textColor}`,
  ].join(' ');
}
