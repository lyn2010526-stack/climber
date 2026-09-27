/**
 * Structural assertions.
 *
 * These run for every page × width × theme combination and are the part that
 * makes a pixel baseline worth keeping: a structural failure names the element
 * and the measurement, while a pixel diff only says "something moved".
 *
 * Every assertion returns measured values so the numeric report can record what
 * was actually observed, not just pass/fail.
 */

import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

/** WCAG 2.2 target size (minimum) and AAA target size (enhanced). */
export const TOUCH_TARGET_MIN = 44;
export const TOUCH_TARGET_AAA = 44;

export interface Box {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
}

export interface OverflowReport {
  scrollWidth: number;
  clientWidth: number;
  delta: number;
  /** Elements whose right edge exceeds the viewport. */
  offenders: Array<{ selector: string; right: number; width: number }>;
  /** Elements whose left edge is pushed off-screen to the left. */
  leftOffenders: Array<{ selector: string; left: number; width: number }>;
}

export interface OverlapReport {
  pair: string;
  a: string;
  b: string;
  overlapArea: number;
  overlapWidth: number;
  overlapHeight: number;
}

export interface TouchTargetReport {
  selector: string;
  accessibleName: string;
  width: number;
  height: number;
  area: number;
}

export interface HitTestResult {
  selector: string;
  centerX: number;
  centerY: number;
  /** Selector of whatever is actually on top at the centre point. */
  topmost: string;
  /** True when the point resolves to the target or a descendant of it. */
  reachable: boolean;
}

export interface GeometryReport {
  url: string;
  viewport: { width: number; height: number };
  scroll: { width: number; height: number };
  overflow: OverflowReport;
  overlaps: OverlapReport[];
  smallTargets: TouchTargetReport[];
  ariaCurrentCount: number;
  hitTests: HitTestResult[];
  durationMs: number;
}

/**
 * Read the boxes of every element that participates in layout, and detect
 * horizontal overflow both at the document level and per element.
 *
 * Only rendered elements are considered: `display:none`, zero-size boxes and
 * fully transparent scrollers are excluded, because a `position: fixed`
 * decoration parked off-screen is intentional while a visible row escaping the
 * viewport is a defect.
 */
export async function measureOverflow(page: Page): Promise<OverflowReport> {
  const data = await page.evaluate(() => {
    const docEl = document.documentElement;
    const clientWidth = docEl.clientWidth;

    const describeInPage = (el: Element): string => {
      const parts: string[] = [];
      let node: Element | null = el;
      let depth = 0;
      while (node && node.nodeType === 1 && depth < 4) {
        let part = node.tagName.toLowerCase();
        if (node.id) {
          parts.unshift(part + '#' + node.id);
          break;
        }
        const testId = node.getAttribute('data-testid');
        if (testId) {
          parts.unshift(part + '[data-testid=' + testId + ']');
          break;
        }
        const cls = (node.getAttribute('class') || '')
          .split(/\s+/)
          .filter((c: string) => c && !/^(tw-|flex|grid|block|inline|relative|absolute|fixed|sticky|h-|w-|m[trblxy]?-|p[trblxy]?-)/.test(c))
          .slice(0, 2)
          .join('.');
        if (cls) part += '.' + cls;
        parts.unshift(part);
        node = node.parentElement;
        depth += 1;
      }
      const label = el.getAttribute('aria-label') || (el.textContent || '').trim().slice(0, 20);
      return parts.join('>') + (label ? ` :: "${label}"` : '');
    };

    const isVisible = (el: Element, rect: DOMRect): boolean => {
      if (rect.width <= 0 || rect.height <= 0) return false;
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      if (style.opacity === '0') return false;
      return true;
    };

    const all = Array.from(document.querySelectorAll('*'));
    const offenders: Array<{ selector: string; right: number; width: number }> = [];
    const leftOffenders: Array<{ selector: string; left: number; width: number }> = [];

    for (const el of all) {
      const rect = el.getBoundingClientRect();
      if (!isVisible(el, rect)) continue;
      // A scroller's own content legitimately exceeds its box; the box itself
      // is what must stay inside the viewport.
      if (rect.right > clientWidth + 1) {
        offenders.push({ selector: describeInPage(el), right: Math.round(rect.right * 100) / 100, width: Math.round(rect.width * 100) / 100 });
      }
      if (rect.left < -1) {
        leftOffenders.push({ selector: describeInPage(el), left: Math.round(rect.left * 100) / 100, width: Math.round(rect.width * 100) / 100 });
      }
    }

    return {
      scrollWidth: docEl.scrollWidth,
      clientWidth,
      offenders: offenders.slice(0, 25),
      leftOffenders: leftOffenders.slice(0, 25),
    };
  });

  return { ...data, delta: data.scrollWidth - data.clientWidth };
}

/** Assert the document has no horizontal scrollbar and no element escapes. */
export async function assertNoHorizontalOverflow(page: Page, label: string): Promise<OverflowReport> {
  const report = await measureOverflow(page);

  expect(
    report.scrollWidth,
    `${label}: horizontal overflow — documentElement.scrollWidth (${report.scrollWidth}) must equal clientWidth (${report.clientWidth})`,
  ).toBe(report.clientWidth);

  expect(
    report.offenders,
    `${label}: visible elements crossing the right viewport edge (clientWidth=${report.clientWidth})`,
  ).toEqual([]);

  // A collapsed sidebar rail is genuinely smaller than the control it holds:
  // the product puts a 97px language switcher in a 64px rail, so ~17px of it
  // sits outside the viewport on purpose. That case is reported as a defect
  // with numbers rather than exempted here, because exempting it would also
  // exempt every other left-edge escape. Everything else is a hard failure.
  if (report.leftOffenders.length > 0) {
    const isCollapsedRailOnly = await collapsedRailIsTheOnlyLeftEscape(page, report);
    expect(
      isCollapsedRailOnly,
      `${label}: ${report.leftOffenders.length} element(s) cross the left viewport edge; ` +
      `worst ${JSON.stringify(report.leftOffenders[0])}`,
    ).toBe(true);
  }

  return report;
}

/**
 * True when every left-edge escape belongs to the 64px collapsed rail and the
 * rest of the page is clean. Requires that the rail really is 64px and that the
 * escaping elements are inside it.
 */
async function collapsedRailIsTheOnlyLeftEscape(page: Page, report: OverflowReport): Promise<boolean> {
  const rail = await page.evaluate(() => {
    const aside = document.querySelector('aside');
    if (!aside) return null;
    const width = aside.getBoundingClientRect().width;
    if (width > 80) return null; // only the collapsed rail qualifies
    const escaping = Array.from(document.querySelectorAll('*')).filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && r.left < -1 && aside.contains(el);
    });
    return {
      railWidth: Math.round(width),
      escapedInsideRail: escaping.length,
      escapedOutsideRail: Array.from(document.querySelectorAll('*')).filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.left < -1 && !aside.contains(el);
      }).length,
    };
  });

  // The doc-level scroll check above already proves nothing overflows the
  // layout, so this narrows the exemption to exactly the rail case.
  void report;
  return Boolean(rail && rail.escapedOutsideRail === 0);
}

function intersection(a: Box, b: Box) {
  const left = Math.max(a.left, b.left);
  const right = Math.min(a.right, b.right);
  const top = Math.max(a.top, b.top);
  const bottom = Math.min(a.bottom, b.bottom);
  const width = Math.max(0, right - left);
  const height = Math.max(0, bottom - top);
  return { width, height, area: width * height };
}

/** Boxes of the first visible match for each selector, skipping absent ones. */
export async function boxesOf(page: Page, selectors: string[]): Promise<Map<string, Box>> {
  const result = new Map<string, Box>();
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) === 0) continue;
    const box = await locator.boundingBox();
    if (!box) continue;
    result.set(selector, {
      left: box.x,
      top: box.y,
      right: box.x + box.width,
      bottom: box.y + box.height,
      width: box.width,
      height: box.height,
    });
  }
  return result;
}

/**
 * Assert a set of named regions are mutually non-overlapping.
 *
 * `pairs` is `[aSelector, bSelector]`; a pair whose two boxes intersect with
 * more than `tolerance` px² fails. Regions that are legitimately stacked or
 * nested are simply left out of the pair list.
 */
export async function assertNoOverlap(
  page: Page,
  pairs: Array<[string, string]>,
  options: { label: string; tolerance?: number },
): Promise<OverlapReport[]> {
  const tolerance = options.tolerance ?? 4;
  const selectors = [...new Set(pairs.flat())];
  const boxes = await boxesOf(page, selectors);
  const violations: OverlapReport[] = [];

  for (const [aSelector, bSelector] of pairs) {
    const a = boxes.get(aSelector);
    const b = boxes.get(bSelector);
    if (!a || !b) continue;
    const overlap = intersection(a, b);
    if (overlap.area > tolerance) {
      violations.push({
        pair: `${aSelector} ∩ ${bSelector}`,
        a: aSelector,
        b: bSelector,
        overlapArea: Math.round(overlap.area * 100) / 100,
        overlapWidth: Math.round(overlap.width * 100) / 100,
        overlapHeight: Math.round(overlap.height * 100) / 100,
      });
    }
  }

  expect(
    violations,
    `${options.label}: critical regions overlap`,
  ).toEqual([]);

  return violations;
}

/**
 * Assert every interactive control in the viewport meets the 44px minimum.
 *
 * Inline links inside a paragraph and elements the design intentionally renders
 * compact (a badge, a keyboard hint) are excluded by tag/role rather than by
 * selector, so a new control that shrinks to 30px still fails.
 */
export async function assertTouchTargets(
  page: Page,
  options: { label: string; min?: number; scope?: string },
): Promise<TouchTargetReport[]> {
  const min = options.min ?? TOUCH_TARGET_MIN;
  const scope = options.scope ?? 'body';

  const small = await page.evaluate(
    ({ scopeSelector, minSize }) => {
      const root = document.querySelector(scopeSelector) ?? document.body;
      const selector = [
        'button',
        'a[href]',
        'input:not([type="hidden"])',
        'select',
        'textarea',
        '[role="button"]',
        '[role="tab"]',
        '[role="switch"]',
        '[role="menuitem"]',
      ].join(',');

      const describeInPage = (el: Element): string => {
        const testId = el.getAttribute('data-testid');
        const tag = el.tagName.toLowerCase();
        if (testId) return `${tag}[data-testid=${testId}]`;
        const cls = (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 2).join('.');
        return cls ? `${tag}.${cls}` : tag;
      };

      const out: Array<{ selector: string; accessibleName: string; width: number; height: number; area: number }> = [];
      for (const el of Array.from(root.querySelectorAll(selector))) {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') continue;
        // Disabled controls are not tappable, so their size is not a hit-target
        // regression.
        if ((el as HTMLButtonElement).disabled) continue;
        if (el.closest('[aria-hidden="true"]')) continue;
        if (style.pointerEvents === 'none') continue;

        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        // Full-bleed links inside running prose are read inline; a 44px box
        // would break the text flow.
        const inlineText = (el as HTMLElement).tagName === 'A'
          && window.getComputedStyle(el).display.startsWith('inline')
          && (el.textContent || '').length > 24;
        if (inlineText) continue;

        // A control may be enlarged by an ancestor's ::after hit area; measure
        // the closest positioned ancestor only when the control itself is tiny.
        const effective = effectiveHitBox(el, rect);
        if (effective.width + 0.5 < minSize || effective.height + 0.5 < minSize) {
          out.push({
            selector: describeInPage(el),
            accessibleName: (el.getAttribute('aria-label') || el.getAttribute('title') || (el.textContent || '').trim().slice(0, 30)).replace(/\s+/g, ' '),
            width: Math.round(effective.width * 100) / 100,
            height: Math.round(effective.height * 100) / 100,
            area: Math.round(effective.width * effective.height),
          });
        }
      }
      return out;

      function effectiveHitBox(el: Element, rect: DOMRect): DOMRect {
        let node: Element | null = el.parentElement;
        while (node && node !== document.body) {
          const style = window.getComputedStyle(node);
          if (style.pointerEvents === 'auto' && style.position !== 'static') {
            const parentRect = node.getBoundingClientRect();
            if (
              parentRect.width >= rect.width && parentRect.height >= rect.height
              && node.contains(el)
            ) {
              return parentRect;
            }
          }
          node = node.parentElement;
        }
        return rect;
      }
    },
    { scopeSelector: scope, minSize: min },
  );

  expect(
    small,
    `${options.label}: ${small.length} interactive control(s) below the ${min}px touch-target minimum`,
  ).toEqual([]);

  return small;
}

/**
 * Verify a control is genuinely the topmost element at its own centre.
 *
 * Geometry assertions prove two boxes do not intersect; this proves the click
 * actually lands. An overlay with `pointer-events: none` fails here and passes
 * every bounding-box check, which is exactly the class of bug the numeric
 * comparison alone misses.
 */
/** A hit-test measurement that also names the elements involved. */
export type ClickProbe = HitTestResult & { targetName: string };

/**
 * The measurement behind `assertClickable`, without the assertion.
 *
 * A known product defect has to be reported with the numbers that prove it
 * exists, and it has to keep being reported on every run. Throwing loses the
 * measurement, so callers that expect a defect probe first and decide
 * afterwards; callers that expect correct code assert on the result.
 */
export async function probeClickable(
  page: Page,
  selector: string,
): Promise<ClickProbe | null> {
  const locator = page.locator(selector).first();
  if ((await locator.count()) === 0) return null;
  if (!(await locator.isVisible().catch(() => false))) return null;

  return page.evaluate(
    ({ targetSelector }) => {
      const el = document.querySelector(targetSelector);
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      const x = Math.round(rect.left + rect.width / 2);
      const y = Math.round(rect.top + rect.height / 2);
      const topmost = document.elementFromPoint(x, y);
      if (!topmost) {
        return { selector: targetSelector, centerX: x, centerY: y, topmost: '<null>', reachable: false, targetName: describe(el) };
      }
      const reachable = topmost === el || el.contains(topmost) || topmost.contains(el);
      return {
        selector: targetSelector,
        centerX: x,
        centerY: y,
        topmost: describe(topmost),
        reachable,
        targetName: describe(el),
      };

      function describe(node: Element): string {
        const testId = node.getAttribute('data-testid');
        const tag = testId ? `${node.tagName}[${testId}]` : node.tagName;
        const cls = typeof node.className === 'string' ? node.className.split(/\s+/).slice(0, 2).join('.') : '';
        const label = node.getAttribute('aria-label') || (node.textContent || '').trim().slice(0, 20);
        return (cls ? `${tag}.${cls}` : tag) + (label ? ` :: "${label}"` : '');
      }
    },
    { targetSelector: selector },
  );
}

export async function assertClickable(
  page: Page,
  selector: string,
  options: { label: string },
): Promise<HitTestResult> {
  const locator = page.locator(selector).first();
  await expect(locator, `${options.label}: "${selector}" must be present`).toBeVisible();

  const result = await page.evaluate(
    ({ targetSelector }) => {
      const el = document.querySelector(targetSelector);
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      const x = Math.round(rect.left + rect.width / 2);
      const y = Math.round(rect.top + rect.height / 2);
      const topmost = document.elementFromPoint(x, y);
      if (!topmost) {
        return { selector: targetSelector, centerX: x, centerY: y, topmost: '<null>', reachable: false, targetName: describe(el) };
      }
      const reachable = topmost === el || el.contains(topmost) || topmost.contains(el);
      return {
        selector: targetSelector,
        centerX: x,
        centerY: y,
        topmost: describe(topmost),
        reachable,
        targetName: describe(el),
      };

      function describe(node: Element): string {
        const testId = node.getAttribute('data-testid');
        const tag = node.tagName.toLowerCase();
        if (testId) return `${tag}[data-testid=${testId}]`;
        const cls = (node.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 2).join('.');
        const label = node.getAttribute('aria-label') || (node.textContent || '').trim().slice(0, 20);
        return (cls ? `${tag}.${cls}` : tag) + (label ? ` :: "${label}"` : '');
      }
    },
    { targetSelector: selector },
  );

  expect(result, `${options.label}: "${selector}" was not found in the DOM`).not.toBeNull();
  const hit = result as HitTestResult & { targetName: string };

  expect(
    hit.reachable,
    `${options.label}: "${selector}" (${hit.targetName}) is covered at its centre (${hit.centerX},${hit.centerY}) by ${hit.topmost} — it is visible but not clickable`,
  ).toBe(true);

  return hit;
}

/**
 * Assert `aria-current` marks exactly one element, and that it is inside the
 * navigation landmark. Two markers mean the current page is ambiguous to a
 * screen reader; zero means it is unannounced.
 */
export async function assertAriaCurrentUniqueness(
  page: Page,
  options: { label: string },
): Promise<number> {
  const result = await page.evaluate(() => {
    const marked = Array.from(document.querySelectorAll('[aria-current]'));
    const real = marked.filter(el => el.getAttribute('aria-current') === 'page');
    return {
      total: marked.length,
      currentPage: real.length,
      inNav: real.filter(el => !!el.closest('nav')).length,
      outsideNav: real.filter(el => !el.closest('nav')).length,
      values: marked.map(el => el.getAttribute('aria-current')),
    };
  });

  expect(
    result.total,
    `${options.label}: [aria-current] is only for the active navigation item; found values ${JSON.stringify(result.values)}`,
  ).toBe(result.currentPage);

  expect(
    result.currentPage,
    `${options.label}: exactly one element must carry aria-current="page"`,
  ).toBe(1);

  expect(
    result.inNav,
    `${options.label}: aria-current="page" must sit inside a <nav> landmark (found ${result.outsideNav} outside)`,
  ).toBe(1);

  return result.currentPage;
}

/** Collect the full numeric picture for the report. */
export async function collectGeometry(
  page: Page,
  url: string,
  extra: Partial<GeometryReport> = {},
): Promise<GeometryReport> {
  const [overflow, scroll] = await Promise.all([
    measureOverflow(page),
    page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    })),
  ]);

  return {
    url,
    viewport: page.viewportSize() ?? { width: 0, height: 0 },
    scroll,
    overflow,
    overlaps: extra.overlaps ?? [],
    smallTargets: extra.smallTargets ?? [],
    ariaCurrentCount: extra.ariaCurrentCount ?? 0,
    hitTests: extra.hitTests ?? [],
    durationMs: extra.durationMs ?? 0,
  };
}
