import {
  Settings, GitBranch, Activity, FolderTree,
  Brain, FileDiff, Wrench, X, ListTodo,
} from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkspaceStore } from '../../store/workspace';
import { ReasoningPanel } from './ReasoningPanel';
import { TaskQueuePanel } from './TaskQueuePanel';
import { ConfigPanel } from './right-panel/ConfigPanel';
import { DiffPanelTab } from './right-panel/DiffPanelTab';
import { ToolCallsTab } from './right-panel/ToolCallsTab';
import { DAGPanel } from './right-panel/DAGPanel';
import { TracePanel } from './right-panel/TracePanel';
import { FilesPanel } from './right-panel/FilesPanel';

export function RightPanel() {
  const { rightPanelTab, rightPanelOpen, activeSessionId, sessions } = useWorkspaceStore(useShallow(s => ({
    rightPanelTab: s.rightPanelTab,
    rightPanelOpen: s.rightPanelOpen,
    activeSessionId: s.activeSessionId,
    sessions: s.sessions,
  })));
  const setRightPanelTab = useWorkspaceStore(s => s.setRightPanelTab);
  const toggleRightPanel = useWorkspaceStore(s => s.toggleRightPanel);

  if (!rightPanelOpen) return null;

  const activeSession = sessions.find(s => s.id === activeSessionId);

  const tabs = [
    { id: 'toolcalls' as const, icon: Wrench, label: '工具' },
    { id: 'reasoning' as const, icon: Brain, label: '推理' },
    { id: 'config' as const, icon: Settings, label: '配置' },
    { id: 'diff' as const, icon: FileDiff, label: 'Diff' },
    { id: 'dag' as const, icon: GitBranch, label: 'DAG' },
    { id: 'trace' as const, icon: Activity, label: '链路' },
    { id: 'files' as const, icon: FolderTree, label: '文件' },
    { id: 'tasks' as const, icon: ListTodo, label: '任务' },
  ];

  return (
    <aside className="flex h-full w-full min-w-0 flex-col backdrop-blur-2xl" style={{ backgroundColor: 'var(--color-glass-bg)', borderLeft: '1px solid var(--color-border-subtle)' }} aria-label="Agent 工作区">
      <div className="flex h-10 shrink-0 items-center justify-between px-3" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
        <div>
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>Agent 工作区</p>
           <p className="max-w-[170px] truncate text-[10px]" style={{ color: 'var(--color-text-muted)' }}>{activeSession ? activeSession.title : '等待会话'}</p>
        </div>
        <button type="button" onClick={toggleRightPanel} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--color-bg-surface-2)]" style={{ color: 'var(--color-text-muted)' }} aria-label="关闭 Agent 工作区" title="关闭工作区">
          <X size={14} />
        </button>
      </div>
      <div className="flex shrink-0 overflow-x-auto" style={{ borderBottom: '1px solid var(--color-border-subtle)' }} role="tablist" aria-label="工作区视图">
        {tabs.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            id={`workspace-tab-${id}`}
            type="button"
            onClick={() => setRightPanelTab(id)}
            className={`relative flex min-w-[52px] shrink-0 flex-col items-center justify-center gap-1 py-2 text-[9px] font-medium transition-colors ${
              rightPanelTab === id
                 ? 'text-[var(--color-text-primary)]'
                 : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            }`}
            role="tab"
            aria-selected={rightPanelTab === id}
            aria-controls={`workspace-panel-${id}`}
            tabIndex={rightPanelTab === id ? 0 : -1}
            title={label}
          >
            <Icon size={13} />
            <span className="max-w-full truncate">{label}</span>
            {rightPanelTab === id && (
              <div className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-[var(--color-accent)]" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div id={`workspace-panel-${rightPanelTab}`} className="flex-1 overflow-y-auto p-3" role="tabpanel" aria-labelledby={`workspace-tab-${rightPanelTab}`} tabIndex={0}>
        {rightPanelTab === 'config' && <ConfigPanel session={activeSession} />}
        {rightPanelTab === 'diff' && <DiffPanelTab sessionId={activeSessionId} />}
        {rightPanelTab === 'toolcalls' && <ToolCallsTab sessionId={activeSessionId} />}
        {rightPanelTab === 'dag' && <DAGPanel />}
        {rightPanelTab === 'trace' && <TracePanel />}
        {rightPanelTab === 'reasoning' && <ReasoningPanel />}
        {rightPanelTab === 'files' && <FilesPanel />}
        {rightPanelTab === 'tasks' && <TaskQueuePanel />}
      </div>
    </aside>
  );
}
