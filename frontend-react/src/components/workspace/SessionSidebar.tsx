import { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare, Plus, Trash2, Sparkles, History,
} from 'lucide-react';
import {
  useWorkspaceStore,
  type Session,
  type ApiSession,
} from '../../store/workspace';
import { api } from '../../api';
import { apiClient } from '../../lib/api-client';
import { ModelConfig } from '../chat/ModelConfig';
import type { ModelSelection } from '../chat/ModelSelector';
import { UserSwitcher } from './UserSwitcher';
import { PermissionModes } from '../agent/PermissionModes';
import type { PermissionMode } from '../agent/PermissionModes';

export function SessionSidebar() {
  const {
    sessions, activeSessionId, setActiveSession,
    loadSessions, createSessionLocal, deleteSession, updateSession,
    loadingSessions, sessionsLoaded, setSessionsLoading,
  } = useWorkspaceStore();

  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [ownerKey, setOwnerKey] = useState<string | null>(null);
  const [identityError, setIdentityError] = useState(false);
  const [useAgentModel, setUseAgentModel] = useState(true);
  const [selection, setSelection] = useState<{ owner: string; model: ModelSelection | null } | null>(null);
  const selectedModel = selection?.owner === ownerKey ? selection.model : null;
  const [creating, setCreating] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [permissionMode, setPermissionMode] = useState<PermissionMode>('manual');
  const [showCheckpoints, setShowCheckpoints] = useState(false);

  const refreshSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = (await api.listSessions()) as ApiSession[];
      loadSessions(Array.isArray(data) ? data : []);
    } catch {
      setSessionsLoading(false);
    }
  }, [loadSessions, setSessionsLoading]);

  useEffect(() => {
    let active = true;
    let controller: AbortController | undefined;
    const refreshOwner = () => {
      controller?.abort();
      controller = new AbortController();
      const signal = controller.signal;
      apiClient.get<{ id: string }>('/auth/me', { signal }).then((user) => {
        if (!active || signal.aborted) return;
        if (!user.id) throw new Error('Missing user identity');
        setOwnerKey(user.id);
        setIdentityError(false);
      }).catch(() => {
        if (!active || signal.aborted) return;
        setOwnerKey(null);
        setSelection(null);
        setIdentityError(true);
      });
    };
    refreshOwner();
    window.addEventListener('storage', refreshOwner);
    window.addEventListener('focus', refreshOwner);
    return () => {
      active = false;
      controller?.abort();
      window.removeEventListener('storage', refreshOwner);
      window.removeEventListener('focus', refreshOwner);
    };
  }, []);

  useEffect(() => {
    let active = true;
    setAgents([]);
    setSelectedAgent('');
    setSelection(null);
    setUseAgentModel(true);
    if (!ownerKey) return;
    api.listAgents().then((data) => {
      if (!active) return;
      setAgents(data);
      if (data.length > 0) setSelectedAgent(data[0].id);
    }).catch(() => {});
    return () => { active = false; };
  }, [ownerKey]);

  useEffect(() => {
    if (!sessionsLoaded) {
      refreshSessions();
    }
  }, [sessionsLoaded, refreshSessions]);

  const handleCreate = useCallback(async () => {
    if (!selectedAgent || !ownerKey || creating || (!useAgentModel && !selectedModel)) return;
    setCreating(true);
    setCreateError(null);
    try {
      const user = await apiClient.get<{ id: string }>('/auth/me');
      if (user.id !== ownerKey) {
        setOwnerKey(user.id || null);
        setSelection(null);
        throw new Error('当前用户已变更，请重新选择智能体和模型');
      }
      const chosen = useAgentModel ? null : selectedModel;
      const title = `会话 ${sessions.length + 1}`;
      const created = await api.createSession({
        title,
        agent_id: selectedAgent,
        model_settings: chosen,
      });
      const newId: string = created?.id || created?.session_id || '';
      const modelConfig: Session['modelConfig'] = {
        provider: created?.provider || chosen?.provider || agents.find((a) => a.id === selectedAgent)?.provider || 'unknown',
        modelId: created?.model_id || chosen?.model_id || agents.find((a) => a.id === selectedAgent)?.model_id || '',
        temperature: 0.7,
        maxTokens: 4096,
      };
      await refreshSessions();
      if (newId) {
        const exists = useWorkspaceStore.getState().sessions.some((s) => s.id === newId);
        if (!exists) {
          createSessionLocal({
            id: newId,
            title: created?.title ?? title,
            status: 'idle',
            messages: [],
            activeSkills: [],
            activeTools: [],
            modelConfig,
            tokenUsage: { used: 0, limit: 200000 },
            createdAt: Date.now(),
          });
        } else {
          updateSession(newId, { modelConfig });
        }
        setActiveSession(newId);
      }
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : '创建会话失败，请重试');
    } finally {
      setCreating(false);
    }
  }, [
    selectedAgent, selectedModel, useAgentModel, ownerKey, creating, sessions.length, agents,
    refreshSessions, createSessionLocal, updateSession, setActiveSession,
  ]);

  const handleDelete = useCallback(async (id: string) => {
    setDeleteError(null);
    try {
      await api.deleteSession(id);
    } catch {
      setDeleteError('删除会话失败，请重试');
      return;
    }
    deleteSession(id);
    await refreshSessions();
  }, [deleteSession, refreshSessions]);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <aside className="session-sidebar" aria-label="会话">
      <div className="border-b border-[var(--color-border-subtle)] p-3">
        <PermissionModes
          currentMode={permissionMode}
          onModeChange={setPermissionMode}
        />
      </div>

      <div className="space-y-2 border-b border-[var(--color-border-subtle)] p-3">
        <button
          onClick={handleCreate}
          disabled={creating || !ownerKey || !selectedAgent || (!useAgentModel && !selectedModel)}
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
          value={useAgentModel ? 'agent' : 'credential'}
          onChange={(e) => { setUseAgentModel(e.target.value === 'agent'); setSelection(null); }}
          aria-label="模型来源"
          disabled={creating || !ownerKey}
          className="h-11 w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-accent)] focus:outline-none"
        >
          <option value="agent">使用智能体默认模型</option>
          <option value="credential">使用已存凭据选择模型</option>
        </select>
        {!useAgentModel && ownerKey && (
          <ModelConfig ownerKey={ownerKey} value={selectedModel} disabled={creating}
            onChange={(model) => setSelection({ owner: ownerKey, model })} />
        )}
        {identityError && <p role="alert">无法确认当前用户，请刷新页面重试</p>}
      </div>

      {deleteError && (
        <p role="alert" className="px-3 py-2 text-xs text-[var(--color-error)]">
          {deleteError}
        </p>
      )}
      {createError && (
        <p role="alert" className="px-3 py-2 text-xs text-[var(--color-error)]">
          {createError}
        </p>
      )}

      <div className="flex-1 space-y-0.5 overflow-y-auto p-2" aria-live="polite" aria-busy={loadingSessions}>
        {loadingSessions && (
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
              onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}
               aria-label={`删除会话 ${s.title || 'Untitled'}`}
                className="flex h-11 w-11 items-center justify-center rounded-md text-[var(--color-text-muted)] opacity-0 transition-colors hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)] group-hover:opacity-100 group-focus-within:opacity-100"
            >
              <Trash2 size={10} />
            </button>
           </div>
        ))}
        {!loadingSessions && sessions.length === 0 && (
          <div className="text-center py-8">
            <span className="text-[10px] text-[var(--color-text-muted)]">暂无会话</span>
          </div>
        )}
      </div>

      {showCheckpoints && (
        <div className="max-h-48 space-y-2 overflow-y-auto border-t border-[var(--color-border-subtle)] p-3">
          <div className="flex items-center gap-2 px-1">
            <History size={12} className="text-[var(--color-accent)]" />
            <span className="text-[11px] font-medium text-[var(--color-text-secondary)]">检查点历史</span>
          </div>
          {(activeSession?.messages ?? []).slice(-10).reverse().map((msg, i) => (
            <div key={i} className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2 py-1.5 text-[10px] text-[var(--color-text-secondary)]">
              <span className="text-[var(--color-text-muted)]">{new Date(msg.timestamp).toLocaleTimeString()}</span>
              <span className="ml-2">{msg.type}</span>
            </div>
          ))}
          {(!activeSession?.messages?.length) && (
            <p className="text-[10px] text-[var(--color-text-muted)] text-center py-2">暂无检查点</p>
          )}
        </div>
      )}

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
