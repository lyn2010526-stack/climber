import { describe, expect, it } from 'vitest';
import {
  availableSessionStatuses,
  buildSessionView,
  groupSessions,
  isSessionFilterActive,
  matchesSessionFilter,
  sessionGroupOf,
  type SessionFilter,
} from '../sessionGrouping';
import type { Session, SessionStatus } from '../../../store/workspace';

const DAY_MS = 24 * 60 * 60 * 1000;

/** A fixed clock, so the day boundaries the buckets cut on are the ones the test states. */
const NOW = new Date('2026-09-26T12:00:00Z').getTime();
const START_OF_TODAY = new Date('2026-09-26T00:00:00Z').getTime();

function session(id: string, overrides: Partial<Session> = {}): Session {
  return {
    id,
    title: `Session ${id}`,
    status: 'idle',
    messages: [],
    activeSkills: [],
    activeTools: [],
    createdAt: NOW,
    ...overrides,
  };
}

const noFilter: SessionFilter = { query: '', status: 'all' };

describe('sessionGroupOf', () => {
  it('buckets by the created_at the backend reported', () => {
    expect(sessionGroupOf(session('a', { createdAt: NOW }), NOW)).toBe('today');
    expect(sessionGroupOf(session('b', { createdAt: START_OF_TODAY }), NOW)).toBe('today');
    expect(sessionGroupOf(session('c', { createdAt: START_OF_TODAY - DAY_MS }), NOW)).toBe('recent');
    expect(sessionGroupOf(session('d', { createdAt: START_OF_TODAY - 6 * DAY_MS }), NOW)).toBe('recent');
    expect(sessionGroupOf(session('e', { createdAt: START_OF_TODAY - 7 * DAY_MS }), NOW)).toBe('earlier');
    expect(sessionGroupOf(session('f', { createdAt: 0 }), NOW)).toBe('earlier');
  });

  it('gives a timestamp the backend never sent its own bucket', () => {
    // "Today" would claim a recency that was not reported, and "earlier" would
    // claim the opposite, so an unusable timestamp is reported as unusable.
    expect(sessionGroupOf(session('a', { createdAt: Number.NaN }), NOW)).toBe('unreported');
    expect(sessionGroupOf(session('b', { createdAt: Number.POSITIVE_INFINITY }), NOW)).toBe('unreported');
    expect(sessionGroupOf(session('c', { createdAt: undefined as unknown as number }), NOW)).toBe('unreported');
  });

  it('uses the backend timeline when the store session has a local fallback', () => {
    const local = session('local', { createdAt: NOW });
    const timeline = new Map([['local', { createdAt: null, updatedAt: NOW }]]);

    expect(sessionGroupOf(local, NOW, timeline)).toBe('unreported');
    expect(buildSessionView([local], noFilter, NOW, timeline).groups[0]?.id).toBe('unreported');
  });
});

describe('groupSessions', () => {
  it('returns groups in reading order, each with its own rows', () => {
    const groups = groupSessions([
      session('old', { createdAt: 0 }),
      session('now'),
      session('week', { createdAt: START_OF_TODAY - 2 * DAY_MS }),
    ], NOW);

    expect(groups.map((group) => group.id)).toEqual(['today', 'recent', 'earlier']);
    expect(groups.map((group) => group.sessions.map((s) => s.id))).toEqual([
      ['now'], ['week'], ['old'],
    ]);
  });

  it('drops a group with no rows rather than rendering a header over nothing', () => {
    // A header standing over zero rows is the shape that made a whole page of
    // sessions unreachable in the reference implementation.
    const groups = groupSessions([session('now'), session('also-now', { createdAt: START_OF_TODAY })], NOW);

    expect(groups).toHaveLength(1);
    expect(groups[0]!.id).toBe('today');
    expect(groups[0]!.sessions).toHaveLength(2);
  });

  it('reports the creation time it could not read', () => {
    const groups = groupSessions([session('broken', { createdAt: Number.NaN })], NOW);

    expect(groups.map((group) => group.id)).toEqual(['unreported']);
    expect(groups[0]!.label).toBe('创建时间未上报');
  });
});

describe('session filtering', () => {
  const sessions = [
    session('alpha', { title: 'Alpha report', status: 'running' }),
    session('beta', { title: 'Beta notes', status: 'idle' }),
    session('gamma', { title: null, status: 'running' }),
  ];

  it('matches the title case-insensitively and treats a blank query as no query', () => {
    expect(isSessionFilterActive({ query: '  ', status: 'all' })).toBe(false);
    expect(matchesSessionFilter(sessions[0]!, { query: 'ALPHA', status: 'all' })).toBe(true);
    expect(matchesSessionFilter(sessions[0]!, { query: 'gamma', status: 'all' })).toBe(false);
    // An untitled session has no title to match, so a text query excludes it
    // rather than matching the empty string.
    expect(matchesSessionFilter(sessions[2]!, { query: 'a', status: 'all' })).toBe(false);
  });

  it('filters on the status the backend reported', () => {
    expect(sessions.filter((s) => matchesSessionFilter(s, { query: '', status: 'running' })).map((s) => s.id))
      .toEqual(['alpha', 'gamma']);
  });

  it('offers only the statuses the loaded list actually carries', () => {
    // Offering a bucket the backend never reported would let the reader filter
    // into a permanently empty list.
    expect(availableSessionStatuses(sessions)).toEqual(['idle', 'running']);
  });

  it('keeps an active filter active even when it excludes everything', () => {
    const view = buildSessionView(sessions, { query: 'nothing matches', status: 'all' }, NOW);

    expect(view.groups).toHaveLength(0);
    expect(view.visible).toHaveLength(0);
    expect(isSessionFilterActive({ query: 'nothing matches', status: 'all' })).toBe(true);
  });

  it('flattens the groups in reading order and records each row its group', () => {
    const view = buildSessionView([
      session('old', { createdAt: 0 }),
      session('now'),
      session('week', { createdAt: START_OF_TODAY - DAY_MS }),
    ], noFilter, NOW);

    expect(view.visible.map((s) => s.id)).toEqual(['now', 'week', 'old']);
    expect(view.groupOf.get('now')).toBe('today');
    expect(view.groupOf.get('week')).toBe('recent');
    expect(view.groupOf.get('old')).toBe('earlier');
  });

  it('reads a status the store has not normalised through the filter', () => {
    const unknown = session('odd', { status: 'unknown' as SessionStatus });
    const view = buildSessionView([unknown], { query: '', status: 'unknown' }, NOW);

    expect(view.visible.map((s) => s.id)).toEqual(['odd']);
  });
});
