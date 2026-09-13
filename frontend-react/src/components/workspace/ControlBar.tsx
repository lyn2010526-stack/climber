import {
  Play, Pause, Square, Camera, RotateCcw, Maximize2, Minimize2,
  FolderTree, GitBranch, Activity, Settings, Eye, EyeOff,
  FileDiff, Wrench, Brain,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { PermissionModeToggle } from './PermissionModeToggle';
import { AutonomySlider } from './AutonomySlider';
import { SessionStatusBadge } from './SessionStatusBadge';

export function ControlBar() {
  const {
    activeSessionId, sessions, rightPanelOpen, toggleRightPanel,
    rightPanelTab, setRightPanelTab, focusMode, toggleFocusMode,
    expertMode, toggleExpertMode,
    permissionMode, setPermissionMode,
    autonomyLevel, setAutonomyLevel,
    updateSession, addSnapshot, snapshots,
  } = useWorkspaceStore();

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const isRunning = activeSession?.status === 'running';
  const isPaused = activeSession?.status === 'paused';
  const tokenLimit = activeSession?.tokenUsage?.limit ?? 0;
  const tokenPercent = tokenLimit > 0
    ? Math.min(100, Math.round(((activeSession?.tokenUsage?.used ?? 0) / tokenLimit) * 100))
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
      });
    }
  };

  return (
    <div className="workspace-control-bar">
      <div className="flex items-center gap-1">
         <button
          onClick={handlePause}
          disabled={!activeSession || (!isRunning && !isPaused)}
           className="icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-30"
            title={isPaused ? '继续' : '暂停'}
            aria-label={isPaused ? '继续会话' : '暂停会话'}
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button
          onClick={handleStop}
          disabled={!activeSession}
            className="icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)] disabled:opacity-30"
          title="停止"
          aria-label="停止会话"
        >
          <Square size={14} />
        </button>
        <button
          onClick={handleSnapshot}
          disabled={!activeSession}
            className="icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-30"
           title="保存快照"
           aria-label="保存快照"
        >
          <Camera size={14} />
        </button>
         <button
            disabled={!activeSession || snapshots.filter(snapshot => snapshot.sessionId === activeSessionId).length === 0}
            className="icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-30"
           title="回滚到快照"
           aria-label="回滚到快照"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      <div className="h-6 w-px bg-[var(--color-border-subtle)] mx-1" />

      <div className="flex items-center gap-1">
        {([
          { id: 'config', icon: Settings, label: '配置', requiresSession: false },
          { id: 'diff', icon: FileDiff, label: 'Diff', requiresSession: true },
          { id: 'toolcalls', icon: Wrench, label: '工具', requiresSession: true },
          { id: 'dag', icon: GitBranch, label: 'DAG', requiresSession: false },
          { id: 'trace', icon: Activity, label: '链路', requiresSession: false },
          { id: 'reasoning', icon: Brain, label: '推理', requiresSession: true },
          { id: 'files', icon: FolderTree, label: '文件', requiresSession: false },
        ] as const).map(({ id, icon: Icon, label, requiresSession }) => {
          const isActive = rightPanelTab === id && rightPanelOpen;
          const isDisabled = requiresSession && !activeSession;
          return (
            <button
              key={id}
              onClick={() => rightPanelTab === id && rightPanelOpen ? toggleRightPanel() : setRightPanelTab(id)}
              disabled={isDisabled}
              aria-pressed={isActive}
              className={`icon-button ${
                isActive
                  ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-30 disabled:hover:bg-transparent'
              }`}
              title={isDisabled ? 'Select a session' : label}
              aria-label={`${label}面板`}
            >
              <Icon size={14} />
            </button>
          );
        })}
      </div>

      <div className="flex-1" />

      {activeSession && (
        <span
          className="control-bar-session-title max-w-[180px] truncate text-xs font-medium text-[var(--color-text-primary)]"
          title={activeSession.title || 'Untitled'}
        >
          {activeSession.title || 'Untitled'}
        </span>
      )}

      {activeSession?.tokenUsage && (
        <div className="flex items-center gap-2 mr-3">
          <span className="text-[10px] text-[var(--color-text-muted)] font-medium">Token</span>
           <div className="w-20 h-1 bg-white/10 rounded-full overflow-hidden" aria-label={`Token 使用率 ${tokenPercent}%`}>
             <div
              className={`h-full rounded-full transition-all duration-300 ${
                (activeSession.tokenUsage.used / activeSession.tokenUsage.limit) > 0.8
                  ? 'bg-amber-500'
                  : 'bg-blue-500'
              }`}
               style={{ width: `${tokenPercent}%` }}
            />
          </div>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
             {tokenPercent}%
          </span>
        </div>
      )}

      {activeSession && (
        <SessionStatusBadge
          status={activeSession.status}
          tokens={activeSession.tokenUsage?.used}
          modelName={activeSession.modelConfig?.modelId}
        />
      )}

      <div className="h-6 w-px bg-[var(--color-border-subtle)] mx-1" />

      <div className="hidden xl:contents">
        <PermissionModeToggle
          value={permissionMode}
          onChange={setPermissionMode}
        />

        <AutonomySlider
          value={autonomyLevel}
          onChange={setAutonomyLevel}
        />
      </div>

      <button
        onClick={toggleExpertMode}
        className={`icon-button ${
          expertMode ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
        }`}
        title={expertMode ? '关闭专家模式' : '开启专家模式'}
        aria-label={expertMode ? '关闭专家模式' : '开启专家模式'}
      >
        {expertMode ? <Eye size={14} /> : <EyeOff size={14} />}
      </button>

      <button
        onClick={toggleFocusMode}
        className={`icon-button ${
          focusMode ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
        }`}
          title="专注模式"
          aria-label="切换专注模式"
      >
        {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
      </button>
    </div>
  );
}
