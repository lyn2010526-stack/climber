import { useCallback, useEffect, useRef, useState } from 'react';

/** Persisted user preference: the reading column spans the whole surface. */
export const MAXIMIZE_SPACE_KEY = 'climber.chat.maximizeSpace';

/**
 * Width changes animate, so a toggle reads as the same column growing rather
 * than as a different layout. Motion-sensitive users get the jump instead.
 */
const WIDTH_TRANSITION = 'transition-[max-width] duration-200 motion-reduce:transition-none';

export interface ReadingWidthOptions {
  /** User preference for a full-width column. Wins over every content tier. */
  fullWidth?: boolean;
  /** The row carries parallel or multi-branch tool output, which needs room. */
  hasParallelContent?: boolean;
}

/**
 * The reading column width, decided by content instead of a fixed constant.
 *
 * Three tiers: a full-width column on request, a wider one when a row carries
 * parallel tool output (side-by-side branches lose their comparison in a
 * narrow column), and the ordinary measure for prose. The transition travels
 * with the class so a message row and the composer can never disagree about it.
 */
export function getReadingWidthClass({
  fullWidth = false,
  hasParallelContent = false,
}: ReadingWidthOptions = {}): string {
  if (fullWidth) return `mx-auto w-full max-w-full ${WIDTH_TRANSITION}`;
  if (hasParallelContent) {
    return `mx-auto w-full md:max-w-[58rem] xl:max-w-[70rem] ${WIDTH_TRANSITION}`;
  }
  return `mx-auto w-full md:max-w-3xl xl:max-w-4xl ${WIDTH_TRANSITION}`;
}

/** More than one tool call on a turn means branches ran side by side. */
export function hasParallelToolContent(toolCallCount: number | undefined): boolean {
  return (toolCallCount ?? 0) > 1;
}

function readStoredFlag(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === 'true';
  } catch {
    return false;
  }
}

function persistFlag(key: string, value: boolean): void {
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // A blocked or full store costs the preference, never the render.
  }
}

/**
 * A boolean preference that survives a reload and defaults to off.
 *
 * The stored value is read once on mount, so the first paint already shows the
 * user's earlier choice, and it is written only when the value actually
 * changes: an untouched preference leaves the store alone. An unreadable store
 * falls back to the default rather than failing the render.
 */
export function useStoredFlag(key: string): [boolean, () => void] {
  const [enabled, setEnabled] = useState(() => readStoredFlag(key));
  const initial = useRef(enabled);
  const toggle = useCallback(() => setEnabled(prev => !prev), []);
  useEffect(() => {
    if (enabled === initial.current) return;
    persistFlag(key, enabled);
  }, [key, enabled]);
  return [enabled, toggle];
}

/** Full-width reading column, persisted, off by default. */
export function useMaximizeChatSpace(): [boolean, () => void] {
  return useStoredFlag(MAXIMIZE_SPACE_KEY);
}
