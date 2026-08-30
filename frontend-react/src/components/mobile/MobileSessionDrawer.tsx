import { useCallback, useEffect, useState } from 'react';
import { Drawer } from 'vaul';
import { toast } from 'sonner';
import { MessageSquare, Plus } from 'lucide-react';
import { api } from '../../api';
import { useWorkspaceStore } from '../../store/workspace';
import { useSessions } from '../../hooks/useSessions';

interface MobileSessionDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MobileSessionDrawer({ open, onOpenChange }: MobileSessionDrawerProps) {
  const { activeSessionId, setActiveSession } = useWorkspaceStore();
  const { sessions, loading, error, createSession } = useSessions();
  const [creating, setCreating] = useState(false);
  const [agentId, setAgentId] = useState<string | undefined>(undefined);

  useEffect(() => {
    api.listAgents()
      .then((data: any[]) => {
        if (data.length > 0) setAgentId(data[0].id);
      })
      .catch(() => {});
  }, []);

  const handleCreate = useCallback(async () => {
    if (creating) return;
    setCreating(true);
    try {
      const session = await createSession(
        agentId ? { title: `会话 ${sessions.length + 1}`, agent_id: agentId } : { title: `会话 ${sessions.length + 1}` }
      );
      setActiveSession(session.id);
      onOpenChange(false);
    } catch {
      toast.error('创建会话失败，请重试');
    } finally {
      setCreating(false);
    }
  }, [creating, sessions.length, agentId, createSession, setActiveSession, onOpenChange]);

  const handleSelect = useCallback((id: string) => {
    setActiveSession(id);
    onOpenChange(false);
  }, [setActiveSession, onOpenChange]);

  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange}>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-md" />
        <Drawer.Content
          className="fixed inset-x-0 bottom-0 z-[60] mx-auto w-full max-w-lg rounded-t-3xl outline-none"
          style={{
            backgroundColor: 'var(--color-bg-surface-1)',
            borderTop: '1px solid var(--color-border-subtle)',
            paddingBottom: 'env(safe-area-inset-bottom, 0px)',
          }}
        >
          <div className="mx-auto mt-3 h-1.5 w-12 shrink-0 rounded-full bg-white/[0.15]" />
          <Drawer.Title className="sr-only">会话列表</Drawer.Title>
          <Drawer.Description className="sr-only">选择或新建一个会话</Drawer.Description>

          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-[var(--color-accent)]" />
                <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  会话
                </h2>
              </div>
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                {sessions.length} 个会话
              </span>
            </div>

            <button
              onClick={handleCreate}
              disabled={creating}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] disabled:opacity-50 text-white rounded-2xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-blue-500/20 active:scale-[0.98]"
            >
              <Plus size={16} strokeWidth={2.5} />
              {creating ? '创建中...' : '新建会话'}
            </button>

            <div className="mt-3 max-h-[50vh] overflow-y-auto space-y-0.5">
              {loading && (
                <div className="text-center py-8">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <span className="text-xs text-[var(--color-text-muted)]">加载中...</span>
                </div>
              )}

              {!loading && error && (
                <div className="text-center py-6 px-4 text-xs text-red-400">加载会话失败</div>
              )}

              {!loading && !error && sessions.length === 0 && (
                <div className="text-center py-8">
                  <span className="text-xs text-[var(--color-text-muted)]">暂无会话，点击上方新建</span>
                </div>
              )}

              {sessions.map((s) => {
                const isActive = activeSessionId === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => handleSelect(s.id)}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-2xl transition-all duration-200 active:scale-[0.98] text-left ${
                      isActive
                        ? 'bg-[var(--color-bg-surface-3)] border border-[var(--color-border-default)]'
                        : 'bg-[var(--color-bg-surface-2)] border border-transparent hover:bg-[var(--color-bg-surface-2)]'
                    }`}
                  >
                    <MessageSquare
                      size={15}
                      className="shrink-0"
                      style={{ color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)' }}
                    />
                    <div className="flex-1 min-w-0">
                      <span
                        className="block truncate text-sm font-medium"
                        style={{ color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)' }}
                      >
                        {s.title || 'Untitled'}
                      </span>
                      <span className="block text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                        {s.status || 'idle'}
                        {s.created_at ? ` · ${new Date(s.created_at).toLocaleString()}` : ''}
                      </span>
                    </div>
                    {isActive && (
                      <span
                        className="w-1.5 h-1.5 rounded-full shrink-0"
                        style={{ backgroundColor: 'var(--color-accent)', boxShadow: '0 0 6px var(--color-accent-glow)' }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
