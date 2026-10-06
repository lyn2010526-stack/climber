/**
 * Scenario D — scroll stability across a long conversation and a live stream.
 *
 * The contract the chat surface implies:
 *
 * - A jump to the bottom lands exactly at the bottom, not near it.
 * - During a stream the view follows new output when the user is already at
 *   the bottom, and leaves the user's viewport alone when they scrolled away.
 *   The app gates this on a 48px threshold (`AnchoredChatColumn` onScroll
 *   handler), so both halves are measured.
 *
 * Why `scrollTop` and not distance-from-bottom is the stability signal: while a
 * stream appends content below the viewport, the distance from the bottom grows
 * legitimately even when nothing moves. The viewport moves only if `scrollTop`
 * changes. Both series are recorded so the distinction is checkable rather than
 * assumed.
 */
import type { Page } from '@playwright/test';
import type { FixtureServer } from '../lib/fixtureServer.ts';
import { buildMessagesPayload } from '../lib/fixtures.ts';
import { gotoApp, markPhase, resetProbe, settle } from '../lib/probe.ts';

export interface FrameSample {
  /** Distance from the bottom, px. */
  distance: number;
  /** Viewport offset from the top of the content, px. */
  scrollTop: number;
  /** Total content height, px. */
  scrollHeight: number;
}

export interface ScrollStabilitySample {
  historySize: number;

  jumpToBottomOffsets: number[];
  /** True when every jump landed within 2px of the bottom. */
  jumpToBottomExact: boolean;
  roundTripOffsetAfterReturn: number | null;

  /** Stream while parked at the bottom: the view should track the bottom. */
  followFrames: FrameSample[];
  followMaxDistanceFromBottom: number | null;
  followStayedAtBottom: boolean;
  followStreamCommits: number;

  /** Stream while scrolled away: the viewport should not move. */
  holdFrames: FrameSample[];
  /** Largest viewport movement, px. This is the jump metric. */
  holdMaxViewportShiftPx: number | null;
  holdStayedPut: boolean;
  holdStreamCommits: number;

  raw: {
    followFrames: FrameSample[];
    holdFrames: FrameSample[];
    apiRequests: Array<{ method: string; path: string }>;
  };
}

export interface ScrollStabilityOptions {
  historySize: number;
  chunks?: number;
  delayMs?: number;
  viewport?: { width: number; height: number };
  seed?: number;
  timeoutMs?: number;
}

export async function runScrollStabilityScenario(
  page: Page,
  server: FixtureServer,
  options: ScrollStabilityOptions,
): Promise<ScrollStabilitySample> {
  const {
    historySize,
    chunks = 40,
    delayMs = 50,
    viewport = { width: 1440, height: 900 },
    seed = 20260926,
    timeoutMs = 180_000,
  } = options;

  await page.setViewportSize(viewport);

  // Pre-seed the AppLockGate skip marker: the first-run enrollment overlay
  // (added 2026-10-05) covers the viewport and blocks the composer otherwise.
  await page.addInitScript(() => {
    try { window.localStorage.setItem('climber.privacy.skipped', '1'); } catch { /* storage may be unavailable */ }
  });

  server.state.messagesPayload = buildMessagesPayload(historySize, seed);
  server.state.messageCount = historySize;
  server.requestLog.length = 0;

  await gotoApp(page, server.baseUrl);
  await page.waitForFunction(
    (count) => {
      const transcript = document.querySelector('[data-transcript]');
      return !!transcript && transcript.children.length >= count;
    },
    historySize,
    { timeout: 240_000 },
  );
  await settle(page);

  // --- static jumps ---------------------------------------------------------
  const jumpToBottomOffsets = await page.evaluate((rounds) => {
    const el = (function find() {
      const candidates = Array.from(document.querySelectorAll('div'))
        .filter((n) => n.scrollHeight > n.clientHeight + 40);
      return candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
    })();
    if (!el) return [];
    const offsets: number[] = [];
    for (let i = 0; i < rounds; i += 1) {
      // Move away first, so each jump is a real transition rather than a no-op.
      el.scrollTop = Math.max(0, el.scrollTop - 1500);
      el.getBoundingClientRect();
      el.scrollTop = el.scrollHeight;
      el.getBoundingClientRect();
      offsets.push(Math.round(el.scrollHeight - el.scrollTop - el.clientHeight));
    }
    return offsets;
  }, 5);

  const roundTripOffsetAfterReturn = await page.evaluate(() => {
    const el = (function find() {
      const candidates = Array.from(document.querySelectorAll('div'))
        .filter((n) => n.scrollHeight > n.clientHeight + 40);
      return candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
    })();
    if (!el) return null;
    el.scrollTop = Math.max(0, el.scrollTop - 1000);
    el.getBoundingClientRect();
    el.scrollTop = el.scrollHeight;
    el.getBoundingClientRect();
    return Math.round(el.scrollHeight - el.scrollTop - el.clientHeight);
  });

  // --- streaming while parked at the bottom (expect: follow) ----------------
  server.state.stream = { chunks, delayMs, token: 'tok', withToolFrames: false, maxDurationMs: timeoutMs };
  await markPhase(page, 'follow-stream');
  await resetProbe(page);
  const follow = await runStreamPhase(page, server, chunks, timeoutMs, 'bottom');

  // --- streaming while scrolled away (expect: hold position) ----------------
  server.state.stream = { chunks, delayMs, token: 'tok', withToolFrames: false, maxDurationMs: timeoutMs };
  await markPhase(page, 'hold-stream');
  await resetProbe(page);
  const hold = await runStreamPhase(page, server, chunks, timeoutMs, 'away');

  const followDistances = follow.frames.map((f) => f.distance);
  const holdScrollTops = hold.frames.map((f) => f.scrollTop);
  const holdBaseline = holdScrollTops[0] ?? 0;
  // Viewport movement is measured against where the user left it, so growth
  // below the fold is not counted as a jump.
  const holdShift = Math.max(0, ...holdScrollTops.map((t) => Math.abs(t - holdBaseline)));

  return {
    historySize,
    jumpToBottomOffsets,
    jumpToBottomExact: jumpToBottomOffsets.every((o) => o <= 2),
    roundTripOffsetAfterReturn,
    followFrames: follow.frames,
    followMaxDistanceFromBottom: followDistances.length ? Math.max(...followDistances) : null,
    // The app's own follow threshold is 48px (AnchoredChatColumn onScroll).
    followStayedAtBottom: followDistances.every((d) => d <= 48),
    followStreamCommits: follow.commits,
    holdFrames: hold.frames,
    holdMaxViewportShiftPx: Number(holdShift.toFixed(1)),
    holdStayedPut: holdShift <= 2,
    holdStreamCommits: hold.commits,
    raw: {
      followFrames: follow.frames,
      holdFrames: hold.frames,
      apiRequests: server.requestLog.map((r) => ({ method: r.method, path: r.path })),
    },
  };
}

interface StreamPhaseResult {
  frames: FrameSample[];
  commits: number;
}

/**
 * Sends one message and records scroll geometry every frame for the stream's life.
 *
 * Sampling runs inside a rAF loop started before the stream produces output, so
 * a jump is captured on the frame it occurs rather than averaged away by a
 * reading taken after the stream ends.
 */
async function runStreamPhase(
  page: Page,
  server: FixtureServer,
  chunks: number,
  timeoutMs: number,
  position: 'bottom' | 'away',
): Promise<StreamPhaseResult> {
  // Anchored composer: standalone textarea + icon-only send button labelled
  // by i18n `chat.send` ("Send"). The button is never disabled; an empty
  // submit is a no-op inside the composer, so a click after fill is enough.
  const composer = page.getByRole('textbox', { name: 'Ask Climber to do anything' });
  await composer.click();
  await composer.fill(`scroll stability probe ${position}`);
  const sendButton = page.getByRole('button', { name: 'Send' });

  // Sampling is armed before the click so no frame of the stream is missed.
  const sampling = page.evaluate((parked) => new Promise<FrameSample[]>((done) => {
    const frames: FrameSample[] = [];
    const find = () => {
      const candidates = Array.from(document.querySelectorAll('div'))
        .filter((el) => el.scrollHeight > el.clientHeight + 40);
      return (candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0] ?? null) as HTMLElement | null;
    };
    if (parked === 'away') {
      const el = find();
      // Park well above the bottom so the 48px follow threshold is disengaged.
      if (el) el.scrollTop = Math.max(0, el.scrollTop - 1200);
    }
    let settled = 0;
    const tick = () => {
      const node = find();
      if (!node) { done(frames); return; }
      frames.push({
        distance: Math.round(node.scrollHeight - node.scrollTop - node.clientHeight),
        scrollTop: Math.round(node.scrollTop),
        scrollHeight: Math.round(node.scrollHeight),
      });
      // Anchored flow: no [data-streaming-cursor] and no form[aria-busy] exist
      // anymore. The stream is over once the assistant turn exists and its
      // status dot stopped pulsing (active=false on the last ThinkingBubble).
      const bubbleCount = document.querySelectorAll('[data-testid="anchored-thinking-bubble"]').length;
      const pulsing = document.querySelectorAll('[data-testid="anchored-thinking-icon"].motion-safe\\:animate-pulse').length;
      if (bubbleCount > 0 && pulsing === 0) {
        settled += 1;
        // A few extra frames so the post-stream layout is captured too.
        if (settled > 10) { done(frames); return; }
      } else {
        settled = 0;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }), position);

  const framesBefore = server.streamFramesWritten;
  await sendButton.click();

  // Completion is driven by the server's own frame counter, so an early UI
  // state cannot cut the measurement short.
  const expected = chunks + 1; // + done
  const streamDeadline = Date.now() + timeoutMs;
  while (server.streamFramesWritten - framesBefore < expected) {
    if (Date.now() > streamDeadline) {
      throw new Error(`stream timed out after ${server.streamFramesWritten - framesBefore}/${expected} frames`);
    }
    await new Promise((r) => setTimeout(r, 50));
  }

  const frames = await sampling;
  const commits = await page.evaluate(() => (window as any).__perfCommits?.commits ?? 0);
  return { frames, commits };
}
