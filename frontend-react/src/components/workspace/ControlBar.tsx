import * as Popover from '@radix-ui/react-popover';
import { useCallback, useRef, useState } from 'react';
import {
  Play, Pause, Square, Camera, RotateCcw, Maximize2, Minimize2, PanelRight, Eye, EyeOff, MoreHorizontal,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useI18n } from '../../i18n';
import { PermissionModeToggle } from './PermissionModeToggle';
import { AutonomySlider } from './AutonomySlider';
import { usePermissionConfig } from './usePermissionConfig';
import { SessionStatusBadge } from './SessionStatusBadge';

const ICON_BUTTON = 'icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-30';

/**
 * The bar carries one thing per row of the workspace: the actions that belong to
 * the active session, then the single switch that reveals its inspector. Group
 * and section navigation lives inside the inspector itself, so repeating it here
 * would offer two paths to the same state.
 */
export function ControlBar() {
  const { t } = useI18n();
  const {
    activeSessionId, sessions, rightPanelOpen, toggleRightPanel,
    focusMode, toggleFocusMode,
    expertMode, toggleExpertMode,
    updateSession, addSnapshot, restoreSnapshot, snapshots,
  } = useWorkspaceStore();
  const permission = usePermissionConfig();

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const hasSession = Boolean(activeSession);
  const isRunning = activeSession?.status === 'running';
  const isPaused = activeSession?.status === 'paused';
  // Token accounting is optional: a session whose backend never reported usage
  // shows "not reported" instead of a fabricated 0 / 200000 gauge.
  const usedTokens = activeSession?.tokenUsage?.used;
  const tokenLimit = activeSession?.tokenUsage?.limit;
  const hasTokenUsage =
    typeof usedTokens === 'number' && Number.isFinite(usedTokens)
    && typeof tokenLimit === 'number' && Number.isFinite(tokenLimit) && tokenLimit > 0;
  const tokenPercent = hasTokenUsage
    ? Math.min(100, Math.round((usedTokens / tokenLimit) * 100))
    : 0;

  const handlePause = () => {
    if (activeSessionId) {
      updateSession(activeSessionId, { status: isPaused ? 'running' : 'paused' });
    }
  };

  const handleStop = () => {
    if (activeSessionId) {
      updateSession(activeSessionId, { status: 'completed' });
    }
  };

  const handleSnapshot = () => {
    if (activeSessionId) {
      addSnapshot({
        id: `snap-${Date.now()}`,
        sessionId: activeSessionId,
        timestamp: Date.now(),
        label: `Snapshot ${snapshots.length + 1}`,
        // The transcript travels with the snapshot, so restoring is a real
        // operation rather than a marker that promises something it cannot do.
        messages: [...(activeSession?.messages ?? [])],
      });
    }
  };

  // The newest snapshot of this session that actually carries a transcript. A
  // snapshot without one cannot be restored, so it is not offered at all instead
  // of being rendered as a control that would always fail.
  const restorableSnapshot = [...snapshots]
    .reverse()
    .find(snapshot => snapshot.sessionId === activeSessionId && Array.isArray(snapshot.messages));
  const canRollback = Boolean(activeSession) && Boolean(restorableSnapshot);
  const rollbackLabel = restorableSnapshot?.label
    ? `恢复到 ${restorableSnapshot.label}`
    : '恢复到快照';
  const [rollbackState, setRollbackState] = useState<{ kind: 'pending' } | { kind: 'failed'; message: string }>();
  // Synchronous mutex: a second activation before the bar re-renders would
  // otherwise start a second rollback on the same snapshot.
  const rollbackInFlight = useRef(false);

  const handleRollback = useCallback(async () => {
    if (!restorableSnapshot || rollbackInFlight.current) return;
    rollbackInFlight.current = true;
    setRollbackState({ kind: 'pending' });
    try {
      await restoreSnapshot(restorableSnapshot.id);
      setRollbackState(undefined);
    } catch (cause) {
      // The snapshot stays restorable and the control stays live, so the failure
      // is reported in place and the next attempt is one activation away.
      setRollbackState({ kind: 'failed', message: cause instanceof Error ? cause.message : t('common.error') });
    } finally {
      rollbackInFlight.current = false;
    }
  }, [restorableSnapshot, restoreSnapshot, t]);

  return (
    <div className="workspace-control-bar" role="toolbar" aria-label={t('sidebar.workspace')} aria-orientation="horizontal">
      {/* Session-scoped primary actions. Each one acts on the active session and
          nothing else, so each is disabled while there is no session to act on. */}
      <div role="group" aria-label={t('navigation.sessions')} className="flex shrink-0 items-center gap-1">
        <button type="button"
          onClick={handlePause}
          disabled={!hasSession || (!isRunning && !isPaused)}
          className={ICON_BUTTON}
          title={t(isPaused ? 'agents.resume' : 'agents.pause')}
          aria-label={t(isPaused ? 'agents.resume' : 'agents.pause')}
        >
          {isPaused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
        </button>
        <button type="button"
          onClick={handleStop}
          disabled={!hasSession}
          className={`${ICON_BUTTON} hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)]`}
          title={t('chat.stop_generation')}
          aria-label={t('chat.stop_generation')}
        >
          <Square size={14} aria-hidden="true" />
        </button>
        <button type="button"
          onClick={handleSnapshot}
          disabled={!hasSession}
          className={ICON_BUTTON}
          title="保存快照"
          aria-label="保存快照"
        >
          <Camera size={14} aria-hidden="true" />
        </button>
        {canRollback && (
          <button type="button"
            onClick={() => { void handleRollback(); }}
            disabled={rollbackState?.kind === 'pending'}
            aria-busy={rollbackState?.kind === 'pending'}
            className={ICON_BUTTON}
            title={rollbackLabel}
            aria-label={rollbackLabel}
          >
            <RotateCcw size={14} aria-hidden="true" />
          </button>
        )}
      </div>

      {rollbackState && (
        <span
          role={rollbackState.kind === 'failed' ? 'alert' : 'status'}
          className={`shrink-0 truncate text-[10px] ${rollbackState.kind === 'failed' ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}`}
        >
          {rollbackState.kind === 'failed' ? `回滚失败：${rollbackState.message}` : '回滚中…'}
        </span>
      )}

      <div className="flex-1" />

      {activeSession && (
        <span
          className="control-bar-session-title hidden min-w-0 max-w-[180px] truncate text-xs font-medium text-[var(--color-text-primary)] sm:block"
          title={activeSession.title || t('right_panel.summary.untitled')}
        >
          {activeSession.title || t('right_panel.summary.untitled')}
        </span>
      )}

      {activeSession && hasTokenUsage && (
        // One gauge, one number: the bar already encodes the ratio, so the
        // adjacent percentage that repeated it is gone.
        <div className="hidden shrink-0 items-center gap-1.5 px-2 lg:flex">
          <div
            className="h-1 w-20 overflow-hidden rounded-full bg-[var(--color-bg-surface-3)]"
            role="progressbar"
            aria-label={t('right_panel.summary.tokens')}
            aria-valuetext={t('right_panel.summary.token_of_limit', {
              used: usedTokens,
              limit: tokenLimit,
            })}
            aria-valuenow={tokenPercent}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full transition-[width] duration-300"
              style={{
                width: `${tokenPercent}%`,
                // Token pressure is a status, so it is the only coloured bar here.
                backgroundColor:
                  tokenPercent >= 90
                    ? 'var(--color-error)'
                    : tokenPercent >= 75
                      ? 'var(--color-warning)'
                      : 'var(--color-info)',
              }}
            />
          </div>
          <span className="font-mono text-[10px] tabular-nums text-[var(--color-text-muted)]">
            {usedTokens}
          </span>
        </div>
      )}

      {activeSession && !hasTokenUsage && (
        // No usage in the payload is a fact worth showing, not a zero to hide.
        <span className="hidden shrink-0 text-[10px] text-[var(--color-text-disabled)] lg:block">
          {t('right_panel.summary.tokens')} {t('right_panel.summary.not_reported')}
        </span>
      )}

      {activeSession && (
        // Status only. The token gauge above is the single token readout, and
        // model identity belongs to the inspector's overview group.
        <SessionStatusBadge status={activeSession.status} />
      )}

      {/* Focus mode is announced with the key that actually leaves it, which the
          layout binds to Escape whenever focus sits outside a text field. */}
      <button type="button"
        onClick={toggleFocusMode}
        aria-pressed={focusMode}
        aria-keyshortcuts="Escape"
        className={`icon-button ${
          focusMode ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
        }`}
        title={`${focusMode ? '退出专注模式' : '进入专注模式'} (Esc)`}
        aria-label={focusMode ? '退出专注模式' : '进入专注模式'}
      >
        {focusMode ? <Minimize2 size={14} aria-hidden="true" /> : <Maximize2 size={14} aria-hidden="true" />}
      </button>

      {/* The one switch that reveals the inspector; its groups and sections are
          navigated inside the panel. */}
      <button type="button"
         onClick={toggleRightPanel}
         aria-pressed={rightPanelOpen}
         aria-controls={rightPanelOpen ? 'workspace-inspector' : undefined}
         data-testid="right-panel-toggle"
        className={`icon-button shrink-0 ${
          rightPanelOpen
            ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]'
            : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
        }`}
        title={t('right_panel.title')}
        aria-label={t('right_panel.title')}
      >
        <PanelRight size={14} aria-hidden="true" />
      </button>

      <Popover.Root>
        <Popover.Trigger asChild>
          <button type="button" aria-label={t('sidebar.more')} title={t('sidebar.more')} className="icon-button shrink-0 text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">
            <MoreHorizontal size={16} aria-hidden="true" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content aria-label={t('sidebar.more')} align="end" sideOffset={8} collisionPadding={12} className="z-50 w-[min(320px,calc(100vw-24px))] max-h-[min(520px,80dvh)] overflow-y-auto rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-3 text-[var(--color-text-primary)] shadow-[var(--shadow-xl)]">
            <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] pb-3">
              <button type="button" onClick={toggleExpertMode} aria-pressed={expertMode} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-[var(--color-bg-surface-2)] aria-pressed:bg-[var(--color-accent-subtle)] aria-pressed:text-[var(--color-accent-foreground)]">
                {expertMode ? <Eye size={14} aria-hidden="true" /> : <EyeOff size={14} aria-hidden="true" />}专家模式
              </button>
            </div>
            <div className="py-3">
              <PermissionModeToggle
                value={permission.mode}
                onChange={(mode) => void permission.setMode(mode)}
                disabled={permission.loading}
                loading={permission.loading}
                error={permission.error}
                onRetry={permission.reload}
              />
            </div>
            <AutonomySlider
              value={permission.mode}
              onChange={(mode) => void permission.setMode(mode)}
              disabled={permission.loading}
            />
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
