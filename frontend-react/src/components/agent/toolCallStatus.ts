import type { ElementType } from 'react';
import { TONE_GLYPH, TONE_TEXT } from '../ui/StatusIcon';
import type { StatusTone } from '../../lib/icons';
import type { TFunction } from '../../i18n';

/**
 * Canonical tool-call lifecycle. Every surface that renders a tool call
 * (chat stream, trace tree) resolves its backend status through
 * {@link normalizeToolStatus} and renders icon + wording from
 * {@link resolveToolStatus} so the same state never reads two ways.
 *
 * The state is named for what happened; the tone is the shared eight-tone
 * vocabulary from `components/ui/StatusIcon`, and the two are separate on
 * purpose. Three of the states are not outcomes at all: `cancelled` is a run
 * the user stopped, `awaiting_approval` is a call parked on a human decision,
 * and `unknown` covers statuses this build does not recognise, so an
 * unrecognised value reads as "not reported" instead of "still waiting".
 *
 * `cancelled` takes `info` and never `error`: a stopped run is not a failure,
 * and colouring it red would report a fault that never happened. `unknown`
 * takes the `unknown` tone, which is a distinct role from `queued` for exactly
 * this reason: a missing value must not read as a healthy one or as a
 * scheduled one.
 */
export type ToolCallStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'error'
  | 'cancelled'
  | 'awaiting_approval'
  | 'unknown';

export interface ToolStatusDescriptor {
  /** The status role, resolved to a glyph and a colour by `StatusIcon`. */
  tone: StatusTone;
  /**
   * The drawing for the state, read out of the same table `StatusIcon` uses,
   * so a caller that still draws the icon itself cannot pick a second glyph or
   * a second colour for a state another surface already resolved.
   */
  icon: ElementType;
  /** Text colour for the wording, so label and glyph never diverge. */
  className: string;
  label: string;
  spin: boolean;
  /**
   * The one state that is still moving. A running badge breathes while it
   * waits; every settled state reports its outcome without animation.
   */
  pulse: boolean;
}

interface StatusMeta {
  tone: StatusTone;
  labelKey: string;
  spin: boolean;
  pulse: boolean;
}

const STATUS_META: Record<ToolCallStatus, StatusMeta> = {
  pending: { tone: 'queued', labelKey: 'tool_call.status_pending', spin: false, pulse: false },
  running: { tone: 'loading', labelKey: 'tool_call.status_running', spin: true, pulse: true },
  success: { tone: 'success', labelKey: 'tool_call.status_success', spin: false, pulse: false },
  error: { tone: 'error', labelKey: 'tool_call.status_error', spin: false, pulse: false },
  cancelled: { tone: 'info', labelKey: 'tool_call.status_cancelled', spin: false, pulse: false },
  awaiting_approval: { tone: 'approval', labelKey: 'tool_call.status_awaiting_approval', spin: false, pulse: false },
  unknown: { tone: 'unknown', labelKey: 'tool_call.status_unknown', spin: false, pulse: false },
};

const STATUS_ALIASES: Record<string, ToolCallStatus> = {
  pending: 'pending',
  queued: 'pending',
  created: 'pending',
  running: 'running',
  in_progress: 'running',
  started: 'running',
  streaming: 'running',
  success: 'success',
  completed: 'success',
  done: 'success',
  ok: 'success',
  error: 'error',
  failed: 'error',
  failure: 'error',
  timeout: 'error',
  cancelled: 'cancelled',
  canceled: 'cancelled',
  aborted: 'cancelled',
  stopped: 'cancelled',
  // A call that is waiting on a person is its own state, not a pending one:
  // the only thing that unblocks it is a decision, never the queue.
  awaiting_approval: 'awaiting_approval',
  approval_required: 'awaiting_approval',
  requires_approval: 'awaiting_approval',
  permission_required: 'awaiting_approval',
};

/**
 * Map any backend or partial status string onto the canonical lifecycle. A
 * missing or unrecognised value resolves to `unknown`, which every surface
 * labels as "not reported" instead of claiming the call is still waiting.
 */
export function normalizeToolStatus(status: string | boolean | null | undefined): ToolCallStatus {
  if (typeof status === 'boolean') return status ? 'success' : 'error';
  const mapped = STATUS_ALIASES[(status ?? '').trim().toLowerCase()];
  return mapped ?? 'unknown';
}

/**
 * The state, resolved. `tone` is the contract: rendering it through
 * `StatusIcon` is what puts the shared glyph and the shared colour on every
 * surface at once.
 */
export function resolveToolStatus(status: ToolCallStatus, t: TFunction): ToolStatusDescriptor {
  const meta = STATUS_META[status];
  return {
    tone: meta.tone,
    icon: TONE_GLYPH[meta.tone],
    className: TONE_TEXT[meta.tone],
    label: t(meta.labelKey),
    spin: meta.spin,
    pulse: meta.pulse,
  };
}

/** The four states a call settles through, in the order a tally reads them. */
export const PRIMARY_TOOL_STATES = ['running', 'pending', 'success', 'error'] as const satisfies readonly ToolCallStatus[];

type StatusCarrier = { status: string | boolean | null | undefined };

/**
 * One tally per canonical state, read off the normalized status. A value this
 * build does not recognise is counted under `unknown`, so an unrecognised
 * wire value is never tallied as a healthy one.
 */
export function countToolStatuses(calls: readonly StatusCarrier[]): Record<ToolCallStatus, number> {
  const counts = Object.fromEntries(
    (Object.keys(STATUS_META) as ToolCallStatus[]).map(state => [state, 0]),
  ) as Record<ToolCallStatus, number>;
  for (const call of calls) {
    counts[normalizeToolStatus(call.status)] += 1;
  }
  return counts;
}

/**
 * The tally line as data: one entry per non-empty state, in the order a
 * reader scans them. The glyph and its tone say which state, the number says
 * how many, and the full phrase travels in `label` so it reaches a screen
 * reader and a hover without repeating the wording on every card below.
 */
export function buildToolStatusSummary(
  counts: Record<ToolCallStatus, number>,
  t: TFunction,
): { tone: StatusTone; count: number; label: string }[] {
  const summary: { tone: StatusTone; count: number; label: string }[] = [];
  for (const state of PRIMARY_TOOL_STATES) {
    if (counts[state] === 0) continue;
    const resolved = resolveToolStatus(state, t);
    if (state === 'running') {
      summary.push({ tone: resolved.tone, count: counts[state], label: t('tool_call.running_count', { count: counts[state] }) });
      continue;
    }
    summary.push({ tone: resolved.tone, count: counts[state], label: resolved.label });
  }
  return summary;
}

/** Collapse a JSON payload for display without dropping any of it. */
export function stringifyPayload(value: unknown): string {
  try {
    const text = JSON.stringify(value, null, 2);
    return text === undefined ? String(value) : text;
  } catch {
    return String(value);
  }
}
