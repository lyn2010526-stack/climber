/**
 * Scenario C — memory growth and listener accounting under a long session.
 *
 * Three questions, answered with three independent instruments:
 *
 * 1. Does a long conversation leak memory? Measured with CDP: the heap is
 *    collected before every reading, so a growth that survives collection is
 *    retained memory rather than uncollected garbage.
 * 2. Do the listeners the app registers get removed? Measured by wrapping
 *    add/removeEventListener, which makes the live balance per target+type
 *    observable from outside React.
 * 3. Does the DOM shrink when the conversation is replaced? Measured directly,
 *    since a transcript that is not released shows up as node growth.
 *
 * The mount/unmount cycle is driven in-page by navigating between routes, so
 * the probe state survives: a page reload would reset the very counters being
 * measured.
 */
import type { CDPSession, Page } from '@playwright/test';
import type { FixtureServer } from '../lib/fixtureServer.ts';
import { buildMessagesPayload } from '../lib/fixtures.ts';
import {
  gotoApp, markPhase, readSnapshot, resetProbe, settle, sampleMemoryAndDom,
} from '../lib/probe.ts';

/** Listener keys the task calls out, reported explicitly even when absent. */
export const WATCHED_LISTENERS = [
  'window|resize',
  'window|keydown',
  'document|keydown',
  'document|resize',
  'window|scroll',
  'document|scroll',
  'window|storage',
  'window|focus',
  'window|hashchange',
] as const;

export interface HeapReading {
  usedBytes: number;
  totalBytes: number;
}

/** Forces a collection, then reads the heap through CDP. */
async function measureHeapAfterGC(cdp: CDPSession): Promise<HeapReading | null> {
  try {
    await cdp.send('HeapProfiler.enable');
    await cdp.send('HeapProfiler.collectGarbage');
    const result = await cdp.send('Runtime.getHeapUsage') as { usedSize: number; totalSize: number };
    return { usedBytes: result.usedSize, totalBytes: result.totalSize };
  } catch (error) {
    // Recorded as a measurement gap rather than silently reported as zero.
    heapUnavailableReason = String(error).slice(0, 200);
    return null;
  }
}

/** Set when CDP heap collection is not available on this browser build. */
let heapUnavailableReason: string | null = null;

export interface LeakSample {
  historySize: number;
  /** Full mount -> unmount cycles performed. */
  cycleCount: number;
  /** GC'd used heap after each cycle's mount. */
  heapAfterMountBytes: number[];
  /** DOM node count after each cycle's mount. */
  domNodesAfterMount: number[];
  /** DOM node count measured while unmounted, to prove release. */
  domNodesWhileUnmounted: number[];
  /** Retained heap growth from the first to the last cycle. */
  heapRetainedGrowthBytes: number;
  heapRetainedGrowthMiB: number;
  /** Heap per message, the number that decides when virtualisation is required. */
  heapBytesPerMessage: number | null;
  /** Watched listener keys with a non-zero live balance after unmount. */
  watchedLiveListenerKeys: string[];
  /** Every key with a non-zero live balance, including unwatched ones. */
  allLiveListenerKeys: string[];
  listenerBalance: Record<string, number>;
  resizeObserversCreated: number;
  resizeObserverCallbacks: number;
  visualViewportInitial: unknown;
  longTaskCount: number;
  /** Non-null when the heap could not be read through CDP. */
  heapUnavailable: string | null;
  raw: {
    heapSamples: unknown[];
    domNodeSamples: unknown[];
    longTasks: unknown[];
    commitTimes: number[];
    listenerCounts: Record<string, number>;
    listenerBalance: Record<string, number>;
  };
}

export interface LeakOptions {
  historySize: number;
  cycleCount?: number;
  viewport?: { width: number; height: number };
  seed?: number;
}

/** Route that is not the chat page, used to unmount the chat subtree. */
const AWAY_HASH = '#/settings';
const CHAT_HASH = '#/chat';

export async function runLeakScenario(
  page: Page,
  server: FixtureServer,
  options: LeakOptions,
): Promise<LeakSample> {
  const {
    historySize,
    cycleCount = 5,
    viewport = { width: 1440, height: 900 },
    seed = 20260926,
  } = options;

  await page.setViewportSize(viewport);
  server.state.messagesPayload = buildMessagesPayload(historySize, seed);
  server.state.messageCount = historySize;
  server.requestLog.length = 0;

  const cdp = await page.context().newCDPSession(page);

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
  await resetProbe(page);
  await markPhase(page, 'leak-start');

  const heapAfterMountBytes: number[] = [];
  const domNodesAfterMount: number[] = [];
  const domNodesWhileUnmounted: number[] = [];

  for (let cycle = 0; cycle < cycleCount; cycle += 1) {
    // Unmount the chat subtree in-page. A route change runs every effect
    // cleanup in ChatInterface and its children, which is exactly where a
    // forgotten removeEventListener would surface.
    await page.evaluate((hash) => { window.location.hash = hash; }, AWAY_HASH);
    await page.waitForFunction(() => !document.querySelector('[data-transcript]'), undefined, { timeout: 30_000 });
    await settle(page);

    const unmounted = await page.evaluate(() => document.getElementsByTagName('*').length);
    domNodesWhileUnmounted.push(unmounted);
    const heapUnmounted = await measureHeapAfterGC(cdp);

    // Mount again with the same long conversation.
    await page.evaluate((hash) => { window.location.hash = hash; }, CHAT_HASH);
    await page.waitForFunction(
      (count) => {
        const transcript = document.querySelector('[data-transcript]');
        return !!transcript && transcript.children.length >= count;
      },
      historySize,
      { timeout: 240_000 },
    );
    await settle(page);

    const sample = await sampleMemoryAndDom(page);
    if (sample.nodes !== undefined) domNodesAfterMount.push(sample.nodes);
    if (sample.mem) heapAfterMountBytes.push(sample.mem.usedJSHeapSize);
    // The GC'd reading is preferred: it excludes uncollected garbage.
    if (heapUnmounted) {
      const mounted = await measureHeapAfterGC(cdp);
      if (mounted) heapAfterMountBytes[heapAfterMountBytes.length - 1] = mounted.usedBytes;
    }
  }

  await markPhase(page, 'leak-end');
  const snapshot = await readSnapshot(page);

  const retained = heapAfterMountBytes.length >= 2
    ? (heapAfterMountBytes[heapAfterMountBytes.length - 1] as number) - (heapAfterMountBytes[0] as number)
    : 0;

  const allLive = Object.entries(snapshot.listenerCounts)
    .filter(([, count]) => count > 0)
    .map(([key]) => key)
    .sort();

  return {
    historySize,
    cycleCount,
    heapAfterMountBytes,
    domNodesAfterMount,
    domNodesWhileUnmounted,
    heapRetainedGrowthBytes: retained,
    heapRetainedGrowthMiB: Number((retained / 1024 / 1024).toFixed(2)),
    heapBytesPerMessage: heapAfterMountBytes.length
      ? Number(((heapAfterMountBytes[0] as number) / historySize).toFixed(0))
      : null,
    watchedLiveListenerKeys: WATCHED_LISTENERS.filter((key) => (snapshot.listenerCounts[key] ?? 0) > 0),
    allLiveListenerKeys: allLive,
    listenerBalance: snapshot.listenerTotal,
    resizeObserversCreated: snapshot.resizeObserversCreated,
    resizeObserverCallbacks: snapshot.resizeObserverCallbacks,
    visualViewportInitial: snapshot.visualViewportInitial,
    longTaskCount: snapshot.longTasks.length,
    heapUnavailable: heapUnavailableReason,
    raw: {
      heapSamples: snapshot.heap,
      domNodeSamples: snapshot.domNodes,
      longTasks: snapshot.longTasks,
      commitTimes: snapshot.commitTimes,
      listenerCounts: snapshot.listenerCounts,
      listenerBalance: snapshot.listenerTotal,
    },
  };
}
