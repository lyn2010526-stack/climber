/**
 * The single timing table behind the entry experience.
 *
 * The splash is measured in JS (it owns the hand-off deadline) but staged in
 * CSS (each layer animates itself), so the two would drift apart the moment
 * anyone retuned one side. Every number the stylesheet uses is declared here
 * and `bootTiming.test.ts` fails if `index.css` disagrees, which keeps the
 * curve of the whole gesture editable from one place.
 */

export interface BootStage {
  /** Milliseconds after the splash mounts. */
  delay: number;
  /** Milliseconds the stage takes to settle. */
  duration: number;
  /** CSS timing function, written exactly as the stylesheet consumes it. */
  curve: string;
}

/** Outer windows. `enter` is the hold, `exit` is the reveal that follows it. */
export const BOOT_SPLASH_WINDOW = {
  /** First arrival in a tab: the full brand gesture. */
  first: { enter: 640, exit: 300 },
  /** A repeat arrival in the same tab: acknowledged, then out of the way. */
  quick: { enter: 180, exit: 160 },
  /** Reduced motion hands the screen back immediately. */
  reduced: { enter: 0, exit: 0 },
} as const;

/**
 * The first-arrival stages. Read as one gesture rather than six fades: the
 * halo blooms first so the frame is already lit, the mark lands on it with a
 * whisper of overshoot, the wordmark and rail follow a beat apart, and the
 * progress fill completes at 590ms — 50ms of stillness before the curtain
 * lifts, so nothing is still moving when the app is revealed.
 */
export const BOOT_STAGES = {
  halo: { delay: 0, duration: 640, curve: 'cubic-bezier(0.22, 1, 0.36, 1)' },
  mark: { delay: 40, duration: 420, curve: 'cubic-bezier(0.34, 1.56, 0.64, 1)' },
  name: { delay: 150, duration: 340, curve: 'cubic-bezier(0.16, 1, 0.3, 1)' },
  rail: { delay: 190, duration: 240, curve: 'var(--ease-ios)' },
  fill: { delay: 210, duration: 380, curve: 'cubic-bezier(0.22, 1, 0.36, 1)' },
  tagline: { delay: 300, duration: 260, curve: 'var(--ease-ios)' },
} as const satisfies Record<string, BootStage>;

export const BOOT_EXIT_CURVE = 'cubic-bezier(0.83, 0, 0.17, 1)';

/** The seam flare and the content fade share the reveal window. */
export const BOOT_EXIT_STAGES = {
  seam: { delay: 0, duration: 300, curve: 'cubic-bezier(0.16, 1, 0.3, 1)' },
  content: { delay: 0, duration: 160, curve: 'var(--ease-ios)' },
} as const satisfies Record<string, BootStage>;

/** Writes a stage as the `animation` shorthand fragment the stylesheet uses. */
export function stageTiming(stage: BootStage): string {
  return stage.delay === 0
    ? `${stage.duration}ms ${stage.curve}`
    : `${stage.duration}ms ${stage.delay}ms ${stage.curve}`;
}

/**
 * The workspace rails. Left → centre → right at a 100ms stagger, which sits in
 * the 80-120ms band where three arrivals still read as one sweep instead of a
 * queue. `total` is the class-drop deadline: it has to outlast the last rail
 * (200 + 460) so no rail is cut off mid-slide.
 */
export const WORKSPACE_ENTER_STAGES = {
  left: { delay: 0, duration: 460, curve: 'var(--ease-spring)' },
  center: { delay: 100, duration: 520, curve: 'var(--ease-spring)' },
  right: { delay: 200, duration: 460, curve: 'var(--ease-spring)' },
} as const satisfies Record<string, BootStage>;

export const WORKSPACE_ENTER_TOTAL_MS = 700;

/** Stagger between two consecutive rails. */
export function workspaceStagger(): number {
  return WORKSPACE_ENTER_STAGES.center.delay - WORKSPACE_ENTER_STAGES.left.delay;
}
