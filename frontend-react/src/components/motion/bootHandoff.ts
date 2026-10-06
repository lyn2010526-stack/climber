import { useEffect, useState } from 'react';

/**
 * The boot hand-off channel.
 *
 * The splash covers an app that is already mounted, so a hero or a workspace
 * that animates on mount spends its whole entrance behind an opaque curtain and
 * the reveal lands on a settled screen — the app looks like it popped in. This
 * channel is how the surfaces underneath learn when to start: the splash
 * announces `holding` while it owns the screen and `revealing` the frame the
 * curtain begins to lift, and the surfaces below time their first gesture to
 * that edge instead of to their own mount.
 *
 * `settled` stays for the rest of the SPA session, so anything mounted later
 * (a route change back to the dashboard) plays immediately instead of waiting
 * for a splash that has already gone.
 */
export type BootPhase = 'holding' | 'revealing' | 'settled';

/** Null until a boot surface announces itself: nothing has claimed the screen. */
let phase: BootPhase | null = null;
const listeners = new Set<(next: BootPhase | null) => void>();

export function readBootPhase(): BootPhase | null {
  return phase;
}

export function announceBootPhase(next: BootPhase): void {
  if (phase === next) return;
  phase = next;
  for (const listener of listeners) listener(next);
}

export function subscribeBootPhase(listener: (next: BootPhase | null) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Drops every listener. Test-only: the channel is module state. */
export function resetBootPhaseForTests(): void {
  phase = null;
  listeners.clear();
}

/**
 * How long a surface waits for a boot announcement before it gives up and plays
 * anyway. The splash announces in a layout effect, so a real boot always beats
 * this deadline; the fallback only covers a surface rendered with no splash
 * above it, which must never be held hostage by a curtain that is not coming.
 */
export const BOOT_REVEAL_FALLBACK_MS = 120;

function mayReveal(): boolean {
  return phase === 'revealing' || phase === 'settled';
}

/**
 * False while the splash still owns the screen, true from the frame the curtain
 * starts to lift. Callers keep their entrance in its opening state until this
 * flips, so the gesture is spent in view.
 */
export function useBootReveal(fallbackMs: number = BOOT_REVEAL_FALLBACK_MS): boolean {
  const [revealed, setRevealed] = useState(mayReveal);

  useEffect(() => {
    if (revealed) return;
    const release = () => {
      if (mayReveal()) setRevealed(true);
    };
    const unsubscribe = subscribeBootPhase(release);
    // A phase that moved between render and effect still has to be picked up.
    release();
    const guard =
      readBootPhase() === null ? window.setTimeout(() => setRevealed(true), fallbackMs) : 0;
    return () => {
      unsubscribe();
      if (guard) window.clearTimeout(guard);
    };
  }, [revealed, fallbackMs]);

  return revealed;
}
