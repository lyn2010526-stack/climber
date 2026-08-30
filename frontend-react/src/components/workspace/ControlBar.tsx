import { useState, useRef, useEffect } from 'react';
import {
  Play, Pause, Square, Camera, RotateCcw, Settings,
  FolderTree, GitBranch, Activity, Eye, EyeOff,
  ChevronDown, Maximize2, Minimize2, MessageSquare,
} from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkspaceStore } from '../../store/workspace';
import { PermissionModeToggle } from './PermissionModeToggle';
import { EnginePermissionModeToggle } from './EnginePermissionModeToggle';
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

  // toggle 样式按钮的公共类：未激活时 muted 色 + hover 反馈，激活时 accent 色
  const toggleBtnClass = (active: boolean) =>
    `p-2 rounded-lg transition-all duration-200 ${
      active
        ? 'text-[var(--color-accent)] bg-[var(--color-accent-subtle)]'
        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
    }`;

  return (
    <div className="flex h-11 items-center gap-1.5 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3">
      <div className="flex items-center gap-0.5">
        {onToggleSessions && (
          <button onClick={onToggleSessions}
            className="p-2 rounded-lg transition-all duration-200 active:scale-95 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]"
            title="会话列表"
            aria-label="打开会话列表"
          >
            <MessageSquare size={14} />
          </button>
        )}
        <button
          onClick={handlePause}
          disabled={!activeSession || (!isRunning && !isPaused)}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]"
          title={isPaused ? '继续' : '暂停'}
          aria-label={isPaused ? '继续会话' : '暂停会话'}
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button
          onClick={handleStop}
          disabled={!activeSession}
          className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95 text-[var(--color-text-secondary)] hover:text-[var(--color-error)] hover:bg-[var(--color-error-subtle)]"
          title="停止"
          aria-label="停止会话"
        >
          <Square size={14} />
        </button>
        <div className="hidden items-center gap-0.5 lg:flex">
          <div className="w-px h-4 mx-0.5 bg-[var(--color-border-subtle)]" />
          <button
            onClick={handleSnapshot}
            disabled={!activeSession}
            className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]"
            title="保存快照"
            aria-label="保存快照"
          >
            <Camera size={14} />
          </button>
          <button
            onClick={handleRollback}
            disabled={!activeSession || snapshots.length === 0}
            className="p-2 rounded-lg transition-all duration-200 disabled:opacity-30 hover:scale-105 active:scale-95 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]"
            title="回滚到快照"
            aria-label="回滚到快照"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center gap-2 min-w-0">
        {activeSession ? (
          <>
            <span className="text-xs font-medium truncate max-w-[200px] text-[var(--color-text-primary)]">
              {activeSession.title || '未命名会话'}
            </span>
            <SessionStatusBadge
              status={activeSession.status}
              tokens={activeSession.tokenUsage?.used}
              modelName={activeSession.modelConfig?.modelId}
            />
          </>
        ) : (
          <span className="text-xs text-[var(--color-text-secondary)]">选择或创建一个会话</span>
        )}
      </div>

      <div className="flex items-center gap-0.5">
        {activeSession?.tokenUsage && (() => {
          const tokenRatio = activeSession.tokenUsage.limit > 0
            ? (activeSession.tokenUsage.used / activeSession.tokenUsage.limit)
            : 0;
          return (
            <div className="hidden xl:flex items-center gap-1.5 mr-1">
              <span className="text-[10px] font-medium text-[var(--color-text-muted)]">Token</span>
              <div className="w-12 h-1 rounded-full overflow-hidden bg-[var(--color-bg-surface-3)]">
                <div
                  className="h-full rounded-full transition-all duration-300 bg-[var(--color-accent)] data-[warn=true]:bg-[var(--color-warning)]"
                  data-warn={tokenRatio > 0.8}
                  style={{ width: `${Math.min(tokenRatio * 100, 100)}%` }}
                />
              </div>
              <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                {Math.round(tokenRatio * 100)}%
              </span>
            </div>
          );
        })()}

        <div className="hidden items-center gap-0.5 md:flex">
          <div className="w-px h-4 mx-0.5 bg-[var(--color-border-subtle)]" />
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
                className={toggleBtnClass(isActive)}
                title={label}
                aria-label={`${label}面板`}
                aria-pressed={isActive}
              >
                <Icon size={14} />
              </button>
            );
          })}
          <div className="w-px h-4 mx-0.5 bg-[var(--color-border-subtle)]" />
        </div>

        <button
          onClick={toggleFocusMode}
          className={toggleBtnClass(focusMode)}
          title="专注模式"
          aria-label={focusMode ? '退出专注模式' : '进入专注模式'}
          aria-pressed={focusMode}
        >
          {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>

        <div ref={settingsRef} className="relative">
          <button
            onClick={() => setSettingsOpen(!settingsOpen)}
            className={`flex items-center gap-0.5 px-1.5 py-1.5 rounded-lg transition-all duration-200 ${
              settingsOpen
                ? 'text-[var(--color-accent)] bg-[var(--color-accent-subtle)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
            }`}
            title="更多设置"
            aria-label="更多设置"
            aria-expanded={settingsOpen}
            aria-haspopup="menu"
          >
            <Settings size={14} />
            <ChevronDown size={10} className={`transition-transform duration-200 ${settingsOpen ? 'rotate-180' : ''}`} />
          </button>

          {settingsOpen && (
            <div
              className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-3 shadow-[var(--shadow-lg)]"
            >
              <div className="space-y-3">
                <div>
                  <div className="text-[10px] font-medium mb-1.5 text-[var(--color-text-muted)]">执行环境</div>
                  <PermissionModeToggle value={permissionMode} onChange={setPermissionMode} />
                </div>

                <div>
                  <div className="text-[10px] font-medium mb-1.5 text-[var(--color-text-muted)]">执行模式</div>
                  <EnginePermissionModeToggle />
                </div>

                <div>
                  <div className="text-[10px] font-medium mb-1.5 text-[var(--color-text-muted)]">自主性</div>
                  <AutonomySlider value={autonomyLevel} onChange={setAutonomyLevel} />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-secondary)]">专家模式</span>
                  <button
                    onClick={toggleExpertMode}
                    className={toggleBtnClass(expertMode)}
                    title={expertMode ? '关闭专家模式' : '开启专家模式'}
                    aria-label={expertMode ? '关闭专家模式' : '开启专家模式'}
                    aria-pressed={expertMode}
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
