import {
  Play, Pause, Square, Camera, RotateCcw, Maximize2, Minimize2,
  FolderTree, GitBranch, Activity, Settings, Eye, EyeOff,
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
      {/* Run controls */}
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
            className="icon-button text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]"
           title="回滚到快照"
           aria-label="回滚到快照"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-[var(--color-border-subtle)] mx-1" />

      {/* Right panel tabs */}
      <div className="flex items-center gap-1">
        {([
          { id: 'config', icon: Settings, label: '配置' },
          { id: 'dag', icon: GitBranch, label: 'DAG' },
          { id: 'trace', icon: Activity, label: '链路' },
          { id: 'files', icon: FolderTree, label: '文件' },
        ] as const).map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => rightPanelTab === id && rightPanelOpen ? toggleRightPanel() : setRightPanelTab(id)}
            className={`icon-button ${
               rightPanelTab === id && rightPanelOpen
                  ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
            }`}
             title={label}
             aria-label={`${label}面板`}
          >
            <Icon size={14} />
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Token gauge */}
      {activeSession?.tokenUsage && (
        <div className="flex items-center gap-2 mr-3">
          <span className="text-[10px] text-[var(--color-text-muted)] font-medium">Token</span>
          <div className="w-20 h-1 bg-white/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                (activeSession.tokenUsage.used / activeSession.tokenUsage.limit) > 0.8
                  ? 'bg-amber-500'
                  : 'bg-blue-500'
              }`}
              style={{ width: `${(activeSession.tokenUsage.used / activeSession.tokenUsage.limit) * 100}%` }}
            />
          </div>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            {Math.round((activeSession.tokenUsage.used / activeSession.tokenUsage.limit) * 100)}%
          </span>
        </div>
      )}

      {/* Session status */}
      {activeSession && (
        <SessionStatusBadge
          status={activeSession.status}
          tokens={activeSession.tokenUsage?.used}
          modelName={activeSession.modelConfig?.modelId}
        />
      )}

      {/* Divider */}
      <div className="h-6 w-px bg-[var(--color-border-subtle)] mx-1" />

      {/* Permission mode */}
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

      {/* Expert mode */}
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

      {/* Focus mode */}
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
