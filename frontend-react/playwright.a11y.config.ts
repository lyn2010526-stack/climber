import { defineConfig, devices } from '@playwright/test';

/**
 * Config for the accessibility suite.
 *
 * Differences from `playwright.config.ts`:
 * - Only the Vite dev server starts. The a11y specs drive every API call through
 *   `e2e/api-fixtures.ts`, so a running backend is a source of non-determinism.
 * - `retries: 0`. An axe result must be reproducible on the same commit; a
 *   retry that passes after a failure is exactly the flake this suite forbids.
 * - The narrow viewport is driven per-test via `setViewportSize` so one worker
 *   covers 1440x900 and 390x844 for the same route.
 */
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';

export default defineConfig({
  testDir: './e2e',
  testMatch: /.*a11y.*\.spec\.ts/,
  // The gate sweeps 52 routes across 2 themes and 2 viewports, and the sweep
  // covers the same matrix again, so this is a long run by design. It stays
  // bounded so a hung page cannot hold CI open indefinitely.
  globalTimeout: 60 * 60_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  timeout: 120_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'a11y',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'npm run dev',
      url: BASE_URL,
      reuseExistingServer: true,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});
