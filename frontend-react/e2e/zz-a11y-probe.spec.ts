import { expect, test } from '@playwright/test';
import { ROUTES, THEMES, VIEWPORTS, describeUnscannable, openRoute } from './a11y-matrix';

test('probe', async ({ page }) => {
  test.setTimeout(15 * 60_000);
  const bad: string[] = [];
  for (const theme of THEMES) {
    for (const viewport of VIEWPORTS) {
      for (const route of ROUTES) {
        const cause = await openRoute(page, route, theme, viewport.width);
        if (cause) bad.push(`#${route} [${theme}/${viewport.width}px]: ${describeUnscannable(cause)}`);
      }
    }
  }
  console.log('PROBE_UNSCANNABLE_COUNT', bad.length);
  console.log(bad.join('\n'));
  expect(bad).toEqual([]);
});
