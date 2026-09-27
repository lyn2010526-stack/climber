/**
 * Browser-side probe: navigation, scenario driving, and metric extraction.
 *
 * All measurement logic that must run inside the page lives here as
 * serialisable functions. Keeping it in one place makes the report's numbers
 * traceable to a single reviewable implementation.
 */
import type { Page } from '@playwright/test';
import { REACT_COMMIT_HOOK_SOURCE } from './reactCommitHook.ts';
import { INSTRUMENT_SOURCE } from './instrument.ts';

export const CHAT_HASH = '#/chat';

/**
 * Resets per-scenario counters and phase marks.
 *
 * Called from Node, executed in the page: the counters live on `window`, and
 * this is the only place their baseline is established.
 */
export async function resetProbe(page: Page) {
  await page.evaluate(() => {
    const perf = (window as any).__perf;
    if (perf) perf.resetCounters();
    const commits = (window as any).__perfCommits;
    if (commits) {
      commits.commits = 0;
      commits.commitTimes = [];
      commits.enabled = true;
    }
  });
}

export async function installProbes(page: Page) {
  await page.addInitScript({ content: INSTRUMENT_SOURCE });
  await page.addInitScript({ content: REACT_COMMIT_HOOK_SOURCE });
}

/** Navigation marks used to segment a scenario's timeline. */
export async function markPhase(page: Page, label: string) {
  await page.evaluate((l: string) => {
    (window as any).__perf?.mark(l);
  }, label);
}

export async function sampleMemoryAndDom(page: Page) {
  return page.evaluate(() => (window as any).__perf.sample());
}

/** Everything the report records, as raw samples. */
export interface ProbeSnapshot {
  /** React commits since the last reset. */
  commits: number;
  commitTimes: number[];
  longTasks: Array<{ start: number; duration: number; name: string }>;
  frameIntervals: number[];
  heap: Array<{ t: number; usedJSHeapSize: number; totalJSHeapSize: number }>;
  domNodes: Array<{ t: number; nodes: number }>;
  /** Live listener counts per target+type, and cumulative add/remove balance. */
  listenerCounts: Record<string, number>;
  listenerTotal: Record<string, number>;
  resizeObserversCreated: number;
  resizeObserverCallbacks: number;
  visualViewportInitial: { width: number; height: number; offsetTop: number; pageTop: number } | null;
  phases: Array<{ label: string; at: number }>;
  longTaskUnsupported: string | null;
  /** Wall time from install to snapshot. */
  elapsed: number;
}

export async function readSnapshot(page: Page): Promise<ProbeSnapshot> {
  return page.evaluate(() => {
    const perf = (window as any).__perf;
    const commits = (window as any).__perfCommits;
    return {
      commits: commits?.commits ?? 0,
      commitTimes: commits?.commitTimes ?? [],
      longTasks: perf?.longTasks ?? [],
      frameIntervals: perf?.frameIntervals ?? [],
      heap: perf?.heap ?? [],
      domNodes: perf?.domNodes ?? [],
      listenerCounts: perf?.listenerCounts ?? {},
      listenerTotal: perf?.listenerTotal ?? {},
      resizeObserversCreated: perf?.resizeObserversCreated ?? 0,
      resizeObserverCallbacks: perf?.resizeObserverCallbacks ?? 0,
      visualViewportInitial: perf?.visualViewportInitial ?? null,
      phases: perf?.phases ?? [],
      longTaskUnsupported: perf?.longTaskUnsupported ?? null,
      elapsed: performance.now() - (perf?.startedAt ?? 0),
    };
  });
}

/**
 * Navigates to a hash route and waits for the app shell to be interactive.
 *
 * "Interactive" is defined as: the root has children, React has committed at
 * least once, and two animation frames have passed so layout is settled.
 */
export async function gotoApp(page: Page, baseUrl: string, hash = CHAT_HASH) {
  await page.goto(`${baseUrl}/${hash}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => {
    const root = document.getElementById('root');
    return !!root && root.childElementCount > 0;
  }, undefined, { timeout: 30_000 });
  await settle(page);
}

/** Waits two animation frames, so style and layout are flushed. */
export async function settle(page: Page) {
  await page.evaluate(() => new Promise<void>((done) => {
    requestAnimationFrame(() => requestAnimationFrame(() => done()));
  }));
}

/** Reads a navigation-timing entry from the real app load. */
export async function readNavigationTiming(page: Page) {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
    if (!nav) return null;
    return {
      responseStart: nav.responseStart,
      domContentLoadedEventEnd: nav.domContentLoadedEventEnd,
      loadEventEnd: nav.loadEventEnd,
      domInteractive: nav.domInteractive,
      transferSize: nav.transferSize,
      encodedBodySize: nav.encodedBodySize,
      decodedBodySize: nav.decodedBodySize,
    };
  });
}

/** FCP and LCP from the paint/LCP entries, when the browser exposes them. */
export async function readPaintTiming(page: Page) {
  return page.evaluate(() => {
    const paints = performance.getEntriesByType('paint').map((e) => ({
      name: e.name, startTime: Number(e.startTime.toFixed(2)),
    }));
    const lcpEntries = performance.getEntriesByType('largest-contentful-paint') as any[];
    return {
      paints,
      lcp: lcpEntries.length
        ? { startTime: Number(lcpEntries[lcpEntries.length - 1].startTime.toFixed(2)) }
        : null,
    };
  });
}

/**
 * Long tasks attributed to the app's own bundle.
 *
 * The longtask entry carries attribution only indirectly, so this returns every
 * entry and lets the report reason about the count; the caller filters by the
 * scenario window using the phase marks.
 */
export async function readLongTasksInWindow(page: Page, fromLabel: string, toLabel?: string) {
  return page.evaluate(([from, to]) => {
    const perf = (window as any).__perf;
    const phases: Array<{ label: string; at: number }> = perf?.phases ?? [];
    const start = phases.find((p) => p.label === from)?.at ?? 0;
    let end = Number.POSITIVE_INFINITY;
    if (to) {
      const found = phases.find((p) => p.label === to);
      if (found) end = found.at;
    }
    return (perf?.longTasks ?? []).filter((t: any) => t.start >= start && t.start <= end);
  }, [fromLabel, toLabel ?? null] as [string, string | null]);
}

/** Counts DOM nodes inside the transcript, the real cost driver. */
export async function countTranscriptNodes(page: Page) {
  return page.evaluate(() => {
    const transcript = document.querySelector('[data-transcript]');
    return {
      total: document.getElementsByTagName('*').length,
      transcriptDescendants: transcript ? transcript.getElementsByTagName('*').length : 0,
      messageRows: transcript ? transcript.children.length : 0,
    };
  });
}

/** Scroll container geometry plus current offset, for scroll-stability checks. */
export async function readScrollState(page: Page) {
  return page.evaluate(() => {
    // The transcript lives in the only vertically scrolling chat pane.
    const candidates = Array.from(document.querySelectorAll('div'))
      .filter((el) => el.scrollHeight > el.clientHeight + 40);
    const el = candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0] as HTMLElement | undefined;
    if (!el) return null;
    return {
      scrollTop: el.scrollTop,
      scrollHeight: el.scrollHeight,
      clientHeight: el.clientHeight,
      distanceFromBottom: el.scrollHeight - el.scrollTop - el.clientHeight,
    };
  });
}

/** Drives a scroll of the transcript and samples frame pacing during it. */
export async function scrollTranscript(page: Page, steps: number, stepDelayMs: number) {
  return page.evaluate(async ([n, delay]) => {
    const candidates = Array.from(document.querySelectorAll('div'))
      .filter((el) => el.scrollHeight > el.clientHeight + 40);
    const el = candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0] as HTMLElement | undefined;
    if (!el) return null;
    const frameGaps: number[] = [];
    const startHeight = el.scrollHeight;
    const perStep = (startHeight - el.clientHeight) / n;
    let last = performance.now();
    for (let i = 0; i < n; i += 1) {
      el.scrollTop = perStep * (i + 1);
      await new Promise<void>((done) => {
        const tick = (t: number) => {
          frameGaps.push(Number((t - last).toFixed(3)));
          last = t;
          if (frameGaps.length < 2) requestAnimationFrame(tick);
          else done();
        };
        requestAnimationFrame(tick);
      });
      await new Promise((r) => setTimeout(r, delay));
    }
    return { frameGaps, finalScrollTop: el.scrollTop, scrollHeight: el.scrollHeight };
  }, [steps, stepDelayMs] as [number, number]);
}

/** Jumps to the bottom and reports whether the offset lands exactly. */
export async function jumpToBottom(page: Page) {
  return page.evaluate(() => {
    const candidates = Array.from(document.querySelectorAll('div'))
      .filter((el) => el.scrollHeight > el.clientHeight + 40);
    const el = candidates.sort((a, b) => b.scrollHeight - a.scrollHeight)[0] as HTMLElement | undefined;
    if (!el) return null;
    el.scrollTop = el.scrollHeight;
    return { scrollTop: el.scrollTop, distanceFromBottom: el.scrollHeight - el.scrollTop - el.clientHeight };
  });
}
