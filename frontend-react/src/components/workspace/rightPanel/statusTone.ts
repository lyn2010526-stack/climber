import type { TFunction } from '../../../i18n';
import type { Session } from '../../../store/workspace';

/**
 * Session status presentation, in two independent parts that always agree:
 * this module maps a status to a tone and to the locale key that names it, and
 * every surface that shows a session status resolves both through here. A
 * reader can tell a paused run from a failed one by colour, and reads the same
 * word for the same state wherever it appears.
 */
export type StatusTone = 'idle' | 'info' | 'warning' | 'success' | 'error' | 'unknown';

export const RUN_STATUS_TONE: Record<Session['status'], StatusTone> = {
  pending: 'idle',
  idle: 'idle',
  running: 'info',
  paused: 'warning',
  completed: 'success',
  failed: 'error',
  stopped: 'idle',
  // A status the backend never declared. It keeps its own tone so a reader can
  // tell "nothing is happening" from "this value is unreported".
  unknown: 'unknown',
};

const SOLID: Record<StatusTone, string> = {
  idle: 'bg-[var(--color-text-muted)]',
  info: 'bg-[var(--color-info)]',
  warning: 'bg-[var(--color-warning)]',
  success: 'bg-[var(--color-success)]',
  error: 'bg-[var(--color-error)]',
  unknown: 'bg-[var(--color-unknown)]',
};

const TEXT: Record<StatusTone, string> = {
  idle: 'text-[var(--color-text-muted)]',
  info: 'text-[var(--color-info)]',
  warning: 'text-[var(--color-warning)]',
  success: 'text-[var(--color-success)]',
  error: 'text-[var(--color-error)]',
  unknown: 'text-[var(--color-unknown)]',
};

/** Ring plus fill for timeline markers: unknown states read as an empty ring. */
const RING: Record<StatusTone, string> = {
  idle: 'border-[var(--color-border-strong)]',
  info: 'border-[var(--color-info)] bg-[var(--color-info)]',
  warning: 'border-[var(--color-warning)] bg-[var(--color-warning)]',
  success: 'border-[var(--color-success)] bg-[var(--color-success)]',
  error: 'border-[var(--color-error)] bg-[var(--color-error)]',
  unknown: 'border-[var(--color-unknown)] bg-[var(--color-unknown)]',
};

export const solidTone = (tone: StatusTone) => SOLID[tone];
export const textTone = (tone: StatusTone) => TEXT[tone];
export const ringTone = (tone: StatusTone) => RING[tone];

/**
 * The single label source for a session status. `right_panel.status.*` covers
 * every value in `SessionStatus`; the raw status is passed as the default so a
 * status a future backend adds stays visible instead of rendering a key.
 */
export function sessionStatusLabel(status: Session['status'], t: TFunction): string {
  return t(`right_panel.status.${status}`, status);
}

/**
 * Backend status vocabularies differ per source, so a plan node or trace step
 * is only toned when its own payload names a state we recognise. Anything else
 * keeps the neutral tone instead of being guessed into a colour.
 */
const NODE_TONE: Record<string, StatusTone> = {
  completed: 'success',
  succeeded: 'success',
  success: 'success',
  running: 'info',
  in_progress: 'info',
  pending: 'idle',
  queued: 'idle',
  paused: 'warning',
  failed: 'error',
  error: 'error',
};

export function toneForNodeStatus(status: string): StatusTone {
  return NODE_TONE[status.trim().toLowerCase()] ?? 'idle';
}
