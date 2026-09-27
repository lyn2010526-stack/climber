import { SESSION_STATUSES, type Session, type SessionStatus } from '../../store/workspace';

/**
 * Session grouping and filtering, derived only from fields the backend actually
 * reports.
 *
 * `SessionOut` (app/api/v1/sessions.py) carries `id`, `title`, `status`,
 * `created_at`, `updated_at`, `provider` and `model_id`. It carries no `pinned`
 * and no `archived`, so this module groups by `created_at` and filters by
 * `title` and `status`. Adding a pin rail or an archive view would require
 * fields the API does not have.
 */

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * How far back the second bucket reaches. Combined with `today` this covers
 * exactly seven calendar dates: today plus the six dates before it, so a
 * timestamp sitting exactly on the boundary belongs to `earlier`.
 */
const RECENT_WINDOW_DAYS = 7;

export type SessionGroupId = 'today' | 'recent' | 'earlier' | 'unreported';

export interface SessionGroup {
  id: SessionGroupId;
  label: string;
  sessions: Session[];
}

export interface SessionTimeline {
  createdAt: number | null;
  updatedAt: number | null;
}

export type SessionTimelineMap = ReadonlyMap<string, SessionTimeline>;

function timelineCreatedAt(session: Session, timeline?: SessionTimelineMap): number | null {
  const reported = timeline?.get(session.id);
  if (reported) return reported.createdAt;
  return session.createdAt;
}

/** Declaration order, which is also the reading order of the sidebar. */
const GROUP_ORDER: readonly SessionGroupId[] = ['today', 'recent', 'earlier', 'unreported'];

const GROUP_LABELS: Record<SessionGroupId, string> = {
  today: '今天',
  recent: `最近 ${RECENT_WINDOW_DAYS} 天`,
  earlier: '更早',
  unreported: '创建时间未上报',
};

/**
 * Bucket a session by the `created_at` the store parsed. A timestamp that is
 * not a finite number gets its own bucket: filing it under "today" would claim
 * a recency the backend never reported, and filing it under "earlier" would
 * claim the opposite.
 */
export function sessionGroupOf(
  session: Session,
  now: number,
  timeline?: SessionTimelineMap,
): SessionGroupId {
  const createdAt = timelineCreatedAt(session, timeline);
  if (typeof createdAt !== 'number' || !Number.isFinite(createdAt)) return 'unreported';
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  const dayStart = startOfToday.getTime();
  if (createdAt >= dayStart) return 'today';
  if (createdAt > dayStart - RECENT_WINDOW_DAYS * DAY_MS) return 'recent';
  return 'earlier';
}

/**
 * Bucket sessions into their date groups.
 *
 * A group with no rows is dropped rather than rendered. A header standing over
 * zero rows is the shape that made whole pages of sessions unreachable in the
 * reference implementation, where an all-pinned page left the virtual list with
 * no rows at all and its paging callback never fired.
 */
export function groupSessions(
  sessions: readonly Session[],
  now: number,
  timeline?: SessionTimelineMap,
): SessionGroup[] {
  const buckets = new Map<SessionGroupId, Session[]>();
  for (const session of sessions) {
    const id = sessionGroupOf(session, now, timeline);
    const bucket = buckets.get(id);
    if (bucket) bucket.push(session);
    else buckets.set(id, [session]);
  }
  return GROUP_ORDER
    .filter((id) => (buckets.get(id)?.length ?? 0) > 0)
    .map((id) => ({ id, label: GROUP_LABELS[id], sessions: buckets.get(id)! }));
}

export interface SessionFilter {
  /** Matched case-insensitively against the title. */
  query: string;
  /** `status` as `SessionOut` reports it, already normalised by the store. */
  status: SessionStatus | 'all';
}

export const EMPTY_SESSION_FILTER: SessionFilter = { query: '', status: 'all' };

export function isSessionFilterActive(filter: SessionFilter): boolean {
  return filter.query.trim() !== '' || filter.status !== 'all';
}

export function matchesSessionFilter(session: Session, filter: SessionFilter): boolean {
  if (filter.status !== 'all' && session.status !== filter.status) return false;
  const query = filter.query.trim().toLowerCase();
  if (query === '') return true;
  return (session.title ?? '').toLowerCase().includes(query);
}

export function applySessionFilter(sessions: readonly Session[], filter: SessionFilter): Session[] {
  if (!isSessionFilterActive(filter)) return [...sessions];
  return sessions.filter((session) => matchesSessionFilter(session, filter));
}

/**
 * Statuses worth offering in the filter: only those the loaded list actually
 * carries, in lifecycle order, so the control cannot offer a bucket the backend
 * has never reported.
 */
export function availableSessionStatuses(sessions: readonly Session[]): SessionStatus[] {
  const present = new Set(sessions.map((session) => session.status));
  return SESSION_STATUSES.filter((status) => present.has(status));
}

export interface SessionView {
  groups: SessionGroup[];
  /** Groups flattened in reading order; the order the arrow keys walk. */
  visible: Session[];
  /** Session id to its group, for handing focus to a group header. */
  groupOf: Map<string, SessionGroupId>;
}

export function buildSessionView(
  sessions: readonly Session[],
  filter: SessionFilter,
  now: number,
  timeline?: SessionTimelineMap,
): SessionView {
  const groups = groupSessions(applySessionFilter(sessions, filter), now, timeline);
  const groupOf = new Map<string, SessionGroupId>();
  for (const group of groups) {
    for (const session of group.sessions) groupOf.set(session.id, group.id);
  }
  return { groups, visible: groups.flatMap((group) => group.sessions), groupOf };
}
