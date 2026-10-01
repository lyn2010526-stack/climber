import { useEffect, useRef, useState } from 'react';
import { ClimberMark } from '../brand/ClimberMark';

export interface BootSplashProps {
  /** Fired once the splash has finished its fade-out. */
  onDone?: () => void;
}

/** The mark and the name hold the screen for at least this long. */
const DISPLAY_MS = 900;
/** The fade that hands the screen back. */
const EXIT_MS = 320;
/** Reduced motion: no held window, only a quick cross-fade. */
const REDUCED_DISPLAY_MS = 0;
const REDUCED_EXIT_MS = 120;

/**
 * Boot animation: the ClimberMark scales in, the brand name fades up behind
 * it, and an indeterminate accent bar sweeps at the bottom. The overlay covers
 * the screen above every dialog surface but never blocks the app content from
 * mounting underneath it, so the shell can render while the splash holds.
 *
 * Timing is driven from here instead of the stylesheet, because the global
 * reduced-motion rule collapses every CSS animation duration to 0.01ms — the
 * splash measures the media query itself so the display window still holds for
 * reduced-motion users, with only the fade shortened.
 *
 * Render it over the shell and pass `onDone`; unmount (or hide) the splash
 * when it fires.
 */
export function BootSplash({ onDone }: BootSplashProps) {
  const [leaving, setLeaving] = useState(false);
  const doneRef = useRef(false);
  // A ref keeps the timers stable even when the caller passes a fresh closure
  // each render: restarting the clock on every parent render would stretch the
  // display window unpredictably.
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  });

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const display = reduced ? REDUCED_DISPLAY_MS : DISPLAY_MS;
    const exit = reduced ? REDUCED_EXIT_MS : EXIT_MS;
    const leaveTimer = window.setTimeout(() => setLeaving(true), display);
    const doneTimer = window.setTimeout(() => {
      if (doneRef.current) return;
      doneRef.current = true;
      onDoneRef.current?.();
    }, display + exit);
    return () => {
      window.clearTimeout(leaveTimer);
      window.clearTimeout(doneTimer);
    };
  }, []);

  return (
    <div
      role="status"
      aria-label="Loading Climber"
      className={leaving ? 'boot-splash boot-splash-exit' : 'boot-splash'}
    >
      <span className="boot-splash-mark" aria-hidden="true">
        <ClimberMark size={56} color="var(--color-accent-foreground)" />
      </span>
      <span className="boot-splash-name">Climber</span>
      <span className="boot-splash-bar" aria-hidden="true" />
    </div>
  );
}

export default BootSplash;
