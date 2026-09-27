# Performance baseline: long lists and streaming rendering

Measures four baselines against the **real** chat surface, in a **real
Chromium**, with no product code modified. Output:
`artifacts/performance-baseline.json`.

## Why the production build

The dev server runs under `StrictMode`, which double-mounts every component.
Render counts, long tasks and commit intervals would all be inflated by an
artefact of the development harness rather than by the application. The
runner therefore serves `dist/` from a local fixture server.

```bash
npm run build   # required once before measuring
```

## Running

```bash
# Everything, writing artifacts/performance-baseline.json
node --experimental-strip-types e2e-perf/run.ts

# One baseline at a time
node --experimental-strip-types e2e-perf/run.ts --only=longlist
node --experimental-strip-types e2e-perf/run.ts --only=streaming
node --experimental-strip-types e2e-perf/run.ts --only=leak
node --experimental-strip-types e2e-perf/run.ts --only=scroll

# Override the message sizes for the long-list curve
node --experimental-strip-types e2e-perf/run.ts --sizes=200,1000,5000
```

Requires `npm run build` to have produced `dist/`, and Playwright's Chromium
(`npx playwright install chromium`).

## Placement, and why it does not touch unit tests

Everything lives in `e2e-perf/`, outside `src/`:

- `vite.config.ts` sets `test.include: ['src/**/*.{test,spec}.?(c|m)[jt]s?(x)']`,
  so vitest never collects these files.
- `tsconfig.app.json` includes only `src`; `tsconfig.node.json` includes only
  `vite.config.ts`. Typecheck does not reach `e2e-perf/`.
- `playwright.config.ts` uses `testDir: './e2e'`, so the existing e2e suite
  never picks these up either.

They are plain Node scripts, not Playwright test specs, so `npx playwright test`
is unaffected.

## Layout

| Path | Role |
|---|---|
| `run.ts` | Orchestrates the four baselines, writes the report. |
| `lib/host.ts` | Host snapshots, load/CPU capture, percentile helper. |
| `lib/fixtureServer.ts` | Serves `dist/`, app API state, paced SSE stream. |
| `lib/fixtures.ts` | Seeded, deterministic message generation. |
| `lib/probe.ts` | In-page navigation and metric extraction. |
| `lib/instrument.ts` | Serialised probe: long tasks, rAF, heap, listeners. |
| `lib/reactCommitHook.ts` | React DevTools hook, installed pre-mount. |
| `lib/appFixtures.ts` | Optional per-page route overrides. |
| `scenarios/longList.ts` | Baseline A: long conversation list. |
| `scenarios/streaming.ts` | Baseline B: streaming render upper bound. |
| `scenarios/leak.ts` | Baseline C: memory and listener accounting. |
| `scenarios/scrollStability.ts` | Baseline D: scroll stability. |

## The four baselines

### A — Long conversation list p95

Loads 200 / 1000 / 5000 messages into the shipped `ChatInterface` and records
first-interactive time, mount commits, long tasks (>50ms), scroll frame pacing
and DOM size.

### B — Streaming render upper bound

The hard requirement: **React commits during a stream must stay below
`chunks / 4`**. A chunk arriving every 16ms is already at refresh rate, so one
render per chunk means nothing is coalesced. Two rates bracket a real backend:
50ms (slow provider) and 16ms (worst case).

Commits are counted through the React DevTools global hook, which fires once per
finished commit. That is the honest unit: it includes the per-commit scroll and
follow-output effects the app registers, which a count of `setState` calls would
miss.

### C — Memory and leak observation

Three independent instruments, because a leak can hide behind any one of them:

- **Heap**: read through CDP after `HeapProfiler.collectGarbage`, so growth is
  retained memory rather than uncollected garbage.
- **DOM**: node counts while mounted and while unmounted, which shows release.
- **Listeners**: `add/removeEventListener` and `ResizeObserver` are wrapped so
  the live balance per target+type is visible from outside React. Watched
  explicitly: `window|resize`, `document|keydown`, `window|scroll`,
  `window|storage`, `window|focus`, `window|hashchange`.

### D — Scroll stability

Jump-to-bottom exactness, and streaming behaviour in both directions: following
new output when parked at the bottom, and holding position when scrolled away.

`scrollTop` is the stability signal, not distance-from-bottom: while a stream
appends content below the viewport, distance-from-bottom grows legitimately even
when nothing moves. Both series are recorded.

## Every number carries a host block and a raw block

A number without both is an anecdote:

- `host` — CPU model, `logicalCpus`, total memory, load averages **before and
  after** the run, `cpuUtilizationPct` before/after/mean, platform.
- `raw` — the untouched sample arrays: long task entries, frame intervals,
  commit timestamps, heap samples, DOM node samples, scroll frame series,
  the fixture server's own API request log.

Statistics are derived from `raw` and can be recomputed independently.

## Determinism

Messages are generated by a seeded `mulberry32` PRNG with a fixed seed, and
stream frames are fixed strings. A rerun on the same host renders byte-identical
content, so a change in the numbers is a real change and not a different
conversation. The stream is paced by the fixture server's clock, so 50ms and
16ms framing are produced by a clock rather than by a loop the page controls.

## A note on frame pacing in headless Chromium

An idle page in this environment produces rAF deltas of ~16.7ms, so 60Hz is
achievable and a larger gap means main-thread blocking. The streaming scenario
records an explicit idle control (`idleFrameP50` / `idleFrameP95`) so streaming
frame numbers can be attributed to blocking rather than to the environment.
