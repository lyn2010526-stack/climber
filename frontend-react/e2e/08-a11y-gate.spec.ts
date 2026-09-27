import { expect, test, type Page } from '@playwright/test';
import { installApiFixture, seedShellState } from './api-fixtures';
import { formatViolations, isBlocking, runAxe, type AxeViolation } from './axe';
import { ROUTES, THEMES, VIEWPORTS, navRouteIds, openRoute } from './a11y-matrix';

/**
 * The gate.
 *
 * The sweep spec produces the full report; this one decides pass or fail. A
 * failure means a real regression on a real route, because the fixture answers
 * every API call and the viewport is set per case.
 *
 * Design rules for keeping this deterministic:
 * - `retries: 0` in `playwright.a11y.config.ts`. A retry that passes after a
 *   failure is precisely the flake this suite is meant to expose.
 * - Only `serious` and `critical` fail the run. A new `minor` advisory is
 *   surfaced by the sweep instead of blocking unrelated work.
 * - The rule set is explicit, so adding an axe version cannot silently change
 *   what counts as a violation.
 */

const THEME = 'dark';
const WIDTH = 1440;

/** Failures worth blocking a merge for. */
const GATE_RULES = [
  // Names: a control nobody can address is unusable.
  'button-name',
  'link-name',
  'label',
  'select-name',
  'aria-command-name',
  'aria-required-children',
  'aria-required-parent',
  'aria-roles',
  'aria-valid-attr',
  'aria-valid-attr-value',
  'aria-allowed-attr',
  'aria-allowed-role',
  'aria-hidden-focus',
  'aria-toggle-field-name',
  'aria-tooltip-name',
  // Relationships: state that points at nothing, or a second current item.
  'aria-valid-attr-value',
  'duplicate-id-aria',
  'duplicate-id',
  // Structure and keyboard reach. `focusable-not-tabbable` and
  // `focus-order-semantics` are axe's focus rules; `aria-hidden-focus` covers a
  // hidden subtree that still holds a stop.
  'list',
  'listitem',
  'definition-list',
  'dlitem',
  'nested-interactive',
  'focus-order-semantics',
  'aria-hidden-focus',
  'scrollable-region-focusable',
  'frame-focusable-content',
  'tabindex',
  // Readability and legibility.
  'color-contrast',
  'link-in-text-block',
  'target-size',
  'meta-viewport-large',
  'object-alt',
  'image-alt',
  'input-image-alt',
  'area-alt',
  'svg-img-alt',
  // Table and form structure.
  'table-duplicate-name',
  'td-headers-attr',
  'th-has-data-cells',
  'form-field-multiple-labels',
  'autocomplete-valid',
] as const;

const dedupe = (rules: readonly string[]) => [...new Set(rules)];

test.describe('axe gate', () => {
  test('the route list is read from the nav config, not hardcoded', () => {
    // If this ever drifts, the gate silently stops covering a page.
    expect(ROUTES).toEqual(navRouteIds());
    expect(ROUTES.length).toBeGreaterThan(20);
    expect(ROUTES).toContain('settings');
    expect(ROUTES).toContain('chat');
  });

  /**
   * One gate per viewport, both themes inside each. Contrast is theme-scoped, so
   * a light-only pass leaves dark text unreadable and vice versa; the viewport
   * split keeps a 390px-only failure, like a label hidden by the mobile sheet,
   * from being invisible at 1440px.
   */
  for (const viewport of VIEWPORTS) {
    test(`no serious or critical axe violations at ${viewport.width}px, both themes`, async ({ page }) => {
      test.setTimeout(20 * 60_000);
      const findings: string[] = [];

      for (const theme of THEMES) {
        for (const route of ROUTES) {
          // An overlay, an unsettled theme or a spinner would all be scanned as
          // if they were the app, so refuse to scan them.
          const cause = await openRoute(page, route, theme, viewport.width);
          expect(cause, `#${route} [${theme}/${viewport.width}px] was not scannable`).toBeNull();

          const violations = await runAxe(page, { enableRules: dedupe(GATE_RULES) });
          for (const violation of violations.filter(isBlocking)) {
            findings.push(
              `#${route} [${theme}/${viewport.width}px] [${violation.impact}] ${violation.id} <${violation.tags.join(', ')}>\n    ${violation.nodes.map(node => node.target.join(' ')).join('\n    ')}`,
            );
          }
        }
      }

      expect(findings, `blocking accessibility violations at ${viewport.width}px:\n${findings.join('\n')}`).toHaveLength(0);
    });
  }
});

/**
 * Assertions for the specific contracts the sweep cannot see. These encode the
 * intent behind each hand fix, so the fix survives the next refactor.
 */
test.describe('a11y contracts in the rendered shell', () => {
  /**
   * Shares the sweep's readiness logic, so a contract assertion never runs
   * against a Suspense spinner and reports a defect that is a timing artefact.
   */
  async function openShell(page: Page, route: string, width = WIDTH) {
    const cause = await openRoute(page, route, THEME, width);
    expect(cause, `#${route} was not scannable: ${cause ?? ''}`).toBeNull();
  }

  test('settings has exactly one aria-current="page" and no section claims it', async ({ page }) => {
    await openShell(page, 'settings');

    // The shell navigation owns the page-level marker.
    await expect(page.locator('aside nav [aria-current="page"]')).toHaveCount(1);

    // A section of the same page is "true", never "page".
    const pageMarkers = await page.locator('[aria-current="page"]').count();
    expect(pageMarkers).toBe(1);
    await expect(page.locator('.settings-nav-item[aria-current="true"]')).toHaveCount(1);
  });

  test('a settings section is named by its label, with the hint as a description', async ({ page }) => {
    await openShell(page, 'settings');
    const section = page.locator('.settings-nav-item[aria-current="true"]');
    const labelledBy = await section.getAttribute('aria-labelledby');
    const describedBy = await section.getAttribute('aria-describedby');
    expect(labelledBy).toBeTruthy();
    expect(describedBy).toBeTruthy();

    const label = (await page.locator(`#${labelledBy}`).textContent())?.trim() ?? '';
    const hint = (await page.locator(`#${describedBy}`).textContent())?.trim() ?? '';
    expect(label).not.toBe('');
    expect(hint).not.toBe('');
    // The bug this pins: the name collapsed to "GeneralAccount Settings".
    expect(label).not.toBe(hint);
    expect(`${label}${hint}`).not.toContain(label + label);
  });

  test('the mobile sheet dismisses from the dialog and exposes a focus trap', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installApiFixture(page, { populated: true });
    await seedShellState(page, THEME);
    await page.goto('/#chat');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(600);

    const more = page.getByRole('button', { name: /更多|More/ });
    await more.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // No click handler lives on a presentation layer any more.
    expect(await page.locator('.mobile-sheet-layer[role="presentation"]').count()).toBe(0);
    await expect(page.locator('.mobile-sheet-backdrop')).toHaveAttribute('aria-hidden', 'true');

    // The sheet owns a name that resolves to a real heading.
    const labelledBy = await dialog.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();
    await expect(page.locator(`#${labelledBy}`)).toHaveJSProperty('tagName', 'H2');

    // Tab from the last stop wraps inside the dialog rather than escaping.
    const stops = dialog.locator('button');
    const count = await stops.count();
    await stops.nth(count - 1).focus();
    await page.keyboard.press('Tab');
    const stillInside = await dialog.evaluate(node => node.contains(document.activeElement));
    expect(stillInside).toBe(true);

    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
  });

  test('the theme toggle meets the 44px touch target in the collapsed rail', async ({ page }) => {
    // 768px is where the rail collapses to 64px and the footer used to clip.
    await openShell(page, 'chat', 768);

    const toggle = page.getByRole('button', { name: /模式，点击切换/ });
    const box = await toggle.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);

    // Nothing in the collapsed rail may stick out of it or scroll inside it.
    // The footer is the rail's last child; a wide control there used to be cut
    // off with no way to reach it.
    const overflow = await page.evaluate(() => {
      const rail = document.querySelector('aside');
      if (!rail) return [{ why: 'no aside in the shell' }];
      const footer = rail.lastElementChild as HTMLElement | null;
      if (!footer) return [{ why: 'the rail has no footer' }];

      const problems: unknown[] = [];
      if (footer.scrollWidth > footer.clientWidth + 1) {
        problems.push({
          why: 'the footer scrolls sideways',
          client: footer.clientWidth,
          scroll: footer.scrollWidth,
          children: Array.from(footer.children).map(child => ({
            cls: (child as HTMLElement).className,
            scroll: (child as HTMLElement).scrollWidth,
            width: Math.round(child.getBoundingClientRect().width),
            inner: Array.from(child.children).map(grand => ({
              tag: grand.tagName,
              cls: (grand as HTMLElement).className,
              scroll: (grand as HTMLElement).scrollWidth,
              width: Math.round(grand.getBoundingClientRect().width),
            })),
          })),
        });
      }
      const bounds = rail.getBoundingClientRect();
      for (const child of Array.from(footer.children)) {
        const childBox = child.getBoundingClientRect();
        if (childBox.right > bounds.right + 1 || childBox.left < bounds.left - 1) {
          problems.push({ why: 'a footer control escapes the rail', left: childBox.left, right: childBox.right, railLeft: bounds.left, railRight: bounds.right });
        }
      }
      return problems;
    });
    expect(overflow).toEqual([]);
  });

  test('every icon-only control on the settings page resolves to a name', async ({ page }) => {
    await openShell(page, 'settings');
    // Scoped to the settings page so a failure points at the page under test.
    // `.settings-layout` only exists on settings, so its absence means the
    // contract never got a chance to run.
    const violations: AxeViolation[] = await runAxe(page, {
      include: ['.settings-layout'],
      enableRules: ['button-name', 'link-name', 'select-name', 'label', 'aria-command-name'],
    });
    expect(formatViolations(violations)).toEqual([]);
  });

  test('the reasoning parameter row names each select', async ({ page }) => {
    await openShell(page, 'reasoning');
    const violations = await runAxe(page, {
      include: ['#main-content'],
      enableRules: ['select-name', 'label'],
    });
    expect(formatViolations(violations)).toEqual([]);
  });
});

export { THEME, WIDTH };
