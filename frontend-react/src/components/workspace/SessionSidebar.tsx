import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MessageSquare, Plus, Trash2, Sparkles, ChevronDown, Search, MoreHorizontal, Pin, Pencil, Download, X, Check, SlidersHorizontal } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
import { useSessions } from '../../hooks/useSessions';
import { api } from '../../api';
import { UserSwitcher } from './UserSwitcher';

export const SessionSidebar = React.memo(function SessionSidebar({ inDrawer = false }: { inDrawer?: boolean }) {
  const activeSessionId = useWorkspaceStore(s => s.activeSessionId);
  const setActiveSession = useWorkspaceStore(s => s.setActiveSession);
  const { sessions, loading, error, createSession, deleteSession, renameSession, refresh } = useSessions();

  const [selectedAgent, setSelectedAgent] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [creating, setCreating] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [agentsError, setAgentsError] = useState(false);
  const [modelsError, setModelsError] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [createOptionsOpen, setCreateOptionsOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('climber-pinned-sessions') || '[]'); } catch { return []; }
  });

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
      const payload = {
        title: `会话 ${sessions.length + 1}`,
        agent_id: selectedAgent,
        ...(selectedModel ? { model_settings: { model_id: selectedModel } } : {}),
      };
      await createSession(payload);
      await refresh();
    } finally {
      setCreating(false);
    }
  }, [selectedAgent, selectedModel, creating, sessions.length, createSession, refresh]);

  const filteredSessions = useMemo(() => {
    const matching = searchQuery
      ? sessions.filter(s => s.title?.toLowerCase().includes(searchQuery.toLowerCase()))
      : sessions;
    return [...matching].sort((a, b) => Number(pinnedIds.includes(b.id)) - Number(pinnedIds.includes(a.id)));
  }, [sessions, searchQuery, pinnedIds]);

  const togglePin = useCallback((id: string) => {
    setPinnedIds(prev => {
      const next = prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id];
      localStorage.setItem('climber-pinned-sessions', JSON.stringify(next));
      return next;
    });
    setMenuSessionId(null);
  }, []);

  const beginRename = useCallback((id: string, title: string | null) => {
    setEditingSessionId(id);
    setEditingTitle(title || '未命名会话');
    setMenuSessionId(null);
  }, []);

  const saveRename = useCallback(async () => {
    if (!editingSessionId || !editingTitle.trim()) return;
    await renameSession(editingSessionId, editingTitle.trim());
    setEditingSessionId(null);
  }, [editingSessionId, editingTitle, renameSession]);

  const exportSession = useCallback(async (id: string, title: string | null) => {
    const data = await api.getSessionMessages(id);
    const body = data.messages.map(message => `## ${message.role}\n\n${message.content || ''}`).join('\n\n---\n\n');
    const blob = new Blob([`# ${title || '未命名会话'}\n\n${body}`], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${(title || 'session').replace(/[\\/:*?"<>|]/g, '-')}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
    setMenuSessionId(null);
  }, []);

  return (
    <div className={inDrawer
      ? "w-full flex flex-col"
      : "w-60 flex flex-col shrink-0 bg-[var(--color-bg-surface-1)] border-r border-[var(--color-border-subtle)]"}>
      <div className="p-2 space-y-1.5 border-b border-[var(--color-border-subtle)]">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-[0.97] text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]"
        >
          <Plus size={14} strokeWidth={2.5} /> 新建会话
        </button>
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="搜索会话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-2.5 py-1.5 text-xs rounded-lg transition-all duration-200 focus:outline-none bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] focus:border-[var(--color-border-default)]"
          />
        </div>
        <button
          type="button"
          onClick={() => setCreateOptionsOpen(current => !current)}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[11px] transition-colors text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]"
          aria-expanded={createOptionsOpen}
        >
          <SlidersHorizontal size={12} />
          <span className="min-w-0 flex-1 truncate">
            {agents.find(agent => agent.id === selectedAgent)?.name || '选择智能体'}
            {selectedModel && ` · ${models.find(item => (item.id || item.model_id) === selectedModel)?.name || selectedModel}`}
          </span>
          <ChevronDown size={11} className={`shrink-0 transition-transform ${createOptionsOpen ? 'rotate-180' : ''}`} />
        </button>
        {createOptionsOpen && <div className="grid grid-cols-1 gap-1.5 rounded-lg p-2 bg-[var(--color-bg-surface-2)]">
          <div>
            {agentsError && (
              <div className="flex items-center justify-between px-2 py-1 text-[10px] text-[var(--color-error)]">
                <span>加载失败</span>
                <button onClick={fetchAgents} className="underline">重试</button>
              </div>
            )}
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              aria-label="新会话使用的智能体"
              className="w-full px-2 py-1.5 rounded-lg text-xs transition-all duration-200 focus:outline-none bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)]"
            >
              {agents.length === 0 && <option value="">智能体...</option>}
              {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            {modelsError && (
              <div className="flex items-center justify-between px-2 py-1 text-[10px] text-[var(--color-error)]">
                <span>加载失败</span>
                <button onClick={fetchModels} className="underline">重试</button>
              </div>
            )}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              aria-label="新会话使用的模型"
              className="w-full px-2 py-1.5 rounded-lg text-xs transition-all duration-200 focus:outline-none bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)]"
            >
              {models.length === 0 && <option value="">模型...</option>}
              {models.map(m => <option key={m.id || m.model_id} value={m.id || m.model_id}>{m.name || m.model_id || m.id}</option>)}
            </select>
          </div>
        </div>}
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {loading && (
          <div className="text-center py-6">
            <div className="w-4 h-4 border-2 rounded-full animate-spin mx-auto mb-1.5 border-[var(--color-accent)] border-t-transparent"
            />
            <span className="text-[10px] text-[var(--color-text-muted)]">加载中...</span>
          </div>
        )}
        {!loading && error && (
          <div role="alert" className="rounded-lg px-3 py-4 text-center bg-[var(--color-error-subtle)] text-[var(--color-error)]">
            <p className="text-xs font-medium">加载会话失败</p>
            <button
              type="button"
              onClick={refresh}
              aria-label="重试加载会话"
              className="mt-2 rounded-md px-2 py-1 text-[10px] font-semibold underline"
            >
              重试
            </button>
          </div>
        )}
        {!error && filteredSessions.map((s) => {
          const isActive = activeSessionId === s.id;
          return (
          <div
            key={s.id}
            role="option"
            tabIndex={0}
            aria-selected={isActive}
            className="group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-150 border text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] data-[active=true]:text-[var(--color-text-primary)] data-[active=true]:bg-[var(--color-bg-surface-2)] data-[active=true]:border-[var(--color-border-default)] border-transparent data-[active=true]:border-[var(--color-border-default)]"
            data-active={isActive}
            onClick={() => editingSessionId !== s.id && setActiveSession(s.id)}
            onKeyDown={(event) => {
              if ((event.key === 'Enter' || event.key === ' ') && editingSessionId !== s.id) {
                event.preventDefault();
                setActiveSession(s.id);
              }
            }}
          >
            <MessageSquare size={13} className={`shrink-0 ${isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'}`} />
            <div className="flex-1 min-w-0">
              {editingSessionId === s.id ? (
                <div className="flex items-center gap-1" onClick={event => event.stopPropagation()}>
                  <input autoFocus value={editingTitle} onChange={event => setEditingTitle(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') saveRename(); if (event.key === 'Escape') setEditingSessionId(null); }} className="w-full min-w-0 rounded-md px-1.5 py-1 text-xs outline-none bg-[var(--color-bg-surface-1)] border border-[var(--color-accent)] text-[var(--color-text-primary)]" aria-label="会话标题" />
                  <button onClick={saveRename} aria-label="保存标题" className="p-1"><Check size={11} /></button>
                  <button onClick={() => setEditingSessionId(null)} aria-label="取消重命名" className="p-1"><X size={11} /></button>
                </div>
              ) : (
                <span className="text-xs truncate flex items-center gap-1 font-medium">
                  {pinnedIds.includes(s.id) && <Pin size={9} className="shrink-0" />}
                  <span className="truncate">{s.title || '未命名会话'}</span>
                </span>
              )}
              <span className="text-[10px] text-[var(--color-text-muted)]">{s.status || 'idle'}</span>
            </div>
            {editingSessionId !== s.id && (
              <div className="relative">
                <button onClick={(event) => { event.stopPropagation(); setMenuSessionId(menuSessionId === s.id ? null : s.id); }} aria-label={`管理 ${s.title || '未命名会话'}`} className="opacity-100 md:opacity-0 group-hover:opacity-100 p-1 rounded-md transition-all text-[var(--color-text-muted)]"><MoreHorizontal size={13} /></button>
                {menuSessionId === s.id && (
                  <div className="absolute right-0 top-7 z-30 w-36 rounded-lg p-1 shadow-xl bg-[var(--color-bg-surface-1)] border border-[var(--color-border-default)]" onClick={event => event.stopPropagation()}>
                    <button onClick={() => togglePin(s.id)} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs hover:bg-[var(--color-bg-surface-2)]"><Pin size={12} />{pinnedIds.includes(s.id) ? '取消置顶' : '置顶会话'}</button>
                    <button onClick={() => beginRename(s.id, s.title)} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs hover:bg-[var(--color-bg-surface-2)]"><Pencil size={12} />重命名</button>
                    <button onClick={() => exportSession(s.id, s.title)} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs hover:bg-[var(--color-bg-surface-2)]"><Download size={12} />导出 Markdown</button>
                    <button onClick={() => { setPendingDeleteId(s.id); setMenuSessionId(null); }} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-[var(--color-error)]"><Trash2 size={12} />删除</button>
                  </div>
                )}
              </div>
            )}
          </div>
          );
        })}
        {!loading && !error && filteredSessions.length === 0 && (
          <div className="text-center py-6">
            <span className="text-[10px] text-[var(--color-text-muted)]">
              {searchQuery ? '无匹配会话' : '暂无会话'}
            </span>
          </div>
        )}
      </div>

      <div className="p-2 space-y-1 border-t border-[var(--color-border-subtle)]">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all duration-150 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]"
        >
          <MoreHorizontal size={12} />
          <span>更多选项</span>
          <ChevronDown size={10} className={`ml-auto transition-transform duration-200 ${showSettings ? 'rotate-180' : ''}`} />
        </button>
        {showSettings && (
          <div className="space-y-0.5">
            <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-[var(--color-text-muted)]">
              <Sparkles size={10} className="text-[var(--color-accent)]" />
              <span>{sessions.length} 个会话</span>
            </div>
            <UserSwitcher />
          </div>
        )}
      </div>

      {pendingDeleteId && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true" aria-label="确认删除会话" onClick={() => setPendingDeleteId(null)}>
          <div className="w-full max-w-sm rounded-xl p-5 shadow-2xl bg-[var(--color-bg-surface-1)] border border-[var(--color-border-default)]" onClick={event => event.stopPropagation()}>
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">删除这个会话？</h2>
            <p className="mt-2 text-xs leading-5 text-[var(--color-text-secondary)]">会话消息和执行记录将一并删除，这项操作无法撤销。</p>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setPendingDeleteId(null)} className="px-3 py-1.5 rounded-lg text-xs border border-[var(--color-border-default)]">取消</button>
              <button onClick={async () => { await deleteSession(pendingDeleteId); setPendingDeleteId(null); }} className="px-3 py-1.5 rounded-lg text-xs text-white bg-[var(--color-error)]">确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
