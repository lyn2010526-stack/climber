import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronsDownUp, ChevronsUpDown, ChevronRight, X } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import type { Session } from '../../store/workspace';
import type { RightPanelTab } from '../../store/types';
import { useI18n } from '../../i18n';
import { ReasoningPanel } from './ReasoningPanel';
import { RunSummary } from './rightPanel/RunSummary';
import {
  RIGHT_PANEL_GROUPS,
  TAB_TO_GROUP,
  resolveGroupTab,
  isGroupAvailable,
  isSessionBound,
  type RightPanelGroupDef,
  type RightPanelSectionDef,
} from './rightPanel/groupModel';
import {
  ActivitySection,
  ConfigSection,
  DagSection,
  DiffSection,
  FilesSection,
  TraceSection,
} from './rightPanel/lazySections';
import { revealTab, useInspectorLayout } from './rightPanel/persistedState';
import { PanelError, PanelLoading, type ReportCount } from './rightPanel/PanelState';
import { cn } from '../../lib/utils';

/**
 * The inspector is an on-demand tool: at most one group is expanded, and a
 * section mounts only while its group is open. Opening the panel therefore
 * issues the one request its current tab needs, and nothing more. Each session
 * keeps its own arrangement, and a section's code is fetched the same moment it
 * is displayed.
 */
export function RightPanel() {
  const {
    rightPanelTab,
    rightPanelTabNonce,
    setRightPanelTab,
    rightPanelOpen,
    activeSessionId,
    sessions,
  } = useWorkspaceStore();
  const { t } = useI18n();

  const activeGroupId = TAB_TO_GROUP[rightPanelTab];
  const [counts, setCounts] = useState<Partial<Record<RightPanelTab, number | undefined>>>({});

  const session = useMemo(
    () => sessions.find((item) => item.id === activeSessionId),
    [sessions, activeSessionId],
  );
  const hasSession = Boolean(session);

  // Availability and open state are separate facts: `hasSession` decides which
  // groups can be entered, the remembered layout decides which one is, and a
  // layout left behind by a session without a run is pruned to what still works.
  const [layout, commitLayout] = useInspectorLayout(activeSessionId, hasSession, activeGroupId);
  const { openGroup, selected } = layout;

  /**
   * A tab asked for from outside the panel reveals its group exactly once.
   *
   * The request is recognised by its nonce and its value, so re-rendering,
   * opening or closing the panel repeats nothing — a manual collapse stays
   * collapsed — while a second request for the tab already in view still counts,
   * because its nonce moved. A session switch is a context of its own and needs
   * no request: each conversation is read from its own remembered layout.
   * Writing the revealed tab straight back into shared state would leak it into
   * the next conversation, so the arrival is recorded once and the layout is
   * written only when a genuinely new request arrives.
   */
  const requestKey = `${rightPanelTabNonce}:${rightPanelTab}`;
  const handledRequestRef = useRef(requestKey);
  useEffect(() => {
    if (handledRequestRef.current === requestKey) return;
    handledRequestRef.current = requestKey;
    commitLayout((previous) => revealTab(previous, rightPanelTab));
  }, [requestKey, rightPanelTab, commitLayout]);

  const isGroupOpen = (group: RightPanelGroupDef) =>
    openGroup === group.id && isGroupAvailable(group, hasSession);

  const activeSectionOf = (group: RightPanelGroupDef): RightPanelTab => {
    const tab = group.id === activeGroupId ? rightPanelTab : selected[group.id] ?? group.defaultTab;
    if (!session && group.sections.find((section) => section.tab === tab)?.requiresSession) {
      return resolveGroupTab(group, false);
    }
    return tab;
  };

  const openGroupDef = RIGHT_PANEL_GROUPS.find((group) => group.id === openGroup);
  const visibleTab = openGroupDef && isGroupOpen(openGroupDef) ? activeSectionOf(openGroupDef) : undefined;

  // A heading number only ever describes the section in view. Collapsing a
  // group or switching tabs retires the previous count instead of leaving a
  // stale one behind.
  useEffect(() => {
    setCounts((previous) => {
      const next: Partial<Record<RightPanelTab, number>> = {};
      let changed = false;
      for (const [tab, value] of Object.entries(previous) as Array<[RightPanelTab, number]>) {
        if (tab === visibleTab) next[tab] = value;
        else changed = true;
      }
      return changed ? next : previous;
    });
  }, [visibleTab]);

  const reporters = useMemo(() => {
    const map = {} as Record<RightPanelTab, ReportCount>;
    for (const group of RIGHT_PANEL_GROUPS) {
      for (const def of group.sections) {
        const tab = def.tab;
        // `undefined` means the section could not report a count (still
        // loading, or the request failed), so the heading shows no tally
        // instead of asserting an empty section.
        map[tab] = (count: number | undefined) =>
          setCounts((previous) => (previous[tab] === count ? previous : { ...previous, [tab]: count }));
      }
    }
    return map;
  }, []);

  if (!rightPanelOpen) return null;

  const closePanel = () => useWorkspaceStore.getState().toggleRightPanel();

  const toggleGroup = (group: RightPanelGroupDef) => {
    if (openGroup === group.id) {
      commitLayout((previous) => ({ ...previous, openGroup: null }));
      return;
    }
    commitLayout((previous) => ({ ...previous, openGroup: group.id }));
    setRightPanelTab(activeSectionOf(group));
  };

  const allCollapsed = openGroup === null;
  const collapseLabel = t(allCollapsed ? 'right_panel.expand_all' : 'right_panel.collapse_all');

  return (
    <aside
      className="flex h-full min-h-0 w-full min-w-0 flex-col border-l border-[var(--color-border-subtle)] bg-[var(--color-glass-bg)]"
      aria-label={t('right_panel.title')}
    >
      <header className="flex items-center gap-1 border-b border-[var(--color-border-subtle)] px-3 py-1.5">
        <h2 className="flex-1 truncate text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-secondary)]">
          {t('right_panel.title')}
        </h2>
        <button
          type="button"
          onClick={closePanel}
          aria-label="关闭检查器"
          title="关闭检查器"
          data-testid="right-panel-close"
          className="flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]"
        >
          <X size={13} aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => commitLayout((previous) => ({ ...previous, openGroup: allCollapsed ? activeGroupId : null }))}
          title={collapseLabel}
          aria-label={collapseLabel}
          className="flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]"
        >
          {allCollapsed ? <ChevronsUpDown size={13} aria-hidden="true" /> : <ChevronsDownUp size={13} aria-hidden="true" />}
        </button>
      </header>

      <RunSummary session={session} />

      <div className="flex-1 overflow-y-auto p-1.5">
        {RIGHT_PANEL_GROUPS.map((group) => {
          const available = isGroupAvailable(group, hasSession);
          const open = isGroupOpen(group);
          const activeTab = activeSectionOf(group);
          // The third gate on the section: only the entry the open group
          // actually shows is mounted, so a section nobody is looking at issues
          // no request and downloads no chunk.
          const activeDef = group.sections.find((def) => def.tab === activeTab);
          const count = open ? counts[activeTab] : undefined;
          const GroupIcon = group.icon;
          return (
            <section key={group.id} className="mb-1 last:mb-0">
              <h3>
                <button
                  type="button"
                  onClick={() => toggleGroup(group)}
                  aria-expanded={open}
                  aria-controls={`inspector-${group.id}`}
                  id={`inspector-heading-${group.id}`}
                  disabled={!available}
                  title={!available ? t('right_panel.summary.no_session_hint') : undefined}
                  className="flex w-full items-center gap-1.5 rounded-[var(--radius-md)] px-1.5 py-1.5 text-left transition-colors hover:bg-[var(--color-bg-surface-2)] disabled:opacity-40 disabled:hover:bg-transparent"
                >
                  <GroupIcon size={12} className="shrink-0 text-[var(--color-text-muted)]" aria-hidden="true" />
                  <span className="flex-1 truncate text-xs font-medium text-[var(--color-text-primary)]">
                    {t(group.labelKey)}
                  </span>
                  {/* Decorative tally for the entries read in the body below. */}
                  {count !== undefined && count > 0 && (
                    <span
                      aria-hidden="true"
                      className="shrink-0 font-mono text-[10px] tabular-nums text-[var(--color-text-muted)]"
                    >
                      {count}
                    </span>
                  )}
                  <ChevronRight
                    size={12}
                    className={cn(
                      'shrink-0 text-[var(--color-text-muted)] transition-transform duration-150',
                      open && 'rotate-90',
                    )}
                    aria-hidden="true"
                  />
                </button>
              </h3>

              {open && (
                <div id={`inspector-${group.id}`} className="pl-1">
                  {group.sections.length > 1 && (
                    <div
                      role="tablist"
                      aria-label={t(group.labelKey)}
                      className="mb-1.5 flex gap-1 border-b border-[var(--color-border-subtle)]"
                    >
                      {group.sections.map((def) => (
                        <SubTab
                          key={def.tab}
                          def={def}
                          hasSession={hasSession}
                          selected={activeTab === def.tab}
                          onSelect={() => {
                            commitLayout((previous) => ({
                              ...previous,
                              selected: { ...previous.selected, [group.id]: def.tab },
                            }));
                            setRightPanelTab(def.tab);
                          }}
                        />
                      ))}
                    </div>
                  )}

                  <div
                    role="tabpanel"
                    id={`inspector-panel-${activeTab}`}
                    aria-labelledby={
                      group.sections.length > 1
                        ? `inspector-tab-${activeTab}`
                        : `inspector-heading-${group.id}`
                    }
                    className="px-1 pb-1.5"
                  >
                    {activeDef && (
                      <SectionBody
                        // Session-independent sections keep their loaded data
                        // across a session switch instead of refetching.
                        key={
                          isSessionBound(activeDef) === true
                            ? `${activeTab}-${activeSessionId}`
                            : activeTab
                        }
                        def={activeDef}
                        tab={activeTab}
                        session={session}
                        sessionId={activeSessionId}
                        onCount={reporters[activeTab]}
                      />
                    )}
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </div>
    </aside>
  );
}

function SubTab({
  def,
  hasSession,
  selected,
  onSelect,
}: {
  def: RightPanelSectionDef;
  hasSession: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  const { t } = useI18n();
  const SectionIcon = def.icon;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      id={`inspector-tab-${def.tab}`}
      aria-controls={selected ? `inspector-panel-${def.tab}` : undefined}
      disabled={def.requiresSession && !hasSession}
      onClick={onSelect}
      className={cn(
        'flex min-h-[28px] flex-1 items-center justify-center gap-1 border-b-2 px-1.5 pb-1 pt-0.5 text-[11px] transition-colors',
        selected
          ? 'border-[var(--color-text-secondary)] font-medium text-[var(--color-text-primary)]'
          : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]',
      )}
    >
      <SectionIcon size={11} aria-hidden="true" />
      <span className="truncate">{t(def.labelKey)}</span>
    </button>
  );
}

/**
 * Three gates stand between a group heading and its section: the group must be
 * available, it must be the open one, and the section must be the entry in
 * view. What is left is a chunk request, and the placeholder that covers it
 * stands exactly as many rows as the content it replaces, so the panel holds
 * its height while the code arrives.
 */
function SectionBody({
  def,
  tab,
  session,
  sessionId,
  onCount,
}: {
  def: RightPanelSectionDef;
  tab: RightPanelTab;
  session: Session | undefined;
  sessionId: string | null;
  onCount: ReportCount;
}) {
  const [retryKey, setRetryKey] = useState(0);
  return (
    <LazySectionBoundary key={retryKey} onRetry={() => setRetryKey((value) => value + 1)}>
      <Suspense
        fallback={
          <div data-testid="inspector-section-fallback">
            <PanelLoading rows={def.skeletonRows} />
          </div>
        }
      >
        {sectionContent({ tab, session, sessionId, onCount })}
      </Suspense>
    </LazySectionBoundary>
  );
}

class LazySectionBoundary extends Component<
  { children: ReactNode; onRetry: () => void },
  { failed: boolean }
> {
  override state = { failed: false };

  override componentDidCatch() {
    this.setState({ failed: true });
  }

  override render() {
    if (this.state.failed) return <PanelError onRetry={this.props.onRetry} />;
    return this.props.children;
  }
}

function sectionContent({
  tab,
  session,
  sessionId,
  onCount,
}: {
  tab: RightPanelTab;
  session: Session | undefined;
  sessionId: string | null;
  onCount: ReportCount;
}) {
  switch (tab) {
    case 'config':
      // Model and token figures live here and nowhere else in the panel.
      return <ConfigSection session={session} />;
    case 'dag':
      return <DagSection onCount={onCount} />;
    case 'trace':
      return <TraceSection onCount={onCount} />;
    case 'reasoning':
      return <ReasoningPanel />;
    case 'diff':
      return <DiffSection sessionId={sessionId} />;
    case 'files':
      // The localised title already carries the document count.
      return <FilesSection />;
    case 'toolcalls':
      return <ActivitySection sessionId={sessionId} onCount={onCount} />;
    default:
      return null;
  }
}
