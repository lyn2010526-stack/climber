import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MessageSquare, Plus, Trash2, Sparkles, ChevronDown, Search, MoreVertical } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useSessions } from '../../stores/useSessions';
import { api } from '../../api';
import { UserSwitcher } from './UserSwitcher';

export const SessionSidebar = React.memo(function SessionSidebar({ inDrawer = false }: { inDrawer?: boolean }) {
  const activeSessionId = useWorkspaceStore(s => s.activeSessionId);
  const setActiveSession = useWorkspaceStore(s => s.setActiveSession);
  const { sessions, loading, createSession, deleteSession, refresh } = useSessions();

  const [selectedAgent, setSelectedAgent] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [creating, setCreating] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [agentsError, setAgentsError] = useState(false);
  const [modelsError, setModelsError] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  const fetchAgents = useCallback(() => {
    setAgentsError(false);
    api.listAgents().then((data) => {
      setAgents(data);
      setAgentsError(false);
      if (data.length > 0) setSelectedAgent(data[0]?.id ?? '');
    }).catch(() => setAgentsError(true));
  }, []);

  const fetchModels = useCallback(() => {
    setModelsError(false);
    api.listModels().then((data) => {
      setModels(data);
      setModelsError(false);
      if (data.length > 0) setSelectedModel(data[0]?.id || data[0]?.model_id || '');
    }).catch(() => setModelsError(true));
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

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

  const filteredSessions = useMemo(() => {
    if (!searchQuery) return sessions;
    const query = searchQuery.toLowerCase();
    return sessions.filter(s => s.title?.toLowerCase().includes(query));
  }, [sessions, searchQuery]);

  const handleMouseEnter = useCallback((e: React.MouseEvent<HTMLDivElement>, sessionId: string) => {
    if (activeSessionId !== sessionId) {
      e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
      e.currentTarget.style.color = 'var(--color-text-primary)';
    }
  }, [activeSessionId]);

  const handleMouseLeave = useCallback((e: React.MouseEvent<HTMLDivElement>, sessionId: string) => {
    if (activeSessionId !== sessionId) {
      e.currentTarget.style.backgroundColor = 'transparent';
      e.currentTarget.style.color = 'var(--color-text-secondary)';
    }
  }, [activeSessionId]);

  return (
    <div className={inDrawer ? "w-full flex flex-col" : "w-60 flex flex-col shrink-0"} style={inDrawer ? {} : {
      backgroundColor: 'var(--color-bg-surface-1)',
      borderRight: '1px solid var(--color-border-subtle)',
    }}>
      <div className="p-2 space-y-1.5" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-[0.97]"
          style={{ color: '#ffffff', backgroundColor: 'var(--color-accent)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-accent)'; }}
        >
          <Plus size={14} strokeWidth={2.5} /> 新建会话
        </button>
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-muted)' }} />
          <input
            type="text"
            placeholder="搜索会话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-2.5 py-1.5 text-xs rounded-lg transition-all duration-200 focus:outline-none"
            style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-primary)',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-default)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-subtle)'; }}
          />
        </div>
        <div className="flex gap-1.5">
          <div className="flex-1">
            {agentsError && (
              <div className="flex items-center justify-between px-2 py-1 text-[10px]" style={{ color: 'var(--color-error)' }}>
                <span>加载失败</span>
                <button onClick={fetchAgents} className="underline">重试</button>
              </div>
            )}
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg text-xs transition-all duration-200 focus:outline-none"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-subtle)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {agents.length === 0 && <option value="">智能体...</option>}
              {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="flex-1">
            {modelsError && (
              <div className="flex items-center justify-between px-2 py-1 text-[10px]" style={{ color: 'var(--color-error)' }}>
                <span>加载失败</span>
                <button onClick={fetchModels} className="underline">重试</button>
              </div>
            )}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg text-xs transition-all duration-200 focus:outline-none"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-subtle)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {models.length === 0 && <option value="">模型...</option>}
              {models.map(m => <option key={m.id || m.model_id} value={m.id || m.model_id}>{m.name || m.model_id || m.id}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {loading && (
          <div className="text-center py-6">
            <div className="w-4 h-4 border-2 rounded-full animate-spin mx-auto mb-1.5"
              style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }}
            />
            <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>加载中...</span>
          </div>
        )}
        {filteredSessions.map((s) => (
          <div
            key={s.id}
            className="group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-150 border"
            style={{
              borderColor: activeSessionId === s.id ? 'var(--color-border-default)' : 'transparent',
              backgroundColor: activeSessionId === s.id ? 'var(--color-bg-surface-2)' : 'transparent',
              color: activeSessionId === s.id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            }}
            onMouseEnter={(e) => handleMouseEnter(e, s.id)}
            onMouseLeave={(e) => handleMouseLeave(e, s.id)}
            onClick={() => setActiveSession(s.id)}
          >
            <MessageSquare size={13} className="shrink-0" style={{
              color: activeSessionId === s.id ? 'var(--color-accent)' : 'var(--color-text-muted)',
            }} />
            <div className="flex-1 min-w-0">
              <span className="text-xs truncate block font-medium">{s.title || '未命名会话'}</span>
              <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>{s.status || 'idle'}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
              className="opacity-100 md:opacity-0 group-hover:opacity-100 p-1 rounded-md transition-all duration-150 shrink-0"
              style={{ color: 'var(--color-text-muted)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-error)'; e.currentTarget.style.backgroundColor = 'var(--color-error-subtle)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <Trash2 size={10} />
            </button>
          </div>
        ))}
        {!loading && filteredSessions.length === 0 && (
          <div className="text-center py-6">
            <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>
              {searchQuery ? '无匹配会话' : '暂无会话'}
            </span>
          </div>
        )}
      </div>

      <div className="p-2 space-y-1" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all duration-150"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--color-text-muted)'; }}
        >
          <MoreVertical size={12} />
          <span>更多选项</span>
          <ChevronDown size={10} className={`ml-auto transition-transform duration-200 ${showSettings ? 'rotate-180' : ''}`} />
        </button>
        {showSettings && (
          <div className="space-y-0.5">
            <div className="flex items-center gap-2 px-2 py-1.5 text-[10px]" style={{ color: 'var(--color-text-muted)' }}>
              <Sparkles size={10} style={{ color: 'var(--color-accent)' }} />
              <span>{sessions.length} 个会话</span>
            </div>
            <UserSwitcher />
          </div>
        )}
      </div>
    </div>
  );
});
