/**
 * Scenario A — long conversation list: p95 cost of a large transcript.
 *
 * The question this answers: as a session grows, what does the browser cost per
 * interaction? Three sizes (200 / 1000 / 5000) are measured so the curve is
 * observed rather than extrapolated, and each size reports first-interactive
 * time, scroll frame pacing, and long-task count.
 *
 * The app is driven unmodified. The fixture server answers the same endpoints
 * `useChat` calls, and the transcript is rendered by the shipped
 * `ChatInterface` with no product code altered.
 */
import type { Page } from '@playwright/test';
import { summarize } from '../lib/host.ts';
import type { FixtureServer } from '../lib/fixtureServer.ts';
import { buildMessagesPayload } from '../lib/fixtures.ts';
import {
  gotoApp, markPhase, readSnapshot, resetProbe, settle,
  readNavigationTiming, readPaintTiming, countTranscriptNodes, readScrollState,
  scrollTranscript, sampleMemoryAndDom,
} from '../lib/probe.ts';

export interface LongListSample {
  messageCount: number;
  /** Wall time from navigation start to the full transcript being in the DOM. */
  firstInteractiveMs: number;
  domContentLoadedMs: number | null;
  loadEventMs: number | null;
  fcpMs: number | null;
  lcpMs: number | null;
  /** React commits from navigation until the transcript is fully mounted. */
  mountCommits: number;
  /** React commits caused by the scripted scroll alone. */
  scrollCommits: number;
  longTaskCount: number;
  longTaskTotalMs: number;
  longTaskMaxMs: number;
  totalDomNodes: number;
  transcriptDescendants: number;
  messageRows: number;
  /** DOM nodes per message: the cost driver behind any virtualisation win. */
  domNodesPerMessage: number;
  heapAfterMountBytes: number | null;
  scrollFrameGaps: number[];
  scrollFrameP50: number | null;
  scrollFrameP95: number | null;
  /** Frames over 32ms, the practical smoothness ceiling at 60Hz. */
  scrollJankFrames: number;
  scrollFinalDistanceFromBottom: number | null;
  raw: {
    navigationTiming: unknown;
    paintTiming: unknown;
    longTasks: unknown[];
    frameIntervals: number[];
    commitTimes: number[];
    heapSamples: unknown[];
    domNodeSamples: unknown[];
    scrollFrameGaps: number[];
    apiRequests: Array<{ method: string; path: string }>;
  };
}

export interface LongListOptions {
  messageCount: number;
  seed?: number;
  viewport?: { width: number; height: number };
  scrollSteps?: number;
  scrollDelayMs?: number;
}

export async function runLongListScenario(
  page: Page,
  server: FixtureServer,
  options: LongListOptions,
): Promise<LongListSample> {
  const {
    messageCount,
    seed = 20260926,
    viewport = { width: 1440, height: 900 },
    scrollSteps = 40,
    scrollDelayMs = 16,
  } = options;

  await page.setViewportSize(viewport);

  // Program the server before the app asks for anything.
  server.state.messagesPayload = buildMessagesPayload(messageCount, seed);
  server.state.messageCount = messageCount;
  server.requestLog.length = 0;

  // The commit counter must span the mount, so it is zeroed here rather than
  // after navigation: React commits the transcript during the first load, and
  // resetting afterwards would report a mount that never happened.
  await resetProbe(page);

  const navStart = Date.now();
  await gotoApp(page, server.baseUrl);

  // Ready means every fixture message is in the transcript. React keys rows by
  // message id, so a full row count is an exact readiness signal, whereas a
  // descendant count would only bound it.
  await page.waitForFunction(
    (count) => {
      const transcript = document.querySelector('[data-transcript]');
      return !!transcript && transcript.children.length >= count;
    },
    messageCount,
    { timeout: 240_000 },
  );
  const firstInteractiveMs = Date.now() - navStart;
  await settle(page);
  // Sampled before the reset so the heap reading reflects the mounted
  // transcript rather than an empty post-reset baseline.
  await sampleMemoryAndDom(page);

  // Mount cost is now fully captured. Long tasks and frame pacing are read
  // before the scroll phase so the two costs stay separable.
  const mountSnapshot = await readSnapshot(page);
  await markPhase(page, 'mounted');

  const navTiming = await readNavigationTiming(page);
  const paintTiming = await readPaintTiming(page);
  const nodes = await countTranscriptNodes(page);
  const mountHeap = mountSnapshot.heap[mountSnapshot.heap.length - 1] ?? null;

  // From here the counters track the scroll interaction only.
  await resetProbe(page);
  await markPhase(page, 'scrolling');
  const scroll = await scrollTranscript(page, scrollSteps, scrollDelayMs);
  await markPhase(page, 'scrolled');
  const scrollState = await readScrollState(page);
  await settle(page);
  const scrollSnapshot = await readSnapshot(page);

  const frameGaps = (scroll?.frameGaps ?? []).filter((g) => g > 0);
  const frameStats = summarize(frameGaps);
  const longTasks = mountSnapshot.longTasks;
  // Commits attributed to the mount: the post-mount reset discards them, so
  // the mount total is read before that reset.
  const mountCommits = mountSnapshot.commits;

  return {
    messageCount,
    firstInteractiveMs,
    domContentLoadedMs: navTiming?.domContentLoadedEventEnd ?? null,
    loadEventMs: navTiming?.loadEventEnd ?? null,
    fcpMs: paintTiming.paints.find((p) => p.name === 'first-contentful-paint')?.startTime ?? null,
    lcpMs: paintTiming.lcp?.startTime ?? null,
    mountCommits,
    scrollCommits: scrollSnapshot.commits,
    longTaskCount: longTasks.length,
    longTaskTotalMs: Number(longTasks.reduce((a, t) => a + t.duration, 0).toFixed(2)),
    longTaskMaxMs: longTasks.length ? Number(Math.max(...longTasks.map((t) => t.duration)).toFixed(2)) : 0,
    totalDomNodes: nodes.total,
    transcriptDescendants: nodes.transcriptDescendants,
    messageRows: nodes.messageRows,
    domNodesPerMessage: Number((nodes.transcriptDescendants / Math.max(1, nodes.messageRows)).toFixed(1)),
    heapAfterMountBytes: mountHeap?.usedJSHeapSize ?? null,
    scrollFrameGaps: frameGaps,
    scrollFrameP50: frameStats.p50,
    scrollFrameP95: frameStats.p95,
    scrollJankFrames: frameGaps.filter((g) => g > 32).length,
    scrollFinalDistanceFromBottom: scrollState?.distanceFromBottom ?? null,
    raw: {
      navigationTiming: navTiming,
      paintTiming,
      longTasks,
      frameIntervals: scrollSnapshot.frameIntervals,
      commitTimes: mountSnapshot.commitTimes,
      heapSamples: mountSnapshot.heap,
      domNodeSamples: mountSnapshot.domNodes,
      scrollFrameGaps: frameGaps,
      apiRequests: server.requestLog.map((r) => ({ method: r.method, path: r.path })),
    },
  };
}
