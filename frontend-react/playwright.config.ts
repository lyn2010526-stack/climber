import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { PREVIEW_ORIGIN, PREVIEW_DIST, previewWebServer } from './e2e/visual/fixtures/preview';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)));

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';
const IS_CI = !!process.env.CI;

// `workers: 1` keeps the default run serial, which is what the flow specs were
// written against. The visual matrix is a large independent fan-out, so
// E2E_WORKERS lets a caller widen it without changing anyone's default.
const WORKERS = Number(process.env.E2E_WORKERS || 1);

// Visual regression is a deterministic check: the same fixtures, the same
// geometry and the same threshold produce the same result on every attempt. A
// retry would re-run a fixed input, so it can only hide a real regression or
// absorb a flake. The visual group therefore pins retries to 0 and overrides the
// IS_CI-based business-flow default below. Only the flow projects keep retries.
const DETERMINISTIC_RETRIES = 0;

// A static preview bundle replaces the dev server for the visual group. The
// fixture router answers every API call inside the browser, so that group needs
// no backend; the flow projects still require both servers.
const USE_PREVIEW = process.env.VISUAL_PREVIEW === '1';

const FLOW_SERVERS = [
  {
    command: 'ENABLE_AUTH=false uvicorn app.main:app --host 0.0.0.0 --port 8000',
    cwd: '..',
    url: `${API_URL}/health`,
    reuseExistingServer: !IS_CI,
    timeout: 120_000,
    stdout: 'pipe' as const,
    stderr: 'pipe' as const,
  },
  {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !IS_CI,
    timeout: 120_000,
    stdout: 'pipe' as const,
    stderr: 'pipe' as const,
  },
];

export default defineConfig({
  testDir: './e2e',
  // The visual matrix is ~270 independent cases over 20 pages x 5 widths x 2
  // themes. Serialising whole files would keep it to a single worker no matter
  // what `workers` says, so tests inside a file are allowed to fan out. Every
  // visual test builds its own context and installs its own routes, so there is
  // no shared state for parallel workers to race on.
  globalTimeout: 60 * 60_000,
  fullyParallel: true,
  forbidOnly: IS_CI,
  retries: IS_CI ? 2 : 0,
  workers: WORKERS,
  reporter: IS_CI
    ? [['github'], ['html', { open: 'never' }]]
    : [['list'], ['html', { open: 'never' }]],
  timeout: 30_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      // Baselines land under artifacts/visual-baselines/<theme>/…, with the
      // theme carried in the snapshot name so a light run and a dark run are
      // separate trees and can never overwrite each other.
      //
      // Anchored to an absolute path: `{testDir}` is relative to each project's
      // own testDir, and the visual group overrides it, so a template built on
      // it would write outside the repository's artifacts directory.
      pathTemplate: `${REPO_ROOT}/artifacts/visual-baselines/{arg}{ext}`,
    },
  },
  use: {
    baseURL: BASE_URL,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: [/.*mobile\.spec\.ts/, /.*visual\/.*\.spec\.ts/],
    },
    {
      name: 'mobile',
      use: { ...devices['Pixel 7'] },
      testMatch: /.*mobile\.spec\.ts/,
    },
    {
      // Deterministic group: structure, theme and the optional pixel layer.
      name: 'visual',
      testDir: './e2e/visual',
      testMatch: /.*\.spec\.ts/,
      retries: DETERMINISTIC_RETRIES,
      use: {
        ...devices['Desktop Chrome'],
        ...(USE_PREVIEW ? { baseURL: PREVIEW_ORIGIN } : {}),
        // Structural geometry is asserted in CSS pixels; a fractional DPR would
        // turn every right-edge comparison into a rounding coin-flip.
        deviceScaleFactor: 1,
        isMobile: false,
        hasTouch: false,
      },
    },
  ],
  webServer: [
    ...previewWebServer(),
    ...(USE_PREVIEW ? [] : FLOW_SERVERS),
  ],
});

export { PREVIEW_DIST };
