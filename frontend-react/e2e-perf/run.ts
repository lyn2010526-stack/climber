#!/usr/bin/env node --experimental-strip-types
/**
 * Performance baseline runner — long lists and streaming rendering.
 *
 * Produces `artifacts/performance-baseline.json`. Every number in that file
 * carries a `host` block (machine capacity, load before and after the run, CPU
 * utilisation) and a `raw` block (the untouched sample arrays), so a figure can
 * always be traced back to the samples and the machine that produced it.
 *
 * Usage:
 *   node --experimental-strip-types e2e-perf/run.ts
 *   node --experimental-strip-types e2e-perf/run.ts --only=streaming
 *   node --experimental-strip-types e2e-perf/run.ts --sizes=200,1000
 *
 * The app under test is the production build in `dist/`, served by a local
 * fixture server. A dev server is deliberately avoided: StrictMode double-mounts
 * every component, which would inflate render counts and long tasks.
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium, type Browser } from 'playwright';
import { buildHostBlock, captureHost, captureRuntime, summarize } from './lib/host.ts';
import { startFixtureServer, type FixtureServer } from './lib/fixtureServer.ts';
import { buildMessagesPayload } from './lib/fixtures.ts';
import { installProbes } from './lib/probe.ts';
import { runLongListScenario } from './scenarios/longList.ts';
import { runStreamingScenario } from './scenarios/streaming.ts';
import { runLeakScenario } from './scenarios/leak.ts';
import { runScrollStabilityScenario } from './scenarios/scrollStability.ts';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const OUT = path.resolve(HERE, '../artifacts/performance-baseline.json');

const MESSAGE_SIZES = [200, 1000, 5000];
const STREAM_CASES = [
  { delayMs: 50, chunks: 60, historySize: 200 },
  { delayMs: 16, chunks: 200, historySize: 200 },
];
const LEAK_HISTORY = 1000;
const SCROLL_HISTORY = 1000;

/**
 * Repeats per configuration.
 *
 * A p95 over a single run is a single sample wearing a percentile's name. Three
 * repeats make the reported spread checkable: the report keeps every run's
 * samples, and the summary is computed across them.
 */
const REPEATS = 3;

function arg(name: string, fallback: string): string {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.split('=')[1] as string : fallback;
}

async function main() {
  const only = arg('only', 'all');
  const sizes = arg('sizes', MESSAGE_SIZES.join(',')).split(',').map((n) => Number(n.trim())).filter(Boolean);
  const repeats = Number(arg('repeats', String(REPEATS)));
  const shouldRun = (name: string) => only === 'all' || only === name;

  const hostBefore = captureHost();
  const browser: Browser = await chromium.launch();
  const server: FixtureServer = await startFixtureServer(0);
  const startedAt = new Date().toISOString();

  const report: Record<string, unknown> = {
    schema: 'climber.frontend.performance-baseline/1',
    generatedAt: startedAt,
    runtime: captureRuntime(),
    methodology: {
      target: 'production build served from dist/ (no StrictMode double-mount)',
      browser: 'chromium via playwright',
      hostBefore,
      notes: [
        'Each measurement pairs a host block with the raw sample arrays it was derived from.',
        'React commits are counted through the React DevTools global hook in the production bundle, so the count is finished commits, including the app\'s per-commit scroll and follow-output effects.',
        'Heap readings are taken through CDP after HeapProfiler.collectGarbage, so growth is retained memory rather than uncollected garbage.',
        'Long tasks are PerformanceObserver longtask entries (>50ms) recorded inside the measured window.',
        'Frame pacing is rAF inter-frame delta; the idle control (streaming scenario) establishes this host\'s rAF cadence so a streaming gap can be attributed to main-thread blocking.',
      ],
    },
  };

  try {
    // ---- A: long conversation list -----------------------------------------
    if (shouldRun('longlist')) {
      const samples = [];
      for (const count of sizes) {
        for (let run = 0; run < repeats; run += 1) {
          const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
          const page = await context.newPage();
          await installProbes(page);
          const sample = await runLongListScenario(page, server, { messageCount: count });
          samples.push({ ...sample, run });
          process.stderr.write(`[longlist] n=${count} run=${run + 1}/${repeats} first=${sample.firstInteractiveMs}ms commits=${sample.mountCommits} longTasks=${sample.longTaskCount} scrollP95=${sample.scrollFrameP95}ms\n`);
          await context.close();
        }
      }
      report.longListP95 = {
        description: 'Cost of a long conversation as a function of message count.',
        repeats,
        host: null,
        samples,
        summaryBySize: sizes.map((count) => {
          const forSize = samples.filter((s) => s.messageCount === count);
          const firsts = forSize.map((s) => s.firstInteractiveMs);
          const scrollP95s = forSize.map((s) => s.scrollFrameP95).filter((v): v is number => typeof v === 'number');
          const longTaskTotals = forSize.map((s) => s.longTaskTotalMs);
          return {
            messageCount: count,
            runs: forSize.length,
            firstInteractiveMs: { ...summarize(firsts), raw: firsts },
            firstInteractiveP95: summarize(firsts).p95,
            mountCommits: { ...summarize(forSize.map((s) => s.mountCommits)), raw: forSize.map((s) => s.mountCommits) },
            longTaskCount: { ...summarize(forSize.map((s) => s.longTaskCount)), raw: forSize.map((s) => s.longTaskCount) },
            longTaskTotalMs: { ...summarize(longTaskTotals), raw: longTaskTotals },
            longTaskMaxMs: { ...summarize(forSize.map((s) => s.longTaskMaxMs)), raw: forSize.map((s) => s.longTaskMaxMs) },
            totalDomNodes: forSize[0]?.totalDomNodes ?? null,
            domNodesPerMessage: forSize[0]?.domNodesPerMessage ?? null,
            scrollFrameP95: { ...summarize(scrollP95s), raw: scrollP95s },
            scrollJankFrames: { ...summarize(forSize.map((s) => s.scrollJankFrames)), raw: forSize.map((s) => s.scrollJankFrames) },
            heapAfterMountBytes: { ...summarize(forSize.map((s) => s.heapAfterMountBytes ?? 0)), raw: forSize.map((s) => s.heapAfterMountBytes) },
          };
        }),
      };
    }

    // ---- B: streaming render upper bound -----------------------------------
    if (shouldRun('streaming')) {
      const samples = [];
      for (const c of STREAM_CASES) {
        for (let run = 0; run < repeats; run += 1) {
          const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
          const page = await context.newPage();
          await installProbes(page);
          const sample = await runStreamingScenario(page, server, c);
          samples.push({ ...sample, run });
          process.stderr.write(`[streaming] chunks=${c.chunks} delay=${c.delayMs}ms run=${run + 1}/${repeats} commits=${sample.streamCommits} bound=${sample.requiredUpperBound} pass=${sample.passesBound} perChunk=${sample.commitsPerChunk}\n`);
          await context.close();
        }
      }
      report.streamingRenderBound = {
        description: 'Hard requirement: React commits during a stream must stay below chunks/4.',
        boundRule: 'streamCommits < chunks / 4',
        repeats,
        host: null,
        samples,
        verdict: STREAM_CASES.map((c) => {
          const forCase = samples.filter((s) => s.chunks === c.chunks && s.delayMs === c.delayMs);
          const commits = forCase.map((s) => s.streamCommits);
          const stats = summarize(commits);
          const bound = Number((c.chunks / 4).toFixed(2));
          return {
            chunks: c.chunks,
            delayMs: c.delayMs,
            runs: forCase.length,
            streamCommits: { ...stats, raw: commits },
            requiredUpperBound: bound,
            passes: forCase.every((s) => s.passesBound),
            /** Worst observed ratio, the number to quote as the headline. */
            worstCommitsPerChunk: forCase.length ? Math.max(...forCase.map((s) => s.commitsPerChunk)) : null,
            commitsPerChunk: { ...stats, raw: forCase.map((s) => s.commitsPerChunk) },
            marginToBound: bound - (stats.max ?? 0),
            longTaskTotalMs: { ...summarize(forCase.map((s) => s.longTaskTotalMs)), raw: forCase.map((s) => s.longTaskTotalMs) },
            streamDurationMs: { ...summarize(forCase.map((s) => s.streamDurationMs)), raw: forCase.map((s) => s.streamDurationMs) },
            frameP95: { ...summarize(forCase.map((s) => s.frameP95 ?? 0)), raw: forCase.map((s) => s.frameP95) },
            idleFrameP95: { ...summarize(forCase.map((s) => s.idleFrameP95 ?? 0)), raw: forCase.map((s) => s.idleFrameP95) },
            streamTextRendered: forCase.every((s) => s.streamTextRendered),
            streamTextRenderedRaw: forCase.map((s) => s.streamTextRendered),
          };
        }),
        allPass: samples.every((s) => s.passesBound),
      };
    }

    // ---- C: memory and listener accounting --------------------------------
    if (shouldRun('leak')) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();
      await installProbes(page);
      const sample = await runLeakScenario(page, server, { historySize: LEAK_HISTORY, cycleCount: 5 });
      report.memoryAndLeak = { description: 'Retained heap, DOM release and listener balance across mount/unmount cycles.', host: null, sample };
      process.stderr.write(`[leak] retained=${sample.heapRetainedGrowthMiB}MiB perMsg=${sample.heapBytesPerMessage}B domReleased=${sample.domNodesWhileUnmounted[0] ?? 'n/a'}\n`);
      await context.close();
    }

    // ---- D: scroll stability ------------------------------------------------
    if (shouldRun('scroll')) {
      const runs = [];
      for (let run = 0; run < repeats; run += 1) {
        const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        const page = await context.newPage();
        await installProbes(page);
        const sample = await runScrollStabilityScenario(page, server, { historySize: SCROLL_HISTORY, chunks: 60, delayMs: 50 });
        runs.push({ ...sample, run });
        process.stderr.write(`[scroll] run=${run + 1}/${repeats} jumpExact=${sample.jumpToBottomExact} followMaxDist=${sample.followMaxDistanceFromBottom} holdMaxShift=${sample.holdMaxViewportShiftPx}px\n`);
        await context.close();
      }
      report.scrollStability = {
        description: 'Jump-to-bottom exactness and streaming follow/hold behaviour.',
        repeats,
        host: null,
        runs,
        sample: runs[0],
        summary: {
          jumpToBottomExact: runs.every((r) => r.jumpToBottomExact),
          roundTripOffsets: runs.map((r) => r.roundTripOffsetAfterReturn),
          followMaxDistanceFromBottom: runs.map((r) => r.followMaxDistanceFromBottom),
          followStayedAtBottom: runs.every((r) => r.followStayedAtBottom),
          holdMaxViewportShiftPx: { ...summarize(runs.map((r) => r.holdMaxViewportShiftPx ?? 0)), raw: runs.map((r) => r.holdMaxViewportShiftPx) },
          holdStayedPut: runs.every((r) => r.holdStayedPut),
        },
      };
    }
  } finally {
    const hostAfter = captureHost();
    const host = buildHostBlock(hostBefore, hostAfter);
    // Every section carries the same host block: the machine a number was
    // measured on is part of the number.
    for (const key of Object.keys(report)) {
      const section = report[key] as Record<string, unknown>;
      if (section && typeof section === 'object' && 'host' in section) {
        section.host = host;
      }
    }
    report.methodology = { ...(report.methodology as Record<string, unknown>), hostBefore, hostAfter, host };
    report.completedAt = new Date().toISOString();

    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
    process.stderr.write(`\nwrote ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)} KiB)\n`);

    await server.close();
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`baseline run failed: ${error?.stack ?? error}\n`);
  process.exit(1);
});
