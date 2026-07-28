import { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare, Plus, Trash2, Sparkles,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useSessions } from '../../stores/useSessions';
import { api } from '../../api';
import { UserSwitcher } from './UserSwitcher';

export function SessionSidebar() {
  const { activeSessionId, setActiveSession } = useWorkspaceStore();
  const { sessions, loading, createSession, deleteSession, refresh } = useSessions();

  const [agents, setAgents] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [creating, setCreating] = useState(false);

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
    <div className="w-60 bg-[#0F0F14]/90 backdrop-blur-2xl border-r border-white/5 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-white/5 space-y-2">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 disabled:opacity-60 text-white rounded-2xl text-xs font-semibold transition-all duration-200 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 active:scale-[0.98] hover:translate-y-[-1px]"
        >
          <Plus size={14} /> {creating ? '创建中...' : '新建会话'}
        </button>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-2xl text-xs text-gray-200 focus:outline-none focus:border-[#007AFF]/50 focus:bg-white/10 transition-all duration-200 hover:border-white/20"
        >
          {agents.length === 0 && <option value="">暂无可用智能体</option>}
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-2xl text-xs text-gray-200 focus:outline-none focus:border-[#007AFF]/50 focus:bg-white/10 transition-all duration-200 hover:border-white/20"
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
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading && (
          <div className="text-center py-8">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <span className="text-[10px] text-gray-500">加载中...</span>
          </div>
        )}
        {sessions.map((s, idx) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-2xl cursor-pointer transition-all duration-200 border animate-in fade-in ${
              activeSessionId === s.id
                ? 'bg-white/[0.08] text-white shadow-md shadow-white/5 border-white/10'
                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border-transparent hover:border-white/5'
            }`}
            style={{ animationDelay: `${Math.min(idx, 8) * 50}ms` }}
            onClick={() => setActiveSession(s.id)}
          >
            <MessageSquare size={13} className="shrink-0 transition-transform duration-200 group-hover:scale-110" />
            <div className="flex-1 min-w-0">
              <span className="text-xs truncate block font-medium">{s.title || 'Untitled'}</span>
              <span className="text-[10px] text-gray-500 font-medium">{s.status || 'idle'}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all duration-200 hover:bg-red-500/10 rounded-xl hover:scale-110"
            >
              <Trash2 size={10} />
            </button>
          </div>
        ))}
        {!loading && sessions.length === 0 && (
          <div className="text-center py-8 animate-in fade-in">
            <span className="text-[10px] text-gray-500">暂无会话</span>
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="border-t border-white/5 p-3">
        <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-gray-500 font-medium">
          <Sparkles size={10} className="transition-transform duration-200 hover:rotate-12" />
          <span>{sessions.length} 个活跃会话</span>
        </div>
        <UserSwitcher />
      </div>
    </div>
  );
}
