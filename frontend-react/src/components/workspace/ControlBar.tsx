import {
  Play, Pause, Square, Camera, RotateCcw, Maximize2, Minimize2,
  FolderTree, GitBranch, Activity, Settings, Eye, EyeOff,
} from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkspaceStore } from '../../store/workspace';
import { PermissionModeToggle } from './PermissionModeToggle';
import { AutonomySlider } from './AutonomySlider';
import { SessionStatusBadge } from './SessionStatusBadge';

export function ControlBar() {
  const {
    activeSessionId, sessions, rightPanelOpen, rightPanelTab,
    focusMode, expertMode, permissionMode, autonomyLevel, snapshots,
  } = useWorkspaceStore(useShallow(s => ({
    activeSessionId: s.activeSessionId,
    sessions: s.sessions,
    rightPanelOpen: s.rightPanelOpen,
    rightPanelTab: s.rightPanelTab,
    focusMode: s.focusMode,
    expertMode: s.expertMode,
    permissionMode: s.permissionMode,
    autonomyLevel: s.autonomyLevel,
    snapshots: s.snapshots,
  })));
  const toggleRightPanel = useWorkspaceStore(s => s.toggleRightPanel);
  const setRightPanelTab = useWorkspaceStore(s => s.setRightPanelTab);
  const toggleFocusMode = useWorkspaceStore(s => s.toggleFocusMode);
  const toggleExpertMode = useWorkspaceStore(s => s.toggleExpertMode);
  const setPermissionMode = useWorkspaceStore(s => s.setPermissionMode);
  const setAutonomyLevel = useWorkspaceStore(s => s.setAutonomyLevel);
  const updateSession = useWorkspaceStore(s => s.updateSession);
  const addSnapshot = useWorkspaceStore(s => s.addSnapshot);

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
    <div className="h-11 flex items-center px-3 gap-1.5" style={{
      backgroundColor: 'rgba(17, 17, 19, 0.85)',
      borderBottom: '1px solid var(--color-border-subtle)',
      backdropFilter: 'blur(20px)',
    }}>
      {/* Run controls */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={handlePause}
          disabled={!activeSession || (!isRunning && !isPaused)}
          className="p-1.5 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title={isPaused ? '继续' : '暂停'}
        >
          {isPaused ? <Play size={13} /> : <Pause size={13} />}
        </button>
        <button
          onClick={handleStop}
          disabled={!activeSession}
          className="p-1.5 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.color = 'rgba(239, 68, 68, 0.9)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="停止"
        >
          <Square size={13} />
        </button>
        <button
          onClick={handleSnapshot}
          disabled={!activeSession}
          className="p-1.5 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="保存快照"
        >
          <Camera size={13} />
        </button>
        <button
          className="p-1.5 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="回滚到快照"
        >
          <RotateCcw size={13} />
        </button>
      </div>

      {/* Divider */}
      <div className="w-px h-5 mx-1" style={{ backgroundColor: 'var(--color-border-subtle)' }} />

      {/* Right panel tabs */}
      <div className="flex items-center gap-0.5">
        {([
          { id: 'config', icon: Settings, label: '配置' },
          { id: 'dag', icon: GitBranch, label: 'DAG' },
          { id: 'trace', icon: Activity, label: '链路' },
          { id: 'files', icon: FolderTree, label: '文件' },
        ] as const).map(({ id, icon: Icon, label }) => {
          const isActive = rightPanelTab === id && rightPanelOpen;
          return (
            <button
              key={id}
              onClick={() => isActive ? toggleRightPanel() : setRightPanelTab(id)}
              className="p-1.5 rounded-lg transition-all duration-200"
              style={{
                color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)',
                backgroundColor: isActive ? 'var(--color-accent-subtle)' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                  e.currentTarget.style.color = 'var(--color-text-secondary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--color-text-muted)';
                }
              }}
              title={label}
            >
              <Icon size={13} />
            </button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Token gauge */}
      {activeSession?.tokenUsage && (
        <div className="flex items-center gap-2 mr-2">
          <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-muted)' }}>Token</span>
          <div className="w-16 h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-bg-surface-3)' }}>
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${Math.min((activeSession.tokenUsage.used / activeSession.tokenUsage.limit) * 100, 100)}%`,
                backgroundColor: (activeSession.tokenUsage.used / activeSession.tokenUsage.limit) > 0.8
                  ? 'var(--color-warning)'
                  : 'var(--color-accent)',
              }}
            />
          </div>
          <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-muted)' }}>
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
      <div className="w-px h-5 mx-1" style={{ backgroundColor: 'var(--color-border-subtle)' }} />

      {/* Permission mode */}
      <PermissionModeToggle
        value={permissionMode}
        onChange={setPermissionMode}
      />

      {/* Autonomy level */}
      <AutonomySlider
        value={autonomyLevel}
        onChange={setAutonomyLevel}
      />

      {/* Expert mode */}
      <button
        onClick={toggleExpertMode}
        className="p-1.5 rounded-lg transition-all duration-200"
        style={{
          color: expertMode ? 'var(--color-accent)' : 'var(--color-text-muted)',
          backgroundColor: expertMode ? 'var(--color-accent-subtle)' : 'transparent',
        }}
        onMouseEnter={(e) => {
          if (!expertMode) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
            e.currentTarget.style.color = 'var(--color-text-secondary)';
          }
        }}
        onMouseLeave={(e) => {
          if (!expertMode) {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-text-muted)';
          }
        }}
        title={expertMode ? '关闭专家模式' : '开启专家模式'}
      >
        {expertMode ? <Eye size={13} /> : <EyeOff size={13} />}
      </button>

      {/* Focus mode */}
      <button
        onClick={toggleFocusMode}
        className="p-1.5 rounded-lg transition-all duration-200"
        style={{
          color: focusMode ? 'var(--color-accent)' : 'var(--color-text-muted)',
          backgroundColor: focusMode ? 'var(--color-accent-subtle)' : 'transparent',
        }}
        onMouseEnter={(e) => {
          if (!focusMode) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
            e.currentTarget.style.color = 'var(--color-text-secondary)';
          }
        }}
        onMouseLeave={(e) => {
          if (!focusMode) {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-text-muted)';
          }
        }}
        title="专注模式"
      >
        {focusMode ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
      </button>
    </div>
  );
}