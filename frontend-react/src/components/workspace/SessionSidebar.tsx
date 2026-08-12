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
  const activeSessionId = useWorkspaceStore(s => s.activeSessionId);
  const setActiveSession = useWorkspaceStore(s => s.setActiveSession);
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
      if (data.length > 0) setSelectedAgent(data[0]?.id ?? '');
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
    <div className="w-60 flex flex-col" style={{
      backgroundColor: 'rgba(17, 17, 19, 0.90)',
      borderRight: '1px solid var(--color-border-subtle)',
    }}>
      {/* Permission Mode Selector */}
      <div className="p-2.5" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
        <PermissionModes
          currentMode={permissionMode}
          onModeChange={setPermissionMode}
        />
      </div>

      {/* Header — New Chat Button */}
      <div className="p-2.5 space-y-2" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-[0.97]"
          style={{
            color: '#ffffff',
            backgroundColor: 'var(--color-accent)',
            boxShadow: '0 0 16px var(--color-accent-glow)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-accent)'; }}
        >
          <Plus size={14} strokeWidth={2.5} /> {creating ? '创建中...' : '新建会话'}
        </button>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="w-full px-2.5 py-1.5 rounded-lg text-xs transition-all duration-200"
          style={{
            color: 'var(--color-text-primary)',
            backgroundColor: 'var(--color-bg-surface-2)',
            border: '1px solid var(--color-border-subtle)',
          }}
        >
          {agents.length === 0 && <option value="">暂无可用智能体</option>}
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full px-2.5 py-1.5 rounded-lg text-xs transition-all duration-200"
          style={{
            color: 'var(--color-text-primary)',
            backgroundColor: 'var(--color-bg-surface-2)',
            border: '1px solid var(--color-border-subtle)',
          }}
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
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {loading && (
          <div className="text-center py-8">
            <div className="w-4 h-4 border-2 rounded-full animate-spin mx-auto mb-2"
              style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }}
            />
            <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>加载中...</span>
          </div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className="group flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-200 border"
            style={{
              borderColor: activeSessionId === s.id ? 'var(--color-border-default)' : 'transparent',
              backgroundColor: activeSessionId === s.id ? 'var(--color-bg-surface-2)' : 'transparent',
              color: activeSessionId === s.id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            }}
            onMouseEnter={(e) => {
              if (activeSessionId !== s.id) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                e.currentTarget.style.color = 'var(--color-text-primary)';
              }
            }}
            onMouseLeave={(e) => {
              if (activeSessionId !== s.id) {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }
            }}
            onClick={() => setActiveSession(s.id)}
          >
            <MessageSquare size={13} className="shrink-0" style={{
              color: activeSessionId === s.id ? 'var(--color-accent)' : 'var(--color-text-muted)',
            }} />
            <div className="flex-1 min-w-0">
              <span className="text-xs truncate block font-medium">{s.title || 'Untitled'}</span>
              <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-muted)' }}>{s.status || 'idle'}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded-lg transition-all duration-200 hover:scale-110"
              style={{ color: 'var(--color-text-muted)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-error)'; e.currentTarget.style.backgroundColor = 'var(--color-error-subtle)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <Trash2 size={10} />
            </button>
          </div>
        ))}
        {!loading && sessions.length === 0 && (
          <div className="text-center py-8">
            <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>暂无会话</span>
          </div>
        )}
      </div>

      {/* Checkpoint History Panel */}
      {showCheckpoints && (
        <div className="max-h-48 overflow-y-auto p-2.5 space-y-2"
          style={{ borderTop: '1px solid var(--color-border-subtle)' }}
        >
          <div className="flex items-center gap-2 px-1">
            <History size={12} style={{ color: 'var(--color-accent)' }} />
            <span className="text-[11px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>检查点历史</span>
          </div>
          {(sessions.find(s => s.id === activeSessionId) as any)?.messages?.slice(-10).reverse().map((msg: any, i: number) => (
            <div key={i} className="px-2 py-1.5 rounded-lg text-[10px]" style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-secondary)',
            }}>
              <span style={{ color: 'var(--color-text-muted)' }}>{new Date(msg.timestamp).toLocaleTimeString()}</span>
              <span className="ml-2">{msg.type}</span>
            </div>
          ))}
          {(!(sessions.find(s => s.id === activeSessionId) as any)?.messages?.length) && (
            <p className="text-[10px] text-center py-2" style={{ color: 'var(--color-text-muted)' }}>暂无检查点</p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="p-2.5 space-y-2" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCheckpoints(!showCheckpoints)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-medium transition-all duration-200"
            style={{
              color: showCheckpoints ? 'var(--color-accent)' : 'var(--color-text-muted)',
              backgroundColor: showCheckpoints ? 'var(--color-accent-subtle)' : 'transparent',
            }}
            onMouseEnter={(e) => {
              if (!showCheckpoints) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }
            }}
            onMouseLeave={(e) => {
              if (!showCheckpoints) {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-muted)';
              }
            }}
          >
            <History size={10} />
            检查点历史
          </button>
        </div>
        <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium" style={{ color: 'var(--color-text-muted)' }}>
          <Sparkles size={10} style={{ color: 'var(--color-accent)' }} />
          <span>{sessions.length} 个活跃会话</span>
        </div>
        <UserSwitcher />
      </div>
    </div>
  );
}