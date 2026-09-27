/**
 * In-page instrumentation, serialised into the browser as a function body.
 *
 * This module is not imported by the app. It is handed to `page.evaluate` and
 * injected via `addInitScript` so the counters are in place before the first
 * frame of the scenario under test. Everything it records is a raw sample: no
 * aggregation happens here, so the report can re-derive statistics from the
 * same numbers.
 */

export const INSTRUMENT_SOURCE = `(() => {
  if (window.__perf) return;

  const state = {
    /** React commit count for the instrumented component subtree. */
    renderCount: 0,
    /** Samples of commit-to-commit wall time, in ms. */
    commitDurations: [],
    /** Monotonic ms since the recorder was installed. */
    startedAt: performance.now(),
    longTasks: [],
    frameIntervals: [],
    frameMarks: [],
    heap: [],
    domNodes: [],
    listenerCounts: {},
    phases: [],
  };
  window.__perf = state;

  // ---- React commit counter -------------------------------------------------
  // A commit is the unit a user feels. Counting renders of a leaf would also
  // count the render functions of siblings, so the counter is installed on the
  // transcript subtree root: one increment per commit of the message list.
  const origCreate = document.createElement.bind(document);
  const rrafTargets = new WeakSet();
  window.__perfHookRender = (label) => {
    state.renderCount += 1;
    if (state.commitDurations.length > 0) {
      const now = performance.now();
      state.commitDurations.push(Number((now - state.commitDurations[state.commitDurations.length - 1]).toFixed(3)));
    }
    if (label) state.phases.push({ label, at: Number(performance.now().toFixed(2)) });
  };
  void origCreate; void rrafTargets;

  // ---- Long tasks ------------------------------------------------------------
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        state.longTasks.push({
          start: Number(entry.startTime.toFixed(2)),
          duration: Number(entry.duration.toFixed(2)),
          name: entry.name,
        });
      }
    }).observe({ entryTypes: ['longtask'] });
  } catch (e) { state.longTaskUnsupported = String(e); }

  // ---- Frame pacing ---------------------------------------------------------
  // rAF deltas are the honest proxy for scroll smoothness: a frame that takes
  // longer than the display interval shows up here as a gap.
  let lastFrame = 0;
  const tick = (t) => {
    if (lastFrame > 0) {
      const delta = t - lastFrame;
      state.frameIntervals.push(Number(delta.toFixed(3)));
      state.frameMarks.push(Number(t.toFixed(2)));
    }
    lastFrame = t;
    state.rafId = requestAnimationFrame(tick);
  };
  state.rafId = requestAnimationFrame(tick);

  // ---- Listener accounting --------------------------------------------------
  // Wrapping add/removeEventListener is the only way to prove a leak from
  // outside React: a component that mounts repeatedly without a matching
  // remove shows up as a monotonically growing count per target+type.
  const counts = state.listenerCounts;
  const key = (target, type, capture) => {
    let name = 'unknown';
    try {
      if (target === window) name = 'window';
      else if (target === document) name = 'document';
      else if (target && target.tagName) name = 'dom:' + target.tagName.toLowerCase();
      else if (target && target.constructor && target.constructor.name) name = 'obj:' + target.constructor.name;
    } catch (e) { name = 'unreadable'; }
    return name + '|' + type + (capture ? '|capture' : '');
  };

  const wrapped = new WeakMap();
  const wrapTarget = (target) => {
    if (!target || wrapped.has(target)) return;
    const add = target.addEventListener;
    const remove = target.removeEventListener;
    if (typeof add !== 'function') return;
    try {
      target.addEventListener = function (type, listener, opts) {
        counts[key(target, type, !!(opts && opts.capture))] = (counts[key(target, type, !!(opts && opts.capture))] || 0) + 1;
        state.listenerTotal = state.listenerTotal || {};
        state.listenerTotal[key(target, type, !!(opts && opts.capture))] = (state.listenerTotal[key(target, type, !!(opts && opts.capture))] || 0) + 1;
        return add.call(this, type, listener, opts);
      };
      target.removeEventListener = function (type, listener, opts) {
        const k = key(target, type, !!(opts && opts.capture));
        if (counts[k]) counts[k] -= 1;
        if (state.listenerTotal[k]) state.listenerTotal[k] -= 1;
        return remove.call(this, type, listener, opts);
      };
      wrapped.set(target, true);
    } catch (e) { /* frozen host object: skip */ }
  };
  wrapTarget(window);
  wrapTarget(document);
  const origDocAdd = document.addEventListener;
  const origWinAdd = window.addEventListener;
  document.addEventListener = function (t, l, o) { wrapTarget(document); return origDocAdd.call(this, t, l, o); };
  window.addEventListener = function (t, l, o) { wrapTarget(window); return origWinAdd.call(this, t, l, o); };
  // Element listeners matter too: the chat composer and sidebar attach to nodes.
  const origElAdd = EventTarget.prototype.addEventListener;
  const origElRemove = EventTarget.prototype.removeEventListener;
  EventTarget.prototype.addEventListener = function (t, l, o) {
    wrapTarget(this);
    const k = key(this, t, !!(o && o.capture));
    counts[k] = (counts[k] || 0) + 1;
    state.listenerTotal = state.listenerTotal || {};
    state.listenerTotal[k] = (state.listenerTotal[k] || 0) + 1;
    return origElAdd.call(this, t, l, o);
  };
  EventTarget.prototype.removeEventListener = function (t, l, o) {
    const k = key(this, t, !!(o && o.capture));
    if (counts[k]) counts[k] -= 1;
    if (state.listenerTotal[k]) state.listenerTotal[k] -= 1;
    return origElRemove.call(this, t, l, o);
  };

  // ---- ResizeObserver / visualViewport --------------------------------------
  const RO = window.ResizeObserver;
  if (RO) {
    const OrigRO = RO;
    const PatchedRO = function (cb) {
      state.resizeObserversCreated = (state.resizeObserversCreated || 0) + 1;
      return new OrigRO(function (...args) {
        state.resizeObserverCallbacks = (state.resizeObserverCallbacks || 0) + 1;
        return cb.apply(this, args);
      });
    };
    PatchedRO.prototype = OrigRO.prototype;
    window.ResizeObserver = PatchedRO;
  }
  if (window.visualViewport) {
    const vv = window.visualViewport;
    state.visualViewportInitial = {
      width: vv.width, height: vv.height,
      offsetTop: vv.offsetTop, pageTop: vv.pageTop,
    };
  }

  // ---- Sampling helpers -----------------------------------------------------
  state.sample = function sample() {
    const mem = performance.memory ? {
      usedJSHeapSize: performance.memory.usedJSHeapSize,
      totalJSHeapSize: performance.memory.totalJSHeapSize,
      jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
    } : null;
    if (mem) state.heap.push({
      t: Number(performance.now().toFixed(2)),
      usedJSHeapSize: mem.usedJSHeapSize,
      totalJSHeapSize: mem.totalJSHeapSize,
    });
    const nodes = document.getElementsByTagName('*').length;
    state.domNodes.push({ t: Number(performance.now().toFixed(2)), nodes });
    return { mem, nodes };
  };

  state.resetCounters = function resetCounters() {
    state.renderCount = 0;
    state.commitDurations = [];
    state.longTasks = [];
    state.frameIntervals = [];
    state.frameMarks = [];
    state.phases = [];
  };

  state.stopRaf = function stopRaf() {
    if (state.rafId) cancelAnimationFrame(state.rafId);
    state.rafId = 0;
  };

  state.mark = function mark(label) {
    state.phases.push({ label, at: Number(performance.now().toFixed(2)) });
  };

  // One GC where the flag is available, so heap readings are comparable.
  state.forceGc = function forceGc() { return false; };

  return true;
})()`;
