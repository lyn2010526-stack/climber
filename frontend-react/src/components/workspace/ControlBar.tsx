import { useState, useRef, useEffect } from 'react';
import {
  Play, Pause, Square, Camera, RotateCcw, Settings,
  FolderTree, GitBranch, Activity, Eye, EyeOff,
  ChevronDown, Maximize2, Minimize2, MessageSquare,
} from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkspaceStore } from '../../store/workspace';
import { PermissionModeToggle } from './PermissionModeToggle';
import { AutonomySlider } from './AutonomySlider';
import { SessionStatusBadge } from './SessionStatusBadge';

export function ControlBar({ onToggleSessions }: { onToggleSessions?: () => void }) {
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

  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
        id: `snap-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sessionId: activeSessionId,
        timestamp: Date.now(),
        label: `Snapshot ${snapshots.length + 1}`,
      });
    }
  };

  const handleRollback = () => {
    if (activeSessionId && snapshots.length > 0) {
      updateSession(activeSessionId, { status: 'idle' });
    }
  };

  return (
    <div className="h-11 flex items-center px-3 gap-1.5" style={{
      backgroundColor: 'var(--color-glass-bg)',
      borderBottom: '1px solid var(--color-border-subtle)',
      backdropFilter: 'blur(20px)',
    }}>
      <div className="flex items-center gap-0.5">
        {onToggleSessions && (
          <button onClick={onToggleSessions}
            className="p-2 rounded-lg transition-all duration-200 active:scale-95"
            style={{ color: 'var(--color-text-secondary)' }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
            title="会话列表"
          >
            <MessageSquare size={14} />
          </button>
        )}
        <button
          onClick={handlePause}
          disabled={!activeSession || (!isRunning && !isPaused)}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title={isPaused ? '继续' : '暂停'}
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button
          onClick={handleStop}
          disabled={!activeSession}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; e.currentTarget.style.color = 'rgba(239, 68, 68, 0.9)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="停止"
        >
          <Square size={14} />
        </button>
        <div className="w-px h-4 mx-0.5" style={{ backgroundColor: 'var(--color-border-subtle)' }} />
        <button
          onClick={handleSnapshot}
          disabled={!activeSession}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="保存快照"
        >
          <Camera size={14} />
        </button>
        <button
          onClick={handleRollback}
          disabled={!activeSession || snapshots.length === 0}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95"
          style={{ color: 'var(--color-text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          title="回滚到快照"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center gap-2 min-w-0">
        {activeSession ? (
          <>
            <span className="text-xs font-medium truncate max-w-[200px]" style={{ color: 'var(--color-text-primary)' }}>
              {activeSession.title || '未命名会话'}
            </span>
            <SessionStatusBadge
              status={activeSession.status}
              tokens={activeSession.tokenUsage?.used}
              modelName={activeSession.modelConfig?.modelId}
            />
          </>
        ) : (
          <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>选择或创建一个会话</span>
        )}
      </div>

      <div className="flex items-center gap-0.5">
        {activeSession?.tokenUsage && (() => {
          const tokenRatio = activeSession.tokenUsage.limit > 0
            ? (activeSession.tokenUsage.used / activeSession.tokenUsage.limit)
            : 0;
          return (
            <div className="flex items-center gap-1.5 mr-1">
              <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-muted)' }}>Token</span>
              <div className="w-12 h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-bg-surface-3)' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${Math.min(tokenRatio * 100, 100)}%`,
                    backgroundColor: tokenRatio > 0.8
                      ? 'var(--color-warning)'
                      : 'var(--color-accent)',
                  }}
                />
              </div>
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-muted)' }}>
                {Math.round(tokenRatio * 100)}%
              </span>
            </div>
          );
        })()}

        <div className="w-px h-4 mx-0.5" style={{ backgroundColor: 'var(--color-border-subtle)' }} />

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
              className="p-2 rounded-lg transition-all duration-200"
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
              <Icon size={14} />
            </button>
          );
        })}

        <div className="w-px h-4 mx-0.5" style={{ backgroundColor: 'var(--color-border-subtle)' }} />

        <button
          onClick={toggleFocusMode}
          className="p-2 rounded-lg transition-all duration-200"
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
          {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>

        <div ref={settingsRef} className="relative">
          <button
            onClick={() => setSettingsOpen(!settingsOpen)}
            className="flex items-center gap-0.5 px-1.5 py-1.5 rounded-lg transition-all duration-200"
            style={{
              color: settingsOpen ? 'var(--color-accent)' : 'var(--color-text-muted)',
              backgroundColor: settingsOpen ? 'var(--color-accent-subtle)' : 'transparent',
            }}
            onMouseEnter={(e) => {
              if (!settingsOpen) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }
            }}
            onMouseLeave={(e) => {
              if (!settingsOpen) {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-muted)';
              }
            }}
            title="更多设置"
          >
            <Settings size={14} />
            <ChevronDown size={10} className={`transition-transform duration-200 ${settingsOpen ? 'rotate-180' : ''}`} />
          </button>

          {settingsOpen && (
            <div
              className="absolute right-0 top-full mt-1 w-56 p-3 rounded-xl z-50"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-default)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              }}
            >
              <div className="space-y-3">
                <div>
                  <div className="text-[10px] font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>权限模式</div>
                  <PermissionModeToggle value={permissionMode} onChange={setPermissionMode} />
                </div>

                <div>
                  <div className="text-[10px] font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>自主性</div>
                  <AutonomySlider value={autonomyLevel} onChange={setAutonomyLevel} />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>专家模式</span>
                  <button
                    onClick={toggleExpertMode}
                    className="p-2 rounded-lg transition-all duration-200"
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
                    {expertMode ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
