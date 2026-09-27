/**
 * Pixel comparison layer.
 *
 * Off by default. `VISUAL_PIXEL=1` turns it on, and the run then either writes a
 * baseline (`--update-snapshots`) or compares against one. The default-off
 * choice is deliberate: with the backend offline a pixel baseline recorded on an
 * empty page is a baseline nobody can judge, and it silently absorbs every later
 * regression. Structure always runs; pixels are an opt-in second layer.
 *
 * Baselines live under `artifacts/visual-baselines/<theme>/` with the platform
 * fingerprint recorded alongside, so a baseline captured on a different GPU or
 * font stack is identified instead of being diffed into noise.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';
import type { Theme } from './theme';

export const BASELINE_ROOT = join(process.cwd(), 'artifacts', 'visual-baselines');
export const FINGERPRINT_PATH = join(BASELINE_ROOT, 'platform-fingerprint.json');

/** Fraction of pixels allowed to differ before a comparison fails. */
const MAX_DIFF_PIXEL_RATIO = 0.001;
/** Anti-aliasing on text is unavoidable across font stacks; allow a little slack. */
const THRESHOLD = 0.18;

export function screenshotIsEnabled(): boolean {
  return process.env.VISUAL_PIXEL === '1';
}

export interface ScreenshotResult {
  path: string;
  compared: boolean;
}

function slug(value: string | null): string {
  return value ?? 'default';
}

/**
 * The snapshot name carries the theme as its first segment, so light and dark
 * land in separate trees and a theme flip can never overwrite the other side.
 * `expect.toHaveScreenshot.pathTemplate` in `playwright.config.ts` resolves this
 * name under `artifacts/visual-baselines/`.
 */
function snapshotNameFor(page: string, state: string | null, width: number, theme: Theme): string {
  return `${theme}/${slug(page)}__${slug(state)}__${width}px.png`;
}

function baselinePathFor(page: string, state: string | null, width: number, theme: Theme): string {
  return join(BASELINE_ROOT, snapshotNameFor(page, state, width, theme));
}

/**
 * Record what produced the baselines: browser build, platform, device pixel
 * ratio and the font families the app loads. Pixel output depends on all four,
 * so a mismatch invalidates comparison rather than merely making it noisy.
 */
export async function writePlatformFingerprint(page: Page): Promise<void> {
  mkdirSync(BASELINE_ROOT, { recursive: true });

  const fonts = await page.evaluate(() => {
    const probe = (family: string): string => {
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      if (!context) return 'unavailable';
      context.font = `16px ${family}`;
      return context.measureText('Climber mmWi1').width.toFixed(2);
    };
    return {
      inter: probe('Inter Variable'),
      jetbrainsMono: probe('JetBrains Mono Variable'),
      genericSans: probe('sans-serif'),
    };
  });

  const devicePixelRatio = await page.evaluate(() => window.devicePixelRatio);

  const fingerprint = {
    capturedAt: new Date().toISOString(),
    platform: process.platform,
    arch: process.arch,
    browserVersion: page.context().browser()?.version() ?? 'unknown',
    deviceScaleFactor: devicePixelRatio,
    viewport: page.viewportSize(),
    fontMetrics: fonts,
    notes: 'Font metric probes: differing values mean different rasterization; regenerate baselines.',
  };

  writeFileSync(FINGERPRINT_PATH, JSON.stringify(fingerprint, null, 2) + '\n', 'utf8');
}

export function readPlatformFingerprint(): Record<string, unknown> | null {
  if (!existsSync(FINGERPRINT_PATH)) return null;
  return JSON.parse(readFileSync(FINGERPRINT_PATH, 'utf8'));
}

/**
 * Compare the current page against its baseline, or write one when
 * `--update-snapshots` is passed. Returns whether a comparison actually ran, so
 * the report distinguishes "no baseline yet" from "matched".
 */
export async function maybeScreenshot(
  page: Page,
  descriptor: { page: string; state: string | null; width: number; theme: Theme },
): Promise<ScreenshotResult> {
  const path = baselinePathFor(descriptor.page, descriptor.state, descriptor.width, descriptor.theme);
  const existed = existsSync(path);

  await expect(page).toHaveScreenshot(
    snapshotNameFor(descriptor.page, descriptor.state, descriptor.width, descriptor.theme),
    {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: MAX_DIFF_PIXEL_RATIO,
      threshold: THRESHOLD,
      scale: 'css',
      fullPage: false,
    },
  );

  return { path, compared: existed };
}
