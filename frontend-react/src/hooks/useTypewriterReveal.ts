import { useCallback, useEffect, useRef, useState } from 'react';

export type TypewriterPreset = 'realtime' | 'balanced' | 'silky';

export interface TypewriterPresetConfig {
  readonly charsPerSecond: number;
}

/** Steady reveal cadence presets, ported from the reference Codex teleprompter. */
export const TYPEWRITER_PRESETS: Record<TypewriterPreset, TypewriterPresetConfig> = {
  realtime: { charsPerSecond: 120 },
  balanced: { charsPerSecond: 80 },
  silky: { charsPerSecond: 64 },
};

/** Default frame budget when the browser rAF timestamp is absent or zeroed (tests). */
export const DEFAULT_FRAME_MS = 16;

const graphemeSegmenter = typeof Intl.Segmenter === 'function'
  ? new Intl.Segmenter(undefined, { granularity: 'grapheme' })
  : undefined;

/** Split text into user-perceived characters without tearing emoji or combining marks. */
export function splitGraphemes(text: string): string[] {
  if (graphemeSegmenter === undefined) return [...text];
  return [...graphemeSegmenter.segment(text)].map(item => item.segment);
}

/** Counts user-perceived characters, not UTF-16 units or Unicode code points. */
export const countChars = (text: string): number => splitGraphemes(text).length;

/**
 * Pure per-frame reveal decision: at least one grapheme per frame while a backlog
 * exists, bounded by the steady chars-per-second rate. Shared by the frame loop
 * and its unit tests.
 */
export function computeTypewriterStep(backlogChars: number, charsPerSecond: number, dtMs: number): number {
  if (backlogChars <= 0 || charsPerSecond <= 0 || dtMs <= 0) return 0;
  return Math.min(backlogChars, Math.max(1, Math.round((charsPerSecond * dtMs) / 1000)));
}

export interface UseTypewriterRevealOptions {
  /** True while the reply is still streaming; turning false flushes the full text. */
  active: boolean;
  /** Steady reveal cadence. */
  preset?: TypewriterPreset;
  /** Master switch; while false the content is always shown in full. */
  enabled?: boolean;
  /** Explicit reduced-motion override; falls back to the media query when omitted. */
  reducedMotion?: boolean;
}

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';

function subscribeReducedMotion(listener: () => void): () => void {
  const query = window.matchMedia?.(REDUCED_MOTION);
  query?.addEventListener('change', listener);
  return () => {
    query?.removeEventListener('change', listener);
  };
}

function readReducedMotion(): boolean {
  return window.matchMedia?.(REDUCED_MOTION).matches === true;
}

/**
 * Reveal a chunked content stream at a steady characters-per-second cadence.
 *
 * While `active` the reply types onto the screen from the accumulated input;
 * the moment streaming stops (done, interrupted, or error) the snapshot is
 * authoritative and the full text appears immediately. The reveal queue also
 * drains fully once the backlog empties, so a settled reply never trails.
 */
export function useTypewriterReveal(
  content: string,
  { active, preset = 'balanced', enabled = true, reducedMotion }: UseTypewriterRevealOptions = { active: false },
): string {
  const cps = TYPEWRITER_PRESETS[preset].charsPerSecond;
  const [displayed, setDisplayed] = useState(content);
  const displayedRef = useRef(displayed);
  const targetRef = useRef(content);
  const targetCharsRef = useRef(splitGraphemes(content));
  const shownCountRef = useRef(countChars(content));
  const rafRef = useRef<number | null>(null);
  const lastFrameRef = useRef<number | null>(null);
  const [reduced, setReduced] = useState(readReducedMotion);

  useEffect(() => {
    setReduced(readReducedMotion());
    return subscribeReducedMotion(() => setReduced(readReducedMotion()));
  }, []);

  const syncImmediate = useCallback((next: string) => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    lastFrameRef.current = null;
    targetRef.current = next;
    targetCharsRef.current = splitGraphemes(next);
    shownCountRef.current = countChars(next);
    if (displayedRef.current !== next) {
      displayedRef.current = next;
      setDisplayed(next);
    }
  }, []);

  const revealEnabled = enabled && active && !(reducedMotion ?? reduced);

  useEffect(() => {
    if (!revealEnabled) {
      // 揭示关闭时 content 即权威：只同步内部 ref（供将来开启时从正确位置继续），
      // 不 setDisplayed —— 否则 displayed 沦为 content 的镜像，每个流式分片都会
      // 多产生一次冗余 commit（任务48：commit 数须低于 chunks/4）。
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      lastFrameRef.current = null;
      targetRef.current = content;
      targetCharsRef.current = splitGraphemes(content);
      shownCountRef.current = countChars(content);
      displayedRef.current = content;
      return;
    }
    const target = targetRef.current;
    if (content === target) return;
    if (!content.startsWith(target)) {
      syncImmediate(content);
      return;
    }
    targetRef.current = content;
    targetCharsRef.current = [...targetCharsRef.current, ...splitGraphemes(content.slice(target.length))];
    if (rafRef.current !== null) return;

    const tick = (frameTs: number) => {
      const now = frameTs;
      const dtMs = lastFrameRef.current === null ? DEFAULT_FRAME_MS : Math.max(1, now - lastFrameRef.current);
      lastFrameRef.current = now;
      const backlog = targetCharsRef.current.length - shownCountRef.current;
      if (backlog <= 0) {
        lastFrameRef.current = null;
        rafRef.current = null;
        const full = targetRef.current;
        if (displayedRef.current !== full) {
          displayedRef.current = full;
          shownCountRef.current = targetCharsRef.current.length;
          setDisplayed(full);
        }
        return;
      }
      const step = computeTypewriterStep(backlog, cps, dtMs);
      const from = shownCountRef.current;
      const segment = targetCharsRef.current.slice(from, from + step).join('');
      if (segment) {
        shownCountRef.current = from + countChars(segment);
        const next = displayedRef.current + segment;
        displayedRef.current = next;
        setDisplayed(next);
      } else {
        const full = targetRef.current;
        displayedRef.current = full;
        shownCountRef.current = targetCharsRef.current.length;
        setDisplayed(full);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [content, revealEnabled, cps, syncImmediate]);

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // 揭示关闭时直接返回 content（无镜像 state、无多余 commit）；开启时返回逐字揭示的 displayed。
  return revealEnabled ? displayed : content;
}
