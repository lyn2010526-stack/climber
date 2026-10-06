import * as Popover from '@radix-ui/react-popover';
import { useCallback, useRef, useState } from 'react';
import {
  Play, Pause, Square, Camera, RotateCcw, Maximize2, Minimize2, PanelRight, Eye, EyeOff, MoreHorizontal,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useI18n } from '../../i18n';
import { PermissionModeToggle } from './PermissionModeToggle';
import { usePermissionConfig } from './usePermissionConfig';
import { SessionStatusBadge } from './SessionStatusBadge';
import './codex-suite.css';

const ICON_BUTTON = 'icon-button cx-bar-btn';

export interface ControlBarProps {
  /** Anchored mounts the slim variant at the top of the chat column. */
  variant?: 'full' | 'slim';
}

/**
 * Session actions for the anchored workspace: the controls that act on the
 * active session (pause/stop, snapshot & rollback), the expert / focus
 * switches and the permission-mode popover. `variant="slim"` keeps the bar to
 * those anchored capabilities on a 40px strip; `variant="full"` is the
 * legacy 52px bar kept for its own test harness.
 */
export function ControlBar({ variant = 'full' }: ControlBarProps) {
  const { t } = useI18n();
  const {
    activeSessionId, sessions,
    rightPanelOpen, toggleRightPanel,
    focusMode, toggleFocusMode,
    expertMode, toggleExpertMode,
    updateSession, addSnapshot, restoreSnapshot, snapshots,
  } = useWorkspaceStore();
  const permission = usePermissionConfig();
  const slim = variant === 'slim';

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
    ? t('anchored.controlbar.restore_named', { name: restorableSnapshot.label })
    : t('anchored.controlbar.restore_snapshot');
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
    <div
      className={slim
        ? 'flex h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-2'
        : 'workspace-control-bar'}
      role="toolbar"
      aria-label={t('sidebar.workspace')}
      aria-orientation="horizontal"
      data-testid={slim ? 'anchored-control-bar' : undefined}
      data-variant={slim ? 'slim' : 'full'}
    >
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
          className={`${ICON_BUTTON} cx-bar-btn-danger`}
          title={t('chat.stop_generation')}
          aria-label={t('chat.stop_generation')}
        >
          <Square size={14} aria-hidden="true" />
        </button>
        <button type="button"
          onClick={handleSnapshot}
          disabled={!hasSession}
          className={ICON_BUTTON}
          title={t('anchored.controlbar.save_snapshot')}
          aria-label={t('anchored.controlbar.save_snapshot')}
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
          className={`cx-pill shrink-0 truncate ${rollbackState.kind === 'failed' ? 'text-[var(--color-error)]' : ''}`}
        >
          {rollbackState.kind === 'failed' ? t('anchored.controlbar.rollback_failed', { message: rollbackState.message }) : t('anchored.controlbar.rolling_back')}
        </span>
      )}

      <div className="flex-1" />

      {!slim && activeSession && (
        <span
          className="control-bar-session-title hidden min-w-0 max-w-[180px] truncate text-[13px] font-medium text-[var(--color-text-primary)] sm:block"
          title={activeSession.title || t('right_panel.summary.untitled')}
        >
          {activeSession.title || t('right_panel.summary.untitled')}
        </span>
      )}

      {!slim && activeSession && hasTokenUsage && (
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
          <span className="cx-mono text-[10px] text-[var(--color-text-muted)]">
            {usedTokens}
          </span>
        </div>
      )}

      {!slim && activeSession && !hasTokenUsage && (
        // No usage in the payload is a fact worth showing, not a zero to hide.
        <span className="hidden shrink-0 text-[10px] text-[var(--color-text-disabled)] lg:block">
          {t('right_panel.summary.tokens')} {t('right_panel.summary.not_reported')}
        </span>
      )}

      {!slim && activeSession && (
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
        className={`icon-button cx-bar-btn ${
          focusMode ? '' : 'text-[var(--color-text-muted)]'
        }`}
        title={focusMode ? t('anchored.controlbar.focus_shortcut', { label: t('anchored.controlbar.exit_focus') }) : t('anchored.controlbar.focus_shortcut', { label: t('anchored.controlbar.enter_focus') })}
        aria-label={focusMode ? t('anchored.controlbar.exit_focus') : t('anchored.controlbar.enter_focus')}
      >
        {focusMode ? <Minimize2 size={14} aria-hidden="true" /> : <Maximize2 size={14} aria-hidden="true" />}
      </button>

      {/* The one switch that reveals the inspector; only the legacy full bar
          carries it — anchored owns its own inspect toggle. */}
      {!slim && (
        <button type="button"
          onClick={toggleRightPanel}
          aria-pressed={rightPanelOpen}
          aria-controls={rightPanelOpen ? 'workspace-inspector' : undefined}
          data-testid="right-panel-toggle"
          className={`icon-button cx-bar-btn shrink-0 ${
            rightPanelOpen ? '' : 'text-[var(--color-text-muted)]'
          }`}
          title={t('right_panel.title')}
          aria-label={t('right_panel.title')}
        >
          <PanelRight size={14} aria-hidden="true" />
        </button>
      )}

      <Popover.Root>
        <Popover.Trigger asChild>
          <button type="button" aria-label={t('sidebar.more')} title={t('sidebar.more')} className="icon-button cx-bar-btn shrink-0 text-[var(--color-text-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">
            <MoreHorizontal size={16} aria-hidden="true" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content aria-label={t('sidebar.more')} align="end" sideOffset={8} collisionPadding={12} className="z-50 w-[min(320px,calc(100vw-24px))] max-h-[min(520px,80dvh)] overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-3 text-[var(--color-text-primary)] shadow-[var(--shadow-xl)]">
            <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] pb-3">
              <button type="button" onClick={toggleExpertMode} aria-pressed={expertMode} className="cx-chip">
                {expertMode ? <Eye size={14} aria-hidden="true" /> : <EyeOff size={14} aria-hidden="true" />}{t('anchored.controlbar.expert')}
              </button>
            </div>
            <div className="pt-3">
              <PermissionModeToggle
                value={permission.mode}
                onChange={(mode) => void permission.setMode(mode)}
                disabled={permission.loading}
                loading={permission.loading}
                error={permission.error}
                onRetry={permission.reload}
              />
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
