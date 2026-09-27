/**
 * Scenario B — streaming render upper bound.
 *
 * This is the metric that turns "one setState per chunk" from a code-reading
 * claim into a measurement. The hard requirement: React commits during a
 * stream must stay below `chunks / 4`.
 *
 * Why that bound: a chunk that arrives every 16ms is, by definition, already
 * at the display refresh rate. If each chunk produced its own commit, the
 * render loop would be running at chunk rate with nothing coalesced. Requiring
 * at least a 4x reduction says rendering has to be decoupled from chunk arrival
 * — batched per frame at worst, and cheaper still when chunks arrive slower
 * than a frame. The two rates bracket the real backend: 50ms is a slow
 * provider, 16ms is the worst case.
 *
 * A commit is counted through the React DevTools global hook in the production
 * build, so the number is what React actually finished, including the
 * streaming-cursor and follow-output effects the app registers per commit.
 */
import type { Page } from '@playwright/test';
import type { FixtureServer } from '../lib/fixtureServer.ts';
import { summarize } from '../lib/host.ts';
import {
  gotoApp, markPhase, readSnapshot, resetProbe, settle, sampleMemoryAndDom,
} from '../lib/probe.ts';

/** Waits for a locator's element to stop being disabled, then returns it. */
async function expectEnabled(locator: import('@playwright/test').Locator) {
  const deadline = Date.now() + 15_000;
  while (await locator.isDisabled()) {
    if (Date.now() > deadline) throw new Error('send button stayed disabled after typing');
    await new Promise((r) => setTimeout(r, 50));
  }
  return locator;
}

/**
 * rAF cadence on an otherwise idle page, sampled after the stream.
 *
 * This is the control for the streaming frame numbers: it establishes what this
 * browser and host produce when nothing is happening, so a streaming frame gap
 * can be attributed to blocking rather than to the environment.
 */
async function measureIdleFrameRate(page: Page, frames = 30): Promise<number[]> {
  return page.evaluate((n) => new Promise<number[]>((done) => {
    const gaps: number[] = [];
    let last = 0;
    let seen = 0;
    const tick = (t: number) => {
      if (last > 0) gaps.push(Number((t - last).toFixed(3)));
      last = t;
      seen += 1;
      if (seen <= n) requestAnimationFrame(tick);
      else done(gaps);
    };
    requestAnimationFrame(tick);
  }), frames);
}

export interface StreamingSample {
  /** Text frames the server was told to emit. */
  chunks: number;
  /** Inter-frame delay configured on the server, in ms. */
  delayMs: number;
  /** Frames the server actually wrote, including tool and done frames. */
  framesWritten: number;
  /** React commits measured from just before submit to just after done. */
  streamCommits: number;
  /** The bound under test: chunks / 4. */
  requiredUpperBound: number;
  /** commits < requiredUpperBound */
  passesBound: boolean;
  /** Commits divided by chunks: 1.0 means one render per chunk. */
  commitsPerChunk: number;
  /** Wall time from submit to the done frame being processed. */
  streamDurationMs: number;
  /** Observed inter-commit gaps, ms. */
  commitIntervals: number[];
  commitIntervalP50: number | null;
  commitIntervalP95: number | null;
  longTaskCount: number;
  longTaskTotalMs: number;
  frameIntervals: number[];
  frameP95: number | null;
  /** Frame gaps with nothing else running: the control for `frameP95`. */
  idleFrameP50: number | null;
  idleFrameP95: number | null;
  heapAfterStreamBytes: number | null;
  /** Rows in the transcript at the end of the stream. */
  finalMessageRows: number;
  /** True when the assistant text actually landed in the DOM. */
  streamTextRendered: boolean;
  raw: {
    commitTimes: number[];
    longTasks: unknown[];
    frameIntervals: number[];
    heapSamples: unknown[];
    domNodeSamples: unknown[];
    apiRequests: Array<{ method: string; path: string }>;
  };
}

export interface StreamingOptions {
  /** Existing history length, so streaming cost is measured on a real corpus. */
  historySize: number;
  chunks: number;
  delayMs: number;
  withToolFrames?: boolean;
  viewport?: { width: number; height: number };
  seed?: number;
  /** How long to wait for the stream to finish before giving up. */
  timeoutMs?: number;
}

/** Submits the composer and waits for the stream to terminate. */
export async function runStreamingScenario(
  page: Page,
  server: FixtureServer,
  options: StreamingOptions,
): Promise<StreamingSample> {
  const {
    historySize,
    chunks,
    delayMs,
    withToolFrames = true,
    viewport = { width: 1440, height: 900 },
    seed = 20260926,
    timeoutMs = 300_000,
  } = options;

  await page.setViewportSize(viewport);

  // A pre-existing conversation makes the stream land on a realistic corpus:
  // the render cost of one chunk scales with how much is already on screen.
  const { buildMessagesPayload } = await import('../lib/fixtures.ts');
  server.state.messagesPayload = buildMessagesPayload(historySize, seed);
  server.state.messageCount = historySize;
  server.state.stream = {
    chunks, delayMs, token: 'tok', withToolFrames, maxDurationMs: timeoutMs,
  };
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

  // The stream measurement starts the instant the submit is dispatched, so
  // every commit caused by the stream is inside the window.
  await resetProbe(page);
  await markPhase(page, 'stream-start');
  const streamStart = Date.now();
  const framesBefore = server.streamFramesWritten;

  // Typed through the real input path rather than by assigning `value`, so
  // React's onChange and the composer's own auto-grow run exactly as they do
  // for a person typing. The native setter assignment that would be faster
  // here bypasses the controlled-component contract and can leave state empty.
  const composer = page.locator('form textarea').first();
  await composer.click();
  await composer.fill('measure the streaming render bound');
  // The send button is disabled until the controlled state registers the text.
  const sendButton = page.locator('form button[type="submit"]');
  await sendButton.waitFor({ state: 'visible', timeout: 15_000 });
  await expectEnabled(sendButton);
  await sendButton.click();

  // Fail loudly with the request log if the submit never reached the backend,
  // rather than reporting a zero-chunk stream as a fast one.
  const submitDeadline = Date.now() + 15_000;
  while (!server.requestLog.some((r) => r.path.endsWith('/chat'))) {
    if (Date.now() > submitDeadline) {
      throw new Error(`chat request never sent; saw: ${server.requestLog.map((r) => r.method + ' ' + r.path).join(', ')}`);
    }
    await new Promise((r) => setTimeout(r, 50));
  }

  // The stream is done when the server has written its terminal done frame and
  // the app has processed it. The wait is driven by the server's own frame
  // counter rather than a UI condition: a composer that is momentarily enabled
  // between submit and first chunk would otherwise end the measurement early.
  const expectedFrames = chunks + (withToolFrames ? 3 : 1); // +tool_call, tool_result, done
  const deadline = Date.now() + timeoutMs;
  while (server.streamFramesWritten - framesBefore < expectedFrames) {
    if (Date.now() > deadline) {
      throw new Error(
        `stream did not complete: wrote ${server.streamFramesWritten - framesBefore}/${expectedFrames} frames in ${timeoutMs}ms`,
      );
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  const streamDurationMs = Date.now() - streamStart;

  // Now wait for the app to settle the terminal frame into the DOM.
  await page.waitForFunction(
    ([count]) => {
      const transcript = document.querySelector('[data-transcript]');
      const text = transcript?.textContent ?? '';
      const lastToken = 'tok' + (count - 1);
      return text.includes(lastToken) && document.querySelectorAll('[data-streaming-cursor]').length === 0;
    },
    [chunks] as [number],
    { timeout: 60_000 },
  );
  await settle(page);
  await markPhase(page, 'stream-end');
  await sampleMemoryAndDom(page);

  const snapshot = await readSnapshot(page);
  const framesWritten = server.streamFramesWritten - framesBefore;
  const commitTimes = snapshot.commitTimes;
  const commitIntervals = commitTimes.slice(1).map((t, i) => Number((t - (commitTimes[i] as number)).toFixed(3)));
  const intervalStats = summarize(commitIntervals);
  const frameStats = summarize(snapshot.frameIntervals.filter((f) => f > 0));
  const requiredUpperBound = Number((chunks / 4).toFixed(2));
  const streamCommits = snapshot.commits;

  // The renderer was idling at 60Hz before the stream started, so a frame gap
  // far beyond ~16.7ms is main-thread blocking, not headless throttling. This
  // is recorded so the claim can be checked rather than assumed.
  const idleFrameStats = summarize(await measureIdleFrameRate(page));

  const finalState = await page.evaluate(() => {
    const transcript = document.querySelector('[data-transcript]');
    return {
      rows: transcript ? transcript.children.length : 0,
      // The streaming assistant turn lands last; its presence proves the
      // chunk deltas reached the DOM rather than being dropped.
      hasStreamedText: (document.querySelector('[data-transcript]')?.textContent ?? '').includes('tok0'),
    };
  });

  return {
    chunks,
    delayMs,
    framesWritten,
    streamCommits,
    requiredUpperBound,
    passesBound: streamCommits < requiredUpperBound,
    commitsPerChunk: Number((streamCommits / chunks).toFixed(3)),
    streamDurationMs,
    commitIntervals,
    commitIntervalP50: intervalStats.p50,
    commitIntervalP95: intervalStats.p95,
    longTaskCount: snapshot.longTasks.length,
    longTaskTotalMs: Number(snapshot.longTasks.reduce((a, t) => a + t.duration, 0).toFixed(2)),
    frameIntervals: snapshot.frameIntervals,
    frameP95: frameStats.p95,
    idleFrameP50: idleFrameStats.p50,
    idleFrameP95: idleFrameStats.p95,
    heapAfterStreamBytes: snapshot.heap[snapshot.heap.length - 1]?.usedJSHeapSize ?? null,
    finalMessageRows: finalState.rows,
    streamTextRendered: finalState.hasStreamedText,
    raw: {
      commitTimes,
      longTasks: snapshot.longTasks,
      frameIntervals: snapshot.frameIntervals,
      heapSamples: snapshot.heap,
      domNodeSamples: snapshot.domNodes,
      apiRequests: server.requestLog.map((r) => ({ method: r.method, path: r.path })),
    },
  };
}
