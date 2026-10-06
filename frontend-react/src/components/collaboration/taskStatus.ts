import type { TFunction } from '../../i18n';

/**
 * The status vocabulary reported by the backend, transcribed from the server sources:
 * The task API response currently reports pending, running, completed, failed, or
 * cancelled. Missing and unknown values remain explicitly unreported.
 *
 * Labels live in the locale bundles, so this module owns the status -> key mapping
 * and every surface resolves the same word for the same state.
 */

export const NOT_REPORTED_KEY = 'collaboration.not_reported';

/** Task lifecycle states, mapped to the key that renders them. */
export const TASK_STATUS_LABEL_KEYS: Record<string, string> = {
  pending: 'collaboration.task_status.pending',
  paused: 'collaboration.task_status.paused',
  running: 'collaboration.task_status.running',
  completed: 'collaboration.task_status.completed',
  failed: 'collaboration.task_status.failed',
  cancelled: 'collaboration.task_status.cancelled',
  claimed: 'collaboration.task_status.claimed',
  ready: 'collaboration.task_status.ready',
};

/** Group lifecycle states, mapped to the key that renders them. */
export const GROUP_STATUS_LABEL_KEYS: Record<string, string> = {
  active: 'collaboration.group_status.active',
};

/**
 * One palette for both task surfaces, so a history row and a monitor row
 * read the same colour for the same state. Unknown states stay neutral rather
 * than being guessed into a colour.
 */
export const TASK_STATUS_COLORS: Record<string, string> = {
  pending: 'text-[var(--color-text-muted)]',
  paused: 'text-[var(--color-text-muted)]',
  running: 'text-[var(--color-accent-foreground)]',
  completed: 'text-[var(--color-success)]',
  failed: 'text-[var(--color-error)]',
  cancelled: 'text-[var(--color-text-muted)]',
  claimed: 'text-[var(--color-accent)]',
  ready: 'text-[var(--color-accent-foreground)]',
};

const TASK_TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

export function isTerminalTaskStatus(status: string | undefined | null): boolean {
  return !!status && TASK_TERMINAL_STATUSES.includes(status);
}

const SUBTASK_ACTIVE_STATUSES = ['pending', 'claimed'];
const SUBTASK_TERMINAL_STATUSES = ['completed', 'failed'];

export function isActiveSubtaskStatus(status: string | undefined | null): boolean {
  return !!status && SUBTASK_ACTIVE_STATUSES.includes(status);
}

export function isTerminalSubtaskStatus(status: string | undefined | null): boolean {
  return !!status && SUBTASK_TERMINAL_STATUSES.includes(status);
}

/**
 * The single answer to "is this task still running?". Callers that also require
 * a task to exist add that check themselves, because a freshly opened group has
 * no task yet and must not read as active.
 */
export function isActiveTaskStatus(status: string | undefined | null): boolean {
  return status === 'pending' || status === 'running';
}

export function taskStatusLabel(status: string | undefined | null, t: TFunction): string {
  if (!status) return t(NOT_REPORTED_KEY);
  const key = TASK_STATUS_LABEL_KEYS[status];
  return key ? t(key) : t(NOT_REPORTED_KEY);
}

export function groupStatusLabel(status: string | undefined | null, t: TFunction): string {
  if (!status) return t(NOT_REPORTED_KEY);
  const key = GROUP_STATUS_LABEL_KEYS[status];
  return key ? t(key) : t(NOT_REPORTED_KEY);
}

export function taskStatusColor(status: string | undefined | null): string {
  return (status && TASK_STATUS_COLORS[status]) || 'text-[var(--color-text-muted)]';
}

/** Formats a number the backend actually sent, including zero. */
export function reportedNumber(value: number | undefined | null, t: TFunction): string {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : t(NOT_REPORTED_KEY);
}
