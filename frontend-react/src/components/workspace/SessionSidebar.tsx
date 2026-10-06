import { Fragment, useState, useEffect, useCallback, useId, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MessageSquare, Plus, Trash2, SlidersHorizontal, History, Search, Filter, ChevronDown, ChevronRight,
} from 'lucide-react';
import {
  useWorkspaceStore,
  normalizeSessionStatus,
  type Session,
  type ApiSession,
  type SessionStatus,
} from '../../store/workspace';
import { api } from '../../api';
import { apiClient } from '../../lib/api-client';
import { ModelConfig } from '../chat/ModelConfig';
import type { ModelSelection } from '../chat/ModelSelector';
import { UserSwitcher } from './UserSwitcher';
import { SessionTitle } from './SessionTitle';
import { formatTime } from '../../i18n/utils';
import {
  availableSessionStatuses,
  buildSessionView,
  isSessionFilterActive,
  type SessionFilter,
  type SessionGroupId,
  type SessionTimeline,
} from './sessionGrouping';
import { sessionStatusLabel } from './rightPanel/statusTone';

/** The panel id a group header points `aria-controls` at. */
const groupPanelId = (id: SessionGroupId) => `session-group-${id}`;

function parseBackendTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * The list is the body of this sidebar: creation lives in one on-demand
 * disclosure at the top, and the checkpoint history opens in a drawer under the
 * list, so no secondary panel permanently takes height away from the sessions.
 */
export function SessionSidebar() {
  const { t } = useTranslation();
  const headingId = useId();
  const checkpointsId = useId();
  const creationOptionsId = useId();
  const filterPanelId = useId();
  const deleteTitleId = useId();
  const deleteBodyId = useId();
  const createButtonRef = useRef<HTMLButtonElement>(null);
  const creationOptionsRef = useRef<HTMLButtonElement>(null);
  const filterToggleRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const sessionButtons = useRef(new Map<string, HTMLButtonElement>());
  const sessionActions = useRef(new Map<string, HTMLButtonElement>());
  const groupButtons = useRef(new Map<SessionGroupId, HTMLButtonElement>());
  const {
    sessions, activeSessionId, setActiveSession,
    loadSessions, createSessionLocal, deleteSession, updateSession,
    loadingSessions, sessionsLoaded, setSessionsLoading,
  } = useWorkspaceStore();

  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [ownerKey, setOwnerKey] = useState<string | null>(null);
  const [identityError, setIdentityError] = useState(false);
  const [useAgentModel, setUseAgentModel] = useState(true);
  const [selection, setSelection] = useState<{ owner: string; model: ModelSelection | null } | null>(null);
  const selectedModel = selection?.owner === ownerKey ? selection.model : null;
  const [creating, setCreating] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [agentsError, setAgentsError] = useState(false);
  const [sessionsError, setSessionsError] = useState(false);
  const [sessionTimeline, setSessionTimeline] = useState<Map<string, SessionTimeline>>(() => new Map());

  const [showCheckpoints, setShowCheckpoints] = useState(false);
  const [showCreationOptions, setShowCreationOptions] = useState(false);
  const [showFilter, setShowFilter] = useState(false);
  const [filter, setFilter] = useState<SessionFilter>({ query: '', status: 'all' });
  const [collapsedGroups, setCollapsedGroups] = useState<ReadonlySet<SessionGroupId>>(() => new Set());
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [hoveredSessionId, setHoveredSessionId] = useState<string | null>(null);

  // The clock the date buckets were cut against. A long-lived sidebar re-reads
  // it, so a session that was "today" at mount does not stay in that group
  // until the next reload.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(tick);
  }, []);

  const refreshSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = (await api.listSessions()) as ApiSession[];
      setSessionsError(false);
      setSessionTimeline(new Map((Array.isArray(data) ? data : []).map((session) => [
        session.id,
        {
          createdAt: parseBackendTimestamp(session.created_at),
          updatedAt: parseBackendTimestamp(session.updated_at),
        },
      ])));
      loadSessions(Array.isArray(data) ? data : []);
    } catch {
      // A failed list is an error state; the sessions already in the store are
      // left untouched and the empty list below is never claimed as "no sessions".
      setSessionsError(true);
      setSessionsLoading(false);
    }
  }, [loadSessions, setSessionsLoading]);

  useEffect(() => {
    let active = true;
    let controller: AbortController | undefined;
    const refreshOwner = () => {
      controller?.abort();
      controller = new AbortController();
      const signal = controller.signal;
      apiClient.get<{ id: string }>('/auth/me', { signal }).then((user) => {
        if (!active || signal.aborted) return;
        if (!user.id) throw new Error('Missing user identity');
        setOwnerKey(user.id);
        setIdentityError(false);
      }).catch(() => {
        if (!active || signal.aborted) return;
        setOwnerKey(null);
        setSelection(null);
        setIdentityError(true);
      });
    };
    refreshOwner();
    window.addEventListener('storage', refreshOwner);
    window.addEventListener('focus', refreshOwner);
    return () => {
      active = false;
      controller?.abort();
      window.removeEventListener('storage', refreshOwner);
      window.removeEventListener('focus', refreshOwner);
    };
  }, []);

  useEffect(() => {
    let active = true;
    setAgents([]);
    setSelectedAgent('');
    setSelection(null);
    setUseAgentModel(true);
    if (!ownerKey) return;
    setAgentsError(false);
    api.listAgents().then((data) => {
      if (!active) return;
      setAgents(data);
      if (data.length > 0) {
        const first = data[0];
        if (first) setSelectedAgent(first.id);
      }
    }).catch(() => {
      // Distinct from "no agents available": the select must not offer an empty
      // list as if the backend had reported one.
      if (active) setAgentsError(true);
    });
    return () => { active = false; };
  }, [ownerKey]);

  useEffect(() => {
    if (!sessionsLoaded) {
      refreshSessions();
    }
  }, [sessionsLoaded, refreshSessions]);

  const handleCreate = useCallback(async () => {
    if (!selectedAgent || !ownerKey || creating || (!useAgentModel && !selectedModel)) return;
    setCreating(true);
    setCreateError(null);
    try {
      const user = await apiClient.get<{ id: string }>('/auth/me');
      if (user.id !== ownerKey) {
        setOwnerKey(user.id || null);
        setSelection(null);
        throw new Error('当前用户已变更，请重新选择智能体和模型');
      }
      const chosen = useAgentModel ? null : selectedModel;
      const title = `会话 ${sessions.length + 1}`;
      const created = await api.createSession({
        title,
        agent_id: selectedAgent,
        model_settings: chosen,
      });
      const newId: string = created?.id || created?.session_id || '';
      // Only values the create response or the chosen model actually carried.
      // The session API reports no temperature, no max tokens and no usage, so
      // those stay absent instead of being filled with 0.7 / 4096 / 200000.
      const provider = created?.provider || chosen?.provider || agents.find((a) => a.id === selectedAgent)?.provider;
      const modelId = created?.model_id || chosen?.model_id || agents.find((a) => a.id === selectedAgent)?.model_id;
      const modelConfig: Session['modelConfig'] = {
        ...(provider ? { provider } : {}),
        ...(modelId ? { modelId } : {}),
      };
      await refreshSessions();
      if (newId) {
        const exists = useWorkspaceStore.getState().sessions.some((s) => s.id === newId);
        if (!exists) {
          createSessionLocal({
            id: newId,
            title: created?.title ?? title,
            status: normalizeSessionStatus(created?.status),
            messages: [],
            activeSkills: [],
            activeTools: [],
            modelConfig: Object.keys(modelConfig).length > 0 ? modelConfig : undefined,
            createdAt: Date.now(),
          });
        } else {
          updateSession(newId, {
            modelConfig: Object.keys(modelConfig).length > 0 ? modelConfig : undefined,
          });
        }
        setActiveSession(newId);
      }
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : '创建会话失败，请重试');
    } finally {
      setCreating(false);
    }
  }, [
    selectedAgent, selectedModel, useAgentModel, ownerKey, creating, sessions.length, agents,
    refreshSessions, createSessionLocal, updateSession, setActiveSession,
  ]);

  const view = useMemo(
    () => buildSessionView(sessions, filter, now, sessionTimeline, 'recent'),
    [sessions, filter, now, sessionTimeline],
  );
  const filterActive = isSessionFilterActive(filter);
  const statusOptions = useMemo(() => availableSessionStatuses(sessions), [sessions]);

  /**
   * Rows the reader has put out of reach by collapsing their group. They stay
   * mounted, so a ref lookup still finds them and `focus()` on them would leave
   * the focus ring on something nobody can see. Every handover has to consult
   * this before it treats a row as a destination.
   */
  const collapsedRowIds = useMemo(() => {
    const hidden = new Set<string>();
    if (collapsedGroups.size === 0) return hidden;
    for (const group of view.groups) {
      if (!collapsedGroups.has(group.id)) continue;
      for (const session of group.sessions) hidden.add(session.id);
    }
    return hidden;
  }, [view, collapsedGroups]);

  const toggleGroup = useCallback((id: SessionGroupId) => {
    setCollapsedGroups((previous) => {
      const next = new Set(previous);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }, []);

  /**
   * Creation, or the control that can reach it: a disabled primary button
   * cannot hold focus, so the handover has to go somewhere that can.
   */
  const creationTarget = useCallback((): HTMLElement | null =>
    createButtonRef.current?.disabled ? creationOptionsRef.current : createButtonRef.current, []);

  /**
   * Whether the row held focus when the confirmation was raised. The dialog
   * takes focus for itself, so this has to be sampled at the moment the action
   * was triggered rather than at confirmation time.
   */
  const pendingRowHeldFocus = useRef(false);
  /** The row outlives the dialog while the request is in flight; this stops a
   *  second request going out for the same row. */
  const deletingId = useRef<string | null>(null);
  /** The element focus came from, so dismissing the dialog gives it back. */
  const dialogOpener = useRef<HTMLElement | null>(null);

  const dismissDialog = useCallback(() => {
    setPendingDeleteId(null);
    dialogOpener.current?.focus();
    dialogOpener.current = null;
  }, []);

  const requestDelete = useCallback((id: string) => {
    const row = sessionButtons.current.get(id)?.parentElement ?? null;
    pendingRowHeldFocus.current = row?.contains(document.activeElement) === true;
    dialogOpener.current = document.activeElement as HTMLElement | null;
    setPendingDeleteId(id);
  }, []);

  /** Focus enters the dialog once it is up, so the reader lands inside it. */
  useEffect(() => {
    if (pendingDeleteId === null) return;
    const opener = dialogOpener.current;
    // The row that raised the dialog is about to lose the request, and a
    // dialog that opened with focus outside it would strand the reader there.
    if (!opener?.isConnected) dialogOpener.current = dialogRef.current;
    const timer = window.setTimeout(() => dialogRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [pendingDeleteId]);

  const handleDialogDismiss = useCallback(() => {
    if (deletingId.current) return;
    dismissDialog();
  }, [dismissDialog]);

  const confirmDelete = useCallback(async () => {
    const id = pendingDeleteId;
    if (!id || deletingId.current) return;
    deletingId.current = id;
    // The dialog closes first: closing it hands focus back to the row that
    // raised it, which is the state the handover below is written against.
    setPendingDeleteId(null);
    const opener = dialogOpener.current;
    dialogOpener.current = null;
    setDeleteError(null);

    const row = sessionButtons.current.get(id)?.parentElement ?? null;
    const rowHeldFocus = pendingRowHeldFocus.current;
    // The successor is read off the *visible* order, so a filter cannot hand
    // focus to a row that has been filtered out. A row inside a group the
    // reader collapsed is still mounted but hidden, and focus cannot go there
    // either, so that case falls through to the group's header.
    const index = view.visible.findIndex((session) => session.id === id);
    const neighbour = view.visible[index + 1] ?? view.visible[index - 1];
    const neighbourId = neighbour?.id;
    const neighbourGroup = neighbour ? view.groupOf.get(neighbour.id) : undefined;
    const neighbourReachable = neighbour !== undefined && !collapsedRowIds.has(neighbour.id);
    const groupTarget = neighbour && !neighbourReachable
      ? groupButtons.current.get(neighbourGroup!)
      : undefined;
    const successor = rowHeldFocus && neighbourReachable
      ? sessionButtons.current.get(neighbour.id) ?? null
      : null;
    // Prefer the neighbouring row; the header of its group covers a collapsed
    // group; creation covers a list that had no other row at all.
    const handoverTarget = successor ?? groupTarget ?? creationTarget();

    try {
      await api.deleteSession(id);
    } catch {
      deletingId.current = null;
      setDeleteError('删除会话失败，请重试');
      // The row survived, so the action that asked for the delete is where a
      // retry starts from.
      opener?.focus();
      return;
    }
    pendingRowHeldFocus.current = false;

    // Focus is handed over before the row unmounts, so the document never spends
    // a frame with no focus owner.
    if (rowHeldFocus) handoverTarget?.focus();
    deleteSession(id);
    await refreshSessions();

    // Unmounting the focused element drops focus to the document, so "focused
    // before" is not "still focused after": the row may be gone by the time the
    // refetch lands. Re-resolve and re-hand, and fall through the same order.
    const activeElement = document.activeElement;
    const rowRemovedFocus = row?.isConnected === false
      && (activeElement === document.body || activeElement === document.documentElement);
    if (rowRemovedFocus) {
      const refreshedSuccessor = neighbourId
        ? sessionButtons.current.get(neighbourId)
        : null;
      const focusTarget: HTMLElement | null = refreshedSuccessor
        ?? (successor?.isConnected ? successor : null)
        ?? groupTarget
        ?? creationTarget();
      focusTarget?.focus();
    }
    // The row is gone, so the guard has nothing left to protect and the next
    // delete in this mount has to be allowed to go out.
    deletingId.current = null;
  }, [pendingDeleteId, view, collapsedRowIds, deleteSession, refreshSessions, creationTarget]);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const checkpoints = (activeSession?.messages ?? []).slice(-10).reverse();
  const pendingDelete = sessions.find((s) => s.id === pendingDeleteId) ?? null;

  const sessionTime = (id: string) => {
    const timestamp = sessionTimeline.get(id)?.updatedAt;
    return typeof timestamp === 'number' && Number.isFinite(timestamp)
      ? formatTime(timestamp)
      : t('common.not_reported', '未上报');
  };

  return (
    <aside className="session-sidebar" aria-label={t('navigation.sessions')}>
      {/* Creation: one primary button, with everything that configures it behind
          a disclosure that starts closed. */}
      <div className="space-y-2 border-b border-[var(--color-border-subtle)] p-3">
        <div className="flex items-center gap-1">
        <button type="button"
          ref={createButtonRef}
          onClick={handleCreate}
          disabled={creating || !ownerKey || !selectedAgent || (!useAgentModel && !selectedModel)}
          className="flex h-11 min-w-0 flex-1 items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] px-3 text-xs font-medium text-[var(--color-accent-text)] transition-colors hover:bg-[var(--color-accent-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]"
        >
          <Plus aria-hidden="true" size={14} strokeWidth={2.5} /> {creating ? '创建中...' : '新建会话'}
        </button>
        <button type="button" ref={creationOptionsRef}
          aria-label="创建配置" title="创建配置"
          aria-expanded={showCreationOptions} aria-controls={showCreationOptions ? creationOptionsId : undefined}
          onClick={() => setShowCreationOptions(!showCreationOptions)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
        >
          <SlidersHorizontal aria-hidden="true" size={16} />
        </button>
        </div>
        <div id={creationOptionsId} hidden={!showCreationOptions}
          className="max-h-[40vh] space-y-2 overflow-y-auto text-xs text-[var(--color-text-secondary)]"
          onKeyDown={(event) => {
            if (event.key !== 'Escape') return;
            event.stopPropagation();
            setShowCreationOptions(false);
            creationOptionsRef.current?.focus();
          }}
        >
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          aria-label="选择智能体"
          disabled={agentsError}
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none disabled:opacity-60"
        >
          {agentsError
            ? <option value="">智能体列表未上报</option>
            : agents.length === 0 && <option value="">暂无可用智能体</option>}
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        {agentsError && (
          <p role="alert" className="text-[11px] text-[var(--color-warning)]">智能体列表加载失败，请稍后重试</p>
        )}
        <select
          value={useAgentModel ? 'agent' : 'credential'}
          onChange={(e) => { setUseAgentModel(e.target.value === 'agent'); setSelection(null); }}
          aria-label="模型来源"
          disabled={creating || !ownerKey}
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
        >
          <option value="agent">使用智能体默认模型</option>
          <option value="credential">使用已存凭据选择模型</option>
        </select>
        {!useAgentModel && ownerKey && (
          <ModelConfig ownerKey={ownerKey} value={selectedModel} disabled={creating}
            onChange={(model) => setSelection({ owner: ownerKey, model })} />
        )}
        </div>
        {identityError && <p role="alert">无法确认当前用户，请刷新页面重试</p>}
      </div>

      {deleteError && (
        <p role="alert" className="px-3 py-2 text-xs text-[var(--color-error)]">
          {deleteError}
        </p>
      )}
      {createError && (
        <p role="alert" className="px-3 py-2 text-xs text-[var(--color-error)]">
          {createError}
        </p>
      )}

      <div className="flex items-center justify-between px-4 pb-1 pt-3 text-xs text-[var(--color-text-muted)]">
        <h2 id={headingId} className="font-medium text-[var(--color-text-secondary)]">{t('navigation.sessions')}</h2>
        <div className="flex items-center gap-1">
        {/* A failed list has no count to report; "0" would claim the backend returned none. */}
        <span
          className="tabular-nums"
          aria-label={sessionsError
            ? `${t('common.count')}: ${t('common.not_reported')}`
            : `${t('common.count')}: ${sessions.length}`}
        >
          {sessionsError ? t('common.not_reported') : sessions.length}
        </span>
        <button type="button" ref={filterToggleRef}
          aria-label={showFilter ? '关闭会话筛选' : '筛选会话'}
          title={showFilter ? '关闭会话筛选' : '筛选会话'}
          aria-expanded={showFilter} aria-controls={showFilter ? filterPanelId : undefined}
          onClick={() => setShowFilter(!showFilter)}
          className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
            filterActive
              ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]'
              : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)]'
          }`}
        >
          <Filter aria-hidden="true" size={14} />
        </button>
        </div>
      </div>
      <div id={filterPanelId} hidden={!showFilter}
        className="space-y-2 border-b border-[var(--color-border-subtle)] px-3 pb-3"
        onKeyDown={(event) => {
          if (event.key !== 'Escape') return;
          event.stopPropagation();
          setShowFilter(false);
          filterToggleRef.current?.focus();
        }}
      >
        <div className="relative">
          <Search aria-hidden="true" size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="search"
            value={filter.query}
            onChange={(event) => setFilter((previous) => ({ ...previous, query: event.target.value }))}
            aria-label="搜索会话标题"
            placeholder="搜索会话标题"
            className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] pl-9 pr-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
          />
        </div>
        <select
          value={filter.status}
          onChange={(event) => setFilter((previous) => ({ ...previous, status: event.target.value as SessionStatus | 'all' }))}
          aria-label="按状态筛选"
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
        >
          <option value="all">全部状态</option>
          {/* Only statuses the loaded list actually carries, so the control never
              offers a bucket the backend has not reported. */}
          {statusOptions.map((status) => (
            <option key={status} value={status}>{sessionStatusLabel(status, t)}</option>
          ))}
        </select>
        {filterActive && (
          <button type="button"
            onClick={() => setFilter({ query: '', status: 'all' })}
            className="min-h-11 w-full rounded-lg border border-[var(--color-border-subtle)] px-3 text-xs text-[var(--color-accent-foreground)] transition-colors hover:bg-[var(--color-accent-subtle)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]"
          >
            清除筛选
          </button>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2" aria-busy={loadingSessions}>
        {loadingSessions && (
          <div role="status" className="text-center py-6">
            <div aria-hidden="true" className="mx-auto mb-2 h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent motion-reduce:animate-none" />
            <span className="text-xs text-[var(--color-text-muted)]">{t('common.loading_data')}</span>
          </div>
        )}
        {sessionsError && (
          <div role="alert" className="rounded-lg border border-[var(--color-warning)]/30 bg-[var(--color-warning-subtle)] px-3 py-4 text-center">
            <p className="text-xs text-[var(--color-text-secondary)]">会话列表未上报</p>
            <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">加载会话失败，请检查后端连接后重试</p>
          </div>
        )}
        {/* One scroll viewport, and the group headers live inside it, so a
            section that grows or collapses above the rows scrolls with them
            instead of pinning itself against the container. */}
        <ul aria-labelledby={headingId} className="space-y-1">
        {view.groups.map((group) => {
          const collapsed = collapsedGroups.has(group.id);
          return (
          <Fragment key={group.id}>
            {/* role="none" keeps the header out of the row count, so the list
                still reports exactly as many items as there are sessions. */}
            <li role="none">
              <button type="button"
                ref={(node) => { if (node) groupButtons.current.set(group.id, node); else groupButtons.current.delete(group.id); }}
                aria-expanded={!collapsed}
                aria-controls={groupPanelId(group.id)}
                onClick={() => toggleGroup(group.id)}
                className="flex min-h-8 w-full items-center gap-1 rounded-md px-2 text-left text-[11px] font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-accent)]"
              >
                {collapsed ? <ChevronRight aria-hidden="true" size={12} /> : <ChevronDown aria-hidden="true" size={12} />}
                <span className="truncate">{group.label}</span>
                <span className="ml-auto tabular-nums">{group.sessions.length}</span>
              </button>
            </li>
            <li role="none" id={groupPanelId(group.id)} hidden={collapsed}>
              <ul className="space-y-1">
              {group.sessions.map((s) => {
                const idx = view.visible.findIndex((session) => session.id === s.id);
                return (
                <li key={s.id}>
                <div
                  onMouseEnter={() => setHoveredSessionId(s.id)}
                  onMouseLeave={() => setHoveredSessionId((current) => (current === s.id ? null : current))}
                  className={`group relative flex min-h-11 w-full items-center rounded-lg border text-left transition-colors ${
                    activeSessionId === s.id
                      ? 'border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]'
                      : 'border-transparent text-[var(--color-text-secondary)] hover:border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                   {activeSessionId === s.id && <span aria-hidden="true" className="absolute inset-y-3 left-0 w-0.5 rounded-full bg-[var(--color-accent)]" />}
                    <button
                      type="button"
                      ref={(node) => { if (node) sessionButtons.current.set(s.id, node); else sessionButtons.current.delete(s.id); }}
                      aria-current={activeSessionId === s.id ? 'true' : undefined}
                      onClick={() => setActiveSession(s.id)}
                      onFocus={() => setHoveredSessionId(s.id)}
                      onBlur={() => setHoveredSessionId((current) => (current === s.id ? null : current))}
                      onKeyDown={(event) => {
                        if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
                        // The row has two focus stops: the title activates the session,
                        // the trailing action acts on it. Forward and back cross between
                        // them, the vertical keys walk the list without selecting.
                        if (event.key === 'ArrowRight') {
                          const action = sessionActions.current.get(s.id);
                          if (action) {
                            event.preventDefault();
                            action.focus();
                          }
                          return;
                        }
                        if (event.key === 'ArrowLeft') {
                          event.preventDefault();
                          return;
                        }
                        const last = view.visible.length - 1;
                        const target = event.key === 'Home' ? 0 : event.key === 'End' ? last
                          : event.key === 'ArrowDown' ? Math.min(idx + 1, last)
                          : event.key === 'ArrowUp' ? Math.max(idx - 1, 0) : null;
                        if (target === null) return;
                        event.preventDefault();
                        // The walk follows the grouped reading order, and a row in a
                        // collapsed group has nothing to focus, so the walk steps
                        // over it rather than stranding the reader on a dead key.
                        const step = target > idx ? 1 : -1;
                        for (let i = target; i >= 0 && i <= last; i += step) {
                          const candidate = view.visible[i]!;
                          // A collapsed row is still mounted, so the ref finds it
                          // and focus would land somewhere the reader cannot see.
                          if (collapsedRowIds.has(candidate.id)) continue;
                          const button = sessionButtons.current.get(candidate.id);
                          if (button) {
                            button.focus();
                            return;
                          }
                        }
                        (creationTarget() ?? groupButtons.current.get(group.id))?.focus();
                      }}
                      aria-keyshortcuts="ArrowUp ArrowDown Home End ArrowRight"
                      className="flex min-h-11 min-w-0 flex-1 items-center gap-2.5 rounded-md px-3 py-1.5 text-left focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-accent)]"
                    >
                      <MessageSquare aria-hidden="true" size={15} className={`shrink-0 ${activeSessionId === s.id ? 'text-[var(--color-accent-foreground)]' : 'text-[var(--color-text-muted)]'}`} />
                      <span className="flex min-w-0 flex-1 items-center gap-2">
                        <SessionTitle
                          title={s.title || t('right_panel.summary.untitled')}
                          active={hoveredSessionId === s.id}
                          className={`text-sm leading-5 ${activeSessionId === s.id ? 'font-semibold' : 'font-medium'}`}
                        />
                        {' '}
                        <span className="sr-only">{sessionStatusLabel(s.status, t)}</span>
                        <span aria-hidden="true" className="shrink-0 truncate text-[11px] text-[var(--color-text-muted)]" title={`${sessionStatusLabel(s.status, t)} · ${sessionTime(s.id)}`}>
                          {sessionStatusLabel(s.status, t)} · {sessionTime(s.id)}
                        </span>
                     </span>
                   </button>
                  <button type="button"
                    ref={(node) => { if (node) sessionActions.current.set(s.id, node); else sessionActions.current.delete(s.id); }}
                    onClick={(e) => { e.stopPropagation(); requestDelete(s.id); }}
                     onKeyDown={(event) => {
                       if (event.key !== 'ArrowLeft') return;
                       event.preventDefault();
                       sessionButtons.current.get(s.id)?.focus();
                     }}
                     aria-label={`${t('common.delete', '删除')}${t('navigation.sessions', '会话')} ${s.title || t('right_panel.summary.untitled', '未命名会话')}`}
                     title={t('common.delete')}
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)] focus-visible:bg-[var(--color-error-subtle)] focus-visible:text-[var(--color-error)] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-accent)]"
                  >
                    <Trash2 aria-hidden="true" size={14} />
                  </button>
                 </div>
                </li>
                );
              })}
              </ul>
            </li>
          </Fragment>
          );
        })}
        </ul>
        {!loadingSessions && !sessionsError && sessions.length > 0 && filterActive && view.visible.length === 0 && (
          /* A filter that excludes everything is a page with no rows, not a
             missing page: the list region still stands, and the way out is a
             control inside it. */
          <div role="status" className="mx-1 rounded-lg border border-dashed border-[var(--color-border-subtle)] px-4 py-8 text-center">
            <Search aria-hidden="true" size={24} className="mx-auto mb-3 text-[var(--color-text-muted)]" />
            <p className="text-sm font-medium text-[var(--color-text-secondary)]">没有匹配当前筛选的会话</p>
            <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">共 {sessions.length} 个会话被当前筛选排除</p>
            <div className="mt-2 flex flex-wrap items-center justify-center gap-1">
              <button type="button"
                onClick={() => setFilter({ query: '', status: 'all' })}
                className="min-h-11 rounded-md px-3 text-xs text-[var(--color-accent-foreground)] hover:bg-[var(--color-accent-subtle)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]"
              >
                清除筛选
              </button>
              <button type="button"
                onClick={() => (createButtonRef.current?.disabled ? creationOptionsRef.current : createButtonRef.current)?.focus()}
                className="min-h-11 rounded-md px-3 text-xs text-[var(--color-accent-foreground)] hover:bg-[var(--color-accent-subtle)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]"
              >
                {t('common.add')} · {t('navigation.sessions')}
              </button>
            </div>
          </div>
        )}
        {!loadingSessions && !sessionsError && sessions.length === 0 && (
          <div role="status" className="mx-1 rounded-lg border border-dashed border-[var(--color-border-subtle)] px-4 py-8 text-center">
            <MessageSquare aria-hidden="true" size={24} className="mx-auto mb-3 text-[var(--color-text-muted)]" />
            <p className="text-sm font-medium text-[var(--color-text-secondary)]">{t('common.no_data')}</p>
            <button type="button" onClick={() => (createButtonRef.current?.disabled ? creationOptionsRef.current : createButtonRef.current)?.focus()} className="mt-2 min-h-11 rounded-md px-3 text-xs text-[var(--color-accent-foreground)] hover:bg-[var(--color-accent-subtle)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]">
              {t('common.add')} · {t('navigation.sessions')}
            </button>
          </div>
        )}
      </div>

      {/* Secondary material sits under the list and stays closed until asked for,
          so opening it never competes with the sessions for the visible area. */}
      <div className="border-t border-[var(--color-border-subtle)] p-3">
        <button type="button"
          aria-expanded={showCheckpoints}
          aria-controls={showCheckpoints ? checkpointsId : undefined}
          onClick={() => setShowCheckpoints(!showCheckpoints)}
          className={`flex min-h-11 w-full items-center gap-1.5 rounded-lg px-2 py-1 text-left text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
            showCheckpoints
              ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]'
              : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]'
          }`}
        >
          <History aria-hidden="true" size={14} />
          检查点历史
        </button>
        {showCheckpoints && (
          <div id={checkpointsId} className="mt-2 max-h-40 space-y-2 overflow-y-auto">
            {checkpoints.map((msg, i) => (
              <div key={`${msg.timestamp}-${i}`} className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2 py-1.5 text-[10px] text-[var(--color-text-secondary)]">
                <span className="text-[var(--color-text-muted)]">{formatTime(msg.timestamp)}</span>
                <span className="ml-2">{msg.type}</span>
              </div>
            ))}
            {checkpoints.length === 0 && (
              <p className="text-[10px] text-[var(--color-text-muted)] text-center py-2">暂无检查点</p>
            )}
          </div>
        )}
        <UserSwitcher />
      </div>

      {/* `DELETE /api/v1/sessions/{id}` drops the row outright and the API
          exposes no restore, archive or soft-delete route, so an undo would be
          a promise the backend cannot keep. The confirmation is the whole
          reversible step, and it says so before anything is sent.

          Rendered here rather than through the shared ConfirmDialog: that
          component reads the application i18n instance, and importing it would
          initialise the global translator inside a test that renders the
          sidebar without one, changing the labels the whole sidebar resolves
          through react-i18next. */}
      {pendingDeleteId !== null && (
        <div
          className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/60 p-4 motion-reduce:animate-none"
          onClick={handleDialogDismiss}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={deleteTitleId}
            aria-describedby={deleteBodyId}
            ref={dialogRef}
            tabIndex={-1}
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                event.stopPropagation();
                handleDialogDismiss();
                return;
              }
              if (event.key !== 'Tab') return;
              // Focus stays inside the dialog while it is up, so a reader who
              // tabs forward cannot land behind it and act on the list blind.
              const stops = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
                'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])',
              ) ?? []);
              if (stops.length === 0) {
                event.preventDefault();
                return;
              }
              const first = stops[0]!;
              const last = stops[stops.length - 1]!;
              if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
                event.preventDefault();
                last.focus();
              } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
              }
            }}
            className="w-full max-w-sm rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-6 shadow-[var(--shadow-xl)] focus-visible:outline-none"
          >
            <h3 id={deleteTitleId} className="text-base font-semibold text-[var(--color-text-primary)]">删除会话</h3>
            <p id={deleteBodyId} className="mt-2 text-sm text-[var(--color-text-secondary)]">
              「{pendingDelete?.title || t('right_panel.summary.untitled', '未命名会话')}」将被永久删除，消息与检查点一并移除。后端没有恢复接口，此操作无法撤销。
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button type="button"
                onClick={handleDialogDismiss}
                className="min-h-11 rounded-lg border border-[var(--color-border-default)] px-4 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                取消
              </button>
              <button type="button"
                onClick={() => { void confirmDelete(); }}
                className="min-h-11 rounded-lg bg-[var(--color-error)] px-4 text-sm font-medium text-[var(--color-text-inverse)] transition-colors hover:bg-[var(--color-error-subtle)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
