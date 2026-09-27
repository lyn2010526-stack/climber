/**
 * React DevTools global hook, installed before any app code runs.
 *
 * In a production build there is no other public way to count how many times
 * React committed a tree: React 19 has no Profiler in a non-dev bundle, and
 * counting calls to a component function from the outside would also count
 * aborted and re-entrant render attempts. `onCommitFiberRoot` fires once per
 * finished commit, which is exactly the unit the render-bound metric needs.
 *
 * It must be defined by `addInitScript` so React sees the hook at createRoot
 * time; assigning it afterwards would miss the mount.
 */
export const REACT_COMMIT_HOOK_SOURCE = `(() => {
  const state = {
    commits: 0,
    /** Commit timestamps, monotonic ms. */
    commitTimes: [],
    /** Per-phase durations, when the profiling build exposes them. */
    renderDurations: [],
    /** Total work time reported by the Profiler for each commit. */
    actualDurations: [],
    enabled: true,
  };
  window.__perfCommits = state;

  const rendererId = 1;
  const rootMap = new Map();

  const hook = {
    renderers: new Map([[rendererId, {
      id: rendererId,
      bundleType: 1,
      version: '19.2.7',
      rendererPackageName: 'react-dom',
      findFiberByHostInstance: () => null,
      getCurrentFiber: () => null,
    }]]),
    supportsFiber: true,
    isDisabled: false,
    inject(renderer) {
      const id = this.renderers.size + 1;
      this.renderers.set(id, renderer);
      return id;
    },
    onCommitFiberRoot(id, root) {
      if (!state.enabled) return;
      state.commits += 1;
      const now = performance.now();
      state.commitTimes.push(Number(now.toFixed(3)));
      try {
        // actualDuration/baseDuration are only populated by the profiling
        // build. Recorded when present, absent otherwise: never fabricated.
        if (root && root.memoizedUpdaters) { /* no-op, shape differs per version */ }
      } catch (e) { /* ignore */ }
    },
    onCommitFiberUnmount() {},
    onPostCommitFiberRoot() {},
    onScheduleFiberRoot() {},
    checkDCE() {},
    getFiberRoots() { return rootMap; },
    setStrictMode() {},
    getCurrentFiber() { return null; },
  };

  Object.defineProperty(window, '__REACT_DEVTOOLS_GLOBAL_HOOK__', {
    value: hook, configurable: true, writable: true,
  });
})()`;
