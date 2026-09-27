import {
  Activity, Brain, FileDiff, FolderTree, GitBranch, Sliders, Wrench, type LucideIcon,
} from 'lucide-react';
import type { RightPanelTab } from '../../../store/types';

export type RightPanelGroupId = 'overview' | 'execution' | 'reasoning' | 'changes' | 'activity';

export interface RightPanelSectionDef {
  tab: RightPanelTab;
  /** i18n key under `right_panel.sections` */
  labelKey: string;
  icon: LucideIcon;
  requiresSession: boolean;
  /**
   * Rows the section's own skeleton stands in for. The chunk gate reuses it so
   * the placeholder is exactly as tall as the content that replaces it and the
   * panel does not jump when the lazy section resolves.
   */
  skeletonRows: number;
}

export interface RightPanelGroupDef {
  id: RightPanelGroupId;
  /** i18n key under `right_panel.groups` */
  labelKey: string;
  icon: LucideIcon;
  /** Section shown when the group is entered without an explicit tab. */
  defaultTab: RightPanelTab;
  sections: RightPanelSectionDef[];
}

const section = (
  tab: RightPanelTab,
  labelKey: string,
  icon: LucideIcon,
  requiresSession: boolean,
  skeletonRows: number,
): RightPanelSectionDef => ({ tab, labelKey, icon, requiresSession, skeletonRows });

/**
 * The right panel is organised as five progressive-disclosure groups. Each
 * group keeps the store's existing tab granularity so the control bar and any
 * deep links keep working, while the visible hierarchy stays two levels deep:
 * a persistent run summary plus collapsible groups.
 */
export const RIGHT_PANEL_GROUPS: RightPanelGroupDef[] = [
  {
    id: 'overview',
    labelKey: 'right_panel.groups.overview',
    icon: Sliders,
    defaultTab: 'config',
    sections: [section('config', 'right_panel.sections.config', Sliders, false, 6)],
  },
  {
    id: 'execution',
    labelKey: 'right_panel.groups.execution',
    icon: GitBranch,
    defaultTab: 'dag',
    sections: [
      section('dag', 'right_panel.sections.dag', GitBranch, false, 3),
      section('trace', 'right_panel.sections.trace', Activity, false, 2),
    ],
  },
  {
    id: 'reasoning',
    labelKey: 'right_panel.sections.reasoning',
    icon: Brain,
    defaultTab: 'reasoning',
    sections: [section('reasoning', 'right_panel.sections.reasoning', Brain, true, 3)],
  },
  {
    id: 'changes',
    labelKey: 'right_panel.groups.changes',
    icon: FileDiff,
    defaultTab: 'diff',
    sections: [
      section('diff', 'right_panel.sections.diff', FileDiff, true, 3),
      section('files', 'right_panel.sections.files', FolderTree, false, 3),
    ],
  },
  {
    id: 'activity',
    labelKey: 'right_panel.groups.activity',
    icon: Wrench,
    defaultTab: 'toolcalls',
    sections: [section('toolcalls', 'right_panel.sections.toolcalls', Wrench, true, 2)],
  },
];

export const TAB_TO_GROUP: Record<RightPanelTab, RightPanelGroupId> = {
  config: 'overview',
  dag: 'execution',
  trace: 'execution',
  reasoning: 'reasoning',
  diff: 'changes',
  files: 'changes',
  toolcalls: 'activity',
};

const GROUP_BY_ID: Partial<Record<RightPanelGroupId, RightPanelGroupDef>> = Object.fromEntries(
  RIGHT_PANEL_GROUPS.map((group) => [group.id, group]),
) as Partial<Record<RightPanelGroupId, RightPanelGroupDef>>;

/**
 * A tab persisted by an earlier session can name a capability the model no
 * longer offers, so a tab is only honoured when the group still declares it.
 */
export function isAvailableTab(tab: unknown, group: RightPanelGroupDef): boolean {
  return typeof tab === 'string' && group.sections.some((def) => def.tab === tab);
}

export function groupById(id: unknown): RightPanelGroupDef | undefined {
  return typeof id === 'string' ? GROUP_BY_ID[id as RightPanelGroupId] : undefined;
}

/** A group is unusable only when every one of its sections needs a session. */
export function isGroupAvailable(group: RightPanelGroupDef, hasSession: boolean): boolean {
  return hasSession || group.sections.some((def) => !def.requiresSession);
}

/**
 * Whether a section's payload depends on the active session. Session-bound
 * sections remount on a session switch so they refetch; session-independent
 * sections keep their data instead of re-issuing requests nobody asked for.
 */
export function isSessionBound(def: RightPanelSectionDef): boolean {
  return def.requiresSession;
}

/** True when any section of the group follows the active session. */
export function isGroupSessionBound(group: RightPanelGroupDef): boolean {
  return group.sections.some(isSessionBound);
}

/**
 * Entry point for a group: the preferred section, falling back to the first
 * section that works without a session so the group is never a dead end.
 */
export function resolveGroupTab(group: RightPanelGroupDef, hasSession: boolean): RightPanelTab {
  if (hasSession) return group.defaultTab;
  const fallback = group.sections.find((def) => !def.requiresSession);
  return fallback?.tab ?? group.defaultTab;
}
