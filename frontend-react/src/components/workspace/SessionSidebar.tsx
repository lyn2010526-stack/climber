import { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare, Plus, Trash2, Sparkles, History,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useSessions } from '../../stores/useSessions';
import { api } from '../../api';
import { UserSwitcher } from './UserSwitcher';
import { PermissionModes } from '../agent/PermissionModes';
import type { PermissionMode } from '../agent/PermissionModes';

export function SessionSidebar() {
  const { activeSessionId, setActiveSession } = useWorkspaceStore();
  const { sessions, loading, createSession, deleteSession, refresh } = useSessions();

  const [agents, setAgents] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [creating, setCreating] = useState(false);
  const [permissionMode, setPermissionMode] = useState<PermissionMode>('manual');
  const [showCheckpoints, setShowCheckpoints] = useState(false);

  useEffect(() => {
    api.listAgents().then((data) => {
      setAgents(data);
      if (data.length > 0) setSelectedAgent(data[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    api.listModels().then((data) => {
      setModels(data);
      if (data.length > 0) setSelectedModel(data[0].id || data[0].model_id);
    }).catch(() => {});
  }, []);

  const handleCreate = useCallback(async () => {
    if (!selectedAgent || creating) return;
    setCreating(true);
    try {
      await createSession({ title: `会话 ${sessions.length + 1}`, agent_id: selectedAgent });
      await refresh();
    } finally {
      setCreating(false);
    }
  }, [selectedAgent, creating, sessions.length, createSession, refresh]);

  return (
    <aside className="session-sidebar" aria-label="会话">
      {/* Permission Mode Selector */}
      <div className="border-b border-[var(--color-border-subtle)] p-3">
        <PermissionModes
          currentMode={permissionMode}
          onModeChange={setPermissionMode}
        />
      </div>

      {/* Header — New Chat Button */}
      <div className="space-y-2 border-b border-[var(--color-border-subtle)] p-3">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] px-3 text-xs font-medium text-white transition-colors hover:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus size={14} strokeWidth={2.5} /> {creating ? '创建中...' : '新建会话'}
        </button>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          aria-label="选择智能体"
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
        >
          {agents.length === 0 && <option value="">暂无可用智能体</option>}
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          aria-label="选择模型"
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
        >
          {models.length === 0 && <option value="">暂无可用模型</option>}
          {models.map(m => (
            <option key={m.id || m.model_id} value={m.id || m.model_id}>
              {m.name || m.model_id || m.id}
            </option>
          ))}
        </select>
      </div>

      {/* Session list */}
      <div className="flex-1 space-y-0.5 overflow-y-auto p-2" aria-live="polite" aria-busy={loading}>
        {loading && (
          <div className="text-center py-8">
            <div className="mx-auto mb-2 h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent" />
            <span className="text-[10px] text-[var(--color-text-muted)]">加载中...</span>
          </div>
        )}
        {sessions.map((s, idx) => (
          <div
            key={s.id}
            className={`group flex min-h-11 w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition-colors ${
              activeSessionId === s.id
                ? 'border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]'
                : 'border-transparent text-[var(--color-text-secondary)] hover:border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]'
            }`}
            style={{ animationDelay: `${Math.min(idx, 8) * 40}ms` }}
          >
             <button
               type="button"
               aria-current={activeSessionId === s.id ? 'true' : undefined}
               onClick={() => setActiveSession(s.id)}
               className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
             >
               <MessageSquare size={13} className={`shrink-0 ${activeSessionId === s.id ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'}`} />
               <span className="min-w-0 flex-1">
                 <span className="block truncate text-xs font-medium">{s.title || 'Untitled'}</span>
                 <span className="block text-[10px] font-medium text-[var(--color-text-muted)]">{s.status || 'idle'}</span>
               </span>
             </button>
            <button
              onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
               aria-label={`删除会话 ${s.title || 'Untitled'}`}
                className="flex h-11 w-11 items-center justify-center rounded-md text-[var(--color-text-muted)] opacity-0 transition-colors hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)] group-hover:opacity-100 group-focus-within:opacity-100"
            >
              <Trash2 size={10} />
            </button>
           </div>
        ))}
        {!loading && sessions.length === 0 && (
          <div className="text-center py-8">
            <span className="text-[10px] text-[var(--color-text-muted)]">暂无会话</span>
          </div>
        )}
      </div>

      {/* Checkpoint History Panel */}
      {showCheckpoints && (
        <div className="max-h-48 space-y-2 overflow-y-auto border-t border-[var(--color-border-subtle)] p-3">
          <div className="flex items-center gap-2 px-1">
            <History size={12} className="text-[var(--color-accent)]" />
            <span className="text-[11px] font-medium text-[var(--color-text-secondary)]">检查点历史</span>
          </div>
          {(sessions.find(s => s.id === activeSessionId) as any)?.messages?.slice(-10).reverse().map((msg: any, i: number) => (
            <div key={i} className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2 py-1.5 text-[10px] text-[var(--color-text-secondary)]">
              <span className="text-[var(--color-text-muted)]">{new Date(msg.timestamp).toLocaleTimeString()}</span>
              <span className="ml-2">{msg.type}</span>
            </div>
          ))}
          {(!(sessions.find(s => s.id === activeSessionId) as any)?.messages?.length) && (
            <p className="text-[10px] text-[var(--color-text-muted)] text-center py-2">暂无检查点</p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="border-t border-[var(--color-border-subtle)] p-3">
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => setShowCheckpoints(!showCheckpoints)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-medium transition-colors ${
              showCheckpoints
                ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <History size={10} />
            检查点历史
          </button>
        </div>
        <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-[var(--color-text-muted)] font-medium">
          <Sparkles size={10} className="text-[var(--color-accent)]" />
          <span>{sessions.length} 个活跃会话</span>
        </div>
        <UserSwitcher />
      </div>
    </aside>
  );
}
