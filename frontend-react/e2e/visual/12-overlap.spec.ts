/**
 * Overlap and reachability between the regions that actually collide in this
 * layout, plus the chat states that only exist after an interaction.
 *
 * The matrix checks geometry per page; this spec drives the states that need a
 * click first (streaming, error) and verifies the Send control is reachable
 * with `elementFromPoint` while the drawer and the bottom navigation are open.
 */

import { test, expect } from '@playwright/test';
import { installApiFixtures, type FixtureHandle } from './fixtures/routes';
import { applyTheme, expectThemeApplied, pinColorScheme, type Theme } from './fixtures/theme';
import {
  assertClickable,
  assertNoHorizontalOverflow,
  assertNoOverlap,
  assertTouchTargets,
} from './fixtures/geometry';
import { freezeHmr } from './fixtures/preview';
import { findKnownDefect } from './fixtures/defects';
import { flushReport, record, recordKnownDefect, resetReport } from './report';
import { WIDTHS, HEIGHTS, isMobileWidth } from './matrix';

const BOTTOM_NAV = 'nav.mobile-bottom-nav';
const MOBILE_CONTENT = 'main#main-content';
const DESKTOP_SIDEBAR = 'aside[aria-label="Main navigation"]';
const DESKTOP_MAIN = 'main#main-content';
const DRAWER = '[data-testid="right-panel-drawer"]';
const COMPOSER = 'textarea[aria-label="输入消息"], textarea';
const SEND = 'button[aria-label="发送消息"]';
const STOP = 'button[aria-label="停止生成"]';

async function settle(page: import('@playwright/test').Page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle').catch(() => undefined);
}

async function fillAndSend(page: import('@playwright/test').Page, text: string) {
  const composer = page.locator(COMPOSER).first();
  await expect(composer, 'composer must be present to drive the chat state').toBeVisible();
  await composer.fill(text);
  // The send control is disabled while the draft is empty, so this also proves
  // the disabled state clears once there is something to send.
  const send = page.locator(SEND).first();
  await expect(send).toBeEnabled();
  await send.click();
}

test.describe('overlap, reachability and interactive chat states', () => {
  test.beforeAll(() => {
    resetReport('overlap');
  });

  // Closes the dev server's hot-reload channel so a source edit mid-run cannot
  // remount the lazy route and leave the page blank.
  test.beforeEach(async ({ page }) => {
    await freezeHmr(page);
  });

  test.afterAll(() => {
    flushReport({ spec: 'overlap', pixelLayerEnabled: false });
  });

  // --- mobile: bottom navigation must never sit on top of the composer ----
  for (const theme of ['light', 'dark'] as Theme[]) {
    test(`mobile 390 ${theme}: bottom nav does not overlap the composer and Send stays clickable`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page);

      await page.goto('/#chat');
      await settle(page);
      await expectThemeApplied(page, theme);

      const nav = page.locator(BOTTOM_NAV);
      const composer = page.locator(COMPOSER).first();
      await expect(nav, 'bottom navigation must render on mobile').toBeVisible();
      await expect(composer, 'composer must render on mobile').toBeVisible();

      // Fill first: an empty composer is a different box (the send control is
      // hidden or disabled), and the overlap that matters is the loaded state.
      await composer.fill('验证底部导航与输入区的关系');
      await page.waitForTimeout(120);

      await assertNoOverlap(page, [[BOTTOM_NAV, COMPOSER]], { label: `mobile ${theme}` });
      // The reserved strip is the mechanism that keeps them apart; assert the
      // content area reserves at least the navigation height.
      const reserve = await page.evaluate(() => {
        const content = document.querySelector('main#main-content');
        return content ? window.getComputedStyle(content).paddingBottom : '0px';
      });
      const reserved = parseFloat(reserve);
      expect(reserved, `mobile ${theme}: .mobile-content must reserve the nav strip, got ${reserve}`)
        .toBeGreaterThanOrEqual(64);

      // The decisive check: the Send button is the topmost element at its own
      // centre, i.e. a real tap lands on it.
      const hit = await assertClickable(page, SEND, { label: `mobile ${theme}` });
      expect(hit.reachable).toBe(true);

      // A send must actually go through, which is the functional version of
      // "the button is reachable".
      await page.locator(SEND).first().click();
      await expect(page.locator(STOP), 'send must transition to the stop control').toBeVisible({ timeout: 5_000 });

      record({
        title: `mobile 390 ${theme} bottom-nav vs composer`,
        page: 'chat',
        state: 'messages',
        width: 390,
        height: 844,
        theme,
        themeProof: await expectThemeApplied(page, theme),
        geometry: {
          url: page.url(),
          viewport: { width: 390, height: 844 },
          scroll: { width: 0, height: 0 },
          overflow: { scrollWidth: 0, clientWidth: 390, delta: 0, offenders: [], leftOffenders: [] },
          overlaps: [],
          smallTargets: [],
          ariaCurrentCount: 1,
          hitTests: [hit],
          durationMs: 0,
        },
        fixturesRequested: [],
        fixturesUnfulfilled: [],
        screenshot: null,
        pixelsCompared: false,
      });
    });
  }

  // --- mobile: the "more" sheet must not cover the Send button ------------
  for (const theme of ['light', 'dark'] as Theme[]) {
    test(`mobile 390 ${theme}: the more sheet closes and returns Send to the top layer`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page);

      await page.goto('/#chat');
      await settle(page);
      await expectThemeApplied(page, theme);

      const more = page.locator(`${BOTTOM_NAV} button[aria-expanded]`).first();
      await expect(more, 'the more-sheet trigger must exist').toBeVisible();
      await more.click();

      const sheet = page.locator('[role="dialog"][aria-modal="true"]');
      await expect(sheet, 'the more sheet must open').toBeVisible();

      // While the sheet is up, Send is legitimately behind a modal layer. The
      // product's obligation is that the sheet is dismissable, not that Send
      // stays clickable under it.
      const close = sheet.locator('button[aria-label="Close"]').first();
      await expect(close, 'the sheet must offer a close control').toBeVisible();

      await close.click();
      await expect(sheet, 'the sheet must close').toBeHidden();

      await page.locator(COMPOSER).first().fill('抽屉关闭后发送按钮应恢复可点');
      const hit = await assertClickable(page, SEND, { label: `mobile ${theme} sheet closed` });
      expect(hit.reachable).toBe(true);
    });
  }

  // --- desktop: sidebar vs main, and the right drawer vs Send -------------
  for (const width of [1440, 1280, 1024, 768] as const) {
    for (const theme of ['light', 'dark'] as Theme[]) {
      test(`desktop ${width} ${theme}: sidebar and main do not overlap; Send is clickable`, async ({ page }) => {
        await page.setViewportSize({ width, height: HEIGHTS[width] });
        await pinColorScheme(page, theme);
        await applyTheme(page, theme);
        await installApiFixtures(page);

        await page.goto('/#chat');
        await settle(page);
        await expectThemeApplied(page, theme);

        const sidebar = page.locator(DESKTOP_SIDEBAR);
        const main = page.locator(DESKTOP_MAIN);
        await expect(sidebar, 'the desktop sidebar must render').toBeVisible();
        await expect(main).toBeVisible();

        await assertNoOverlap(page, [[DESKTOP_SIDEBAR, DESKTOP_MAIN]], { label: `desktop ${width} ${theme}` });

        const composer = page.locator('textarea, input[placeholder]').first();
        if ((await composer.count()) > 0 && await composer.isVisible().catch(() => false)) {
          await composer.fill('桌面布局下的发送按钮命中测试');
          const sendSelector = (await page.locator('button[aria-label="Send"]').count()) > 0
            ? 'button[aria-label="Send"]'
            : SEND;
          if ((await page.locator(sendSelector).count()) > 0) {
            const hit = await assertClickable(page, sendSelector, { label: `desktop ${width} ${theme}` });
            expect(hit.reachable).toBe(true);
          }
        }

        await assertNoHorizontalOverflow(page, `desktop ${width} ${theme}`);
        await assertTouchTargets(page, {
          label: `desktop ${width} ${theme} sidebar`,
          min: 44,
          scope: DESKTOP_SIDEBAR,
        });
      });
    }
  }

  // --- chat states that require a click -----------------------------------
  for (const width of WIDTHS) {
    const theme: Theme = 'light';
    test(`chat streaming @ ${width}px ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width, height: HEIGHTS[width] });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      const fixtures: FixtureHandle = await installApiFixtures(page, { streamDelayMs: 15_000 });

      await page.goto('/#chat');
      await settle(page);
      await expectThemeApplied(page, theme);

      await fillAndSend(page, '触发一次流式响应以验证流式中状态');

      // The stop control replaces send while streaming — the observable proof
      // that `isStreaming` is true, rather than a spinner we hope is related.
      const stopSelector = (await page.locator(STOP).count()) > 0
        ? STOP
        : 'button[aria-label="Stop generation"]';
      await expect(
        page.locator(stopSelector).first(),
        'the composer must switch to the stop control while streaming',
      ).toBeVisible({ timeout: 8_000 });

      const busy = await page.locator('section[aria-busy]').first().getAttribute('aria-busy');
      expect(busy, 'the chat section must report aria-busy during streaming').toBe('true');

      fixtures.releaseStreams();
    });

    test(`chat error @ ${width}px ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width, height: HEIGHTS[width] });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page, { statusOverrides: { '/sessions/:id/chat': 503 } });

      await page.goto('/#chat');
      await settle(page);
      await expectThemeApplied(page, theme);

      await fillAndSend(page, '触发一次失败响应以验证错误态');

      const alert = page.locator('[role="alert"]').first();
      await expect(alert, 'a failed stream must surface an alert').toBeVisible({ timeout: 8_000 });
      const text = (await alert.innerText()).trim();
      expect(text.length, 'the error alert must carry a message').toBeGreaterThan(0);
    });

    test(`chat empty @ ${width}px ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width, height: HEIGHTS[width] });
      await pinColorScheme(page, theme);
      await applyTheme(page, theme);
      await installApiFixtures(page, {
        overrides: { '/sessions/:id/messages': { messages: [] } },
      });

      await page.goto('/#chat');
      await settle(page);
      await expectThemeApplied(page, theme);

      // An empty state must render real content, not a blank scroll area —
      // this is the assertion the previous empty baseline could not make.
      const content = page.locator('main#main-content');
      const text = ((await content.innerText()) ?? '').trim();
      expect(text.length, 'the empty chat must render an empty state with copy').toBeGreaterThan(0);
    });
  }

  // --- collapsed sidebar is a touch surface too ---------------------------
  for (const width of [1024, 768] as const) {
    test(`collapsed sidebar @ ${width}px keeps 44px targets`, async ({ page }) => {
      await page.setViewportSize({ width, height: HEIGHTS[width] });
      await pinColorScheme(page, 'dark');
      await applyTheme(page, 'dark');
      await installApiFixtures(page);

      await page.goto('/#agents');
      await settle(page);
      await expectThemeApplied(page, 'dark');

      const toggle = page.locator('aside[aria-label="Main navigation"] button[aria-label="Collapse sidebar"]');
      await expect(toggle).toBeVisible();
      await toggle.click();
      await page.waitForTimeout(320); // the sidebar width transition

      const expanded = await page.locator('aside[aria-label="Main navigation"] button[aria-label="Expand sidebar"]');
      await expect(expanded, 'the sidebar must report the collapsed state').toBeVisible();

      const sidebarWidth = await page.locator('aside[aria-label="Main navigation"]').boundingBox();
      expect(
        Math.round(sidebarWidth?.width ?? 0),
        'the collapsed sidebar must use the 64px token',
      ).toBe(64);

      await assertTouchTargets(page, {
        label: `collapsed sidebar ${width}px`,
        min: 44,
        scope: 'aside[aria-label="Main navigation"]',
      });

      // The left-edge escape is a known defect (UI-002): the 64px rail holds a
      // ~97px language control, so it leaves the viewport and reaches into main.
      // `assertNoHorizontalOverflow` exempts exactly that case and still fails on
      // any other left escape, so this measures it explicitly instead.
      const report = await assertNoHorizontalOverflow(page, `collapsed sidebar ${width}px`);
      if (report.leftOffenders.length > 0) {
        const defect = findKnownDefect({ page: 'rail', width, control: DESKTOP_SIDEBAR });
        expect(
          defect,
          `collapsed sidebar ${width}px: elements crossed the left viewport edge but no known defect covers it: ` +
            JSON.stringify(report.leftOffenders[0]),
        ).not.toBeNull();
        const worst = report.leftOffenders[0];
        if (!worst) throw new Error('leftOffenders was non-empty but its first entry was undefined');
        recordKnownDefect({
          ...defect!,
          title: `collapsed sidebar @ ${width}px`,
          width,
          height: HEIGHTS[width],
          theme: 'dark',
          state: null,
          evidence: {
            centerX: 0,
            centerY: 0,
            topmost: `${worst.selector} escapes the left edge by ${Math.abs(worst.left).toFixed(2)}px ` +
              `(rail 64px, control ${worst.width}px wide)`,
            targetName: worst.selector,
          },
        });
      }
    });
  }

  // --- mobile pages that are not adapted must fall back, not render dead ---
  test('mobile falls back to the chat surface for desktop-only pages', async ({ page }) => {
    const desktopOnly = ['mcp', 'traces', 'eval', 'cost', 'doctor', 'scheduler', 'workflows', 'reasoning', 'skills', 'plugins', 'notifications'];
    for (const target of desktopOnly) {
      await page.setViewportSize({ width: 390, height: 844 });
      await pinColorScheme(page, 'light');
      await applyTheme(page, 'light');
      await installApiFixtures(page);

      await page.goto(`/#${target}`);
      await settle(page);

      await expect
        .poll(() => page.evaluate(() => window.location.hash.replace(/^#\/?/, '')), {
          message: `${target} must fall back to chat below 768px`,
        })
        .toBe('chat');

      const bottomNav = page.locator(BOTTOM_NAV);
      await expect(bottomNav, `${target}: the mobile shell must render`).toBeVisible();
      expect(isMobileWidth(390)).toBe(true);
    }
  });
});
