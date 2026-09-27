import { useCallback, useEffect, useMemo, useState } from 'react';
import type { RightPanelTab } from '../../../store/types';
import {
  TAB_TO_GROUP,
  groupById,
  isAvailableTab,
  isGroupAvailable,
  type RightPanelGroupId,
} from './groupModel';

/** One storage entry holds every context, so the key stays stable forever. */
export const INSPECTOR_LAYOUT_STORAGE_KEY = 'climber.rightPanel.layout';

export interface InspectorLayout {
  /** The one group allowed to be expanded, or null when the user collapsed all. */
  openGroup: RightPanelGroupId | null;
  /** Last section the user picked inside a multi-section group. */
  selected: Partial<Record<RightPanelGroupId, RightPanelTab>>;
}

type LayoutRecord = Record<string, InspectorLayout>;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * The layout belongs to the conversation it was arranged in: two sessions of
 * the same agent keep their own expanded group and their own selected tab.
 * A context without a session is still an addressable context — the panel is
 * reachable before one is picked — so it gets its own key.
 */
export function layoutContextKey(sessionId: string | null): string {
  return sessionId ? `session:${sessionId}` : 'session:none';
}

function readLayouts(): LayoutRecord {
  try {
    const raw = localStorage.getItem(INSPECTOR_LAYOUT_STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (!isRecord(parsed)) return {};
    const entries = Object.entries(parsed).filter(
      ([, entry]) => isRecord(entry) && ('openGroup' in entry || 'selected' in entry),
    );
    return Object.fromEntries(entries) as LayoutRecord;
  } catch {
    // Storage unavailable or holding something else: start from the defaults.
    return {};
  }
}

function writeLayouts(layouts: LayoutRecord): void {
  try {
    localStorage.setItem(INSPECTOR_LAYOUT_STORAGE_KEY, JSON.stringify(layouts));
  } catch {
    // A refused write (private mode, quota) costs persistence, never the panel.
  }
}

/**
 * Drop whatever the current capability set no longer supports. A layout written
 * before a group lost its session-independent section, or before a tab was
 * renamed, is pruned here instead of resurrecting a dead entry on every read.
 */
export function pruneLayout(layout: unknown, hasSession: boolean): InspectorLayout {
  const pruned: InspectorLayout = { openGroup: null, selected: {} };
  if (!isRecord(layout)) return pruned;
  for (const [id, tab] of Object.entries(isRecord(layout.selected) ? layout.selected : {})) {
    const group = groupById(id);
    if (group && isGroupAvailable(group, hasSession) && isAvailableTab(tab, group)) {
      pruned.selected[group.id] = tab as RightPanelTab;
    }
  }
  const openGroup = groupById(layout.openGroup);
  if (openGroup && isGroupAvailable(openGroup, hasSession)) pruned.openGroup = openGroup.id;
  return pruned;
}

const sameLayout = (a: InspectorLayout, b: InspectorLayout): boolean =>
  a.openGroup === b.openGroup &&
  JSON.stringify(a.selected) === JSON.stringify(b.selected);

/**
 * Expansion and selection survive a reload, scoped to the active session.
 *
 * The record holds one entry per context and the current entry is *derived* from
 * it, so switching sessions re-reads that conversation's arrangement instead of
 * writing the new one over the old. Capability availability and open state stay
 * separate concerns: the entry says which group the user arranged, `pruneLayout`
 * says which of those groups the current session can still serve.
 */
export function useInspectorLayout(
  sessionId: string | null,
  hasSession: boolean,
  fallbackGroup: RightPanelGroupId,
): [InspectorLayout, (next: (previous: InspectorLayout) => InspectorLayout) => void] {
  const contextKey = useMemo(() => layoutContextKey(sessionId), [sessionId]);
  const [layouts, setLayouts] = useState<LayoutRecord>(readLayouts);
  const fallback = useMemo<InspectorLayout>(
    () => ({ openGroup: fallbackGroup, selected: {} }),
    [fallbackGroup],
  );

  const current = useMemo(
    () => pruneLayout(layouts[contextKey] ?? fallback, hasSession),
    [layouts, contextKey, fallback, hasSession],
  );

  const commit = useCallback(
    (next: (previous: InspectorLayout) => InspectorLayout) => {
      setLayouts((previous) => {
        const base = pruneLayout(previous[contextKey] ?? fallback, hasSession);
        const entry = pruneLayout(next(base), hasSession);
        if (sameLayout(entry, base)) return previous;
        return { ...previous, [contextKey]: entry };
      });
    },
    [contextKey, fallback, hasSession],
  );

  useEffect(() => {
    writeLayouts(layouts);
  }, [layouts]);

  return [current, commit];
}

/** Reveal `tab`: its group expands and the group remembers the choice. */
export function revealTab(layout: InspectorLayout, tab: RightPanelTab): InspectorLayout {
  const groupId: RightPanelGroupId = TAB_TO_GROUP[tab];
  return { ...layout, openGroup: groupId, selected: { ...layout.selected, [groupId]: tab } };
}
