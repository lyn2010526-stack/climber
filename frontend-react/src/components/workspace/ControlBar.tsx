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
    <div className="h-12 bg-[#0F0F14]/80 backdrop-blur-2xl border-b border-white/10 flex items-center px-4 gap-2 shadow-sm shadow-white/5">
      {/* Run controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={handlePause}
          disabled={!activeSession || (!isRunning && !isPaused)}
           className="p-2 rounded-2xl hover:bg-white/10 text-[var(--color-text-secondary)] hover:text-white transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
           title={isPaused ? '继续' : '暂停'}
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button
          onClick={handleStop}
          disabled={!activeSession}
           className="p-2 rounded-2xl hover:bg-red-500/10 text-[var(--color-text-secondary)] hover:text-red-400 transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          title="停止"
        >
          <Square size={14} />
        </button>
        <button
          onClick={handleSnapshot}
          disabled={!activeSession}
           className="p-2 rounded-2xl hover:bg-white/10 text-[var(--color-text-secondary)] hover:text-white transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
           title="保存快照"
        >
          <Camera size={14} />
        </button>
        <button
           className="p-2 rounded-2xl hover:bg-white/10 text-[var(--color-text-secondary)] hover:text-white transition-all duration-200 hover:scale-105 active:scale-95"
          title="回滚到快照"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-white/10 mx-1" />

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
            className={`p-2 rounded-2xl transition-all duration-200 ${
               rightPanelTab === id && rightPanelOpen
                 ? 'bg-white/10 text-white shadow-sm shadow-white/5 border border-white/10'
                 : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-white/5 border border-transparent'
            }`}
            title={label}
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
      <div className="w-px h-6 bg-white/10 mx-1" />

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
        className={`p-2 rounded-2xl transition-all duration-200 ${
          expertMode ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-sm shadow-purple-500/10' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-white/5 border border-transparent'
        }`}
        title={expertMode ? '关闭专家模式' : '开启专家模式'}
      >
        {expertMode ? <Eye size={14} /> : <EyeOff size={14} />}
      </button>

      {/* Focus mode */}
      <button
        onClick={toggleFocusMode}
        className={`p-2 rounded-2xl transition-all duration-200 ${
          focusMode ? 'bg-white/10 text-white shadow-sm shadow-white/5 border border-white/10' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-white/5 border border-transparent'
        }`}
          title="专注模式"
      >
        {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
      </button>
    </div>
  );
}
