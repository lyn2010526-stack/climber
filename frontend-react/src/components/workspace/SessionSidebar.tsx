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
    <div className="w-60 bg-[#0F0F14]/95 backdrop-blur-2xl border-r border-white/[0.04] flex flex-col">
      {/* Permission Mode Selector */}
      <div className="p-3 border-b border-white/[0.04]">
        <PermissionModes
          currentMode={permissionMode}
          onModeChange={setPermissionMode}
        />
      </div>

      {/* Header — New Chat Button */}
      <div className="p-3 border-b border-white/[0.04] space-y-2">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] hover:from-[#60A5FA] hover:to-[#A78BFA] disabled:opacity-50 text-white rounded-2xl text-xs font-semibold transition-all duration-200 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 active:scale-[0.97] hover:translate-y-[-1px]"
        >
          <Plus size={14} strokeWidth={2.5} /> {creating ? '创建中...' : '新建会话'}
        </button>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-2xl text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/40 focus:bg-white/[0.06] transition-all duration-200 hover:border-white/[0.1]"
        >
          {agents.length === 0 && <option value="">暂无可用智能体</option>}
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-2xl text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/40 focus:bg-white/[0.06] transition-all duration-200 hover:border-white/[0.1]"
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
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {loading && (
          <div className="text-center py-8">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <span className="text-[10px] text-[var(--color-text-muted)]">加载中...</span>
          </div>
        )}
        {sessions.map((s, idx) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-2xl cursor-pointer transition-all duration-200 border ${
              activeSessionId === s.id
                ? 'bg-white/[0.06] text-white shadow-md shadow-black/20 border-white/[0.08]'
                : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/[0.03] border-transparent hover:border-white/[0.04]'
            }`}
            style={{ animationDelay: `${Math.min(idx, 8) * 40}ms` }}
            onClick={() => setActiveSession(s.id)}
          >
            <MessageSquare size={13} className={`shrink-0 transition-all duration-200 ${activeSessionId === s.id ? 'text-blue-400' : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]'}`} />
            <div className="flex-1 min-w-0">
              <span className="text-xs truncate block font-medium">{s.title || 'Untitled'}</span>
              <span className="text-[10px] text-[var(--color-text-muted)] font-medium">{s.status || 'idle'}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
              className="opacity-0 group-hover:opacity-100 p-1.5 hover:text-red-400 transition-all duration-200 hover:bg-red-500/10 rounded-xl hover:scale-110"
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
        <div className="border-t border-white/[0.04] p-3 space-y-2 max-h-48 overflow-y-auto">
          <div className="flex items-center gap-2 px-1">
            <History size={12} className="text-blue-400" />
            <span className="text-[11px] font-medium text-[var(--color-text-secondary)]">检查点历史</span>
          </div>
          {(sessions.find(s => s.id === activeSessionId) as any)?.messages?.slice(-10).reverse().map((msg: any, i: number) => (
            <div key={i} className="px-2 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-[10px] text-[var(--color-text-secondary)]">
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
      <div className="border-t border-white/[0.04] p-3">
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => setShowCheckpoints(!showCheckpoints)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-medium transition-colors ${
              showCheckpoints
                ? 'bg-blue-500/10 text-blue-400'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-white/[0.04]'
            }`}
          >
            <History size={10} />
            检查点历史
          </button>
        </div>
        <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-[var(--color-text-muted)] font-medium">
          <Sparkles size={10} className="text-blue-400" />
          <span>{sessions.length} 个活跃会话</span>
        </div>
        <UserSwitcher />
      </div>
    </div>
  );
}
