import { useState } from 'react';
import { Drawer } from 'vaul';
import { MessageSquare, Sparkles, Network, Cpu, Bot, Settings, Bell, Workflow, CalendarClock, MoreHorizontal } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
const MOBILE_TABS: { id: string; icon: typeof MessageSquare; label: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台' },
  { id: 'factory', icon: Sparkles, label: '执行' },
  { id: 'cluster', icon: Network, label: '集群' },
  { id: 'tasks', icon: Cpu, label: '任务' },
  { id: 'agents', icon: Bot, label: '智能体' },
];

const MORE_ITEMS: { id: string; icon: typeof Settings; label: string }[] = [
  { id: 'notifications', icon: Bell, label: '通知中心' },
  { id: 'workflows', icon: Workflow, label: '工作流' },
  { id: 'scheduler', icon: CalendarClock, label: '调度器' },
  { id: 'settings', icon: Settings, label: '系统设置' },
];

export function MobileBottomNav({ currentPage, onNavigate }: { currentPage: string; onNavigate: (page: string) => void }) {
  const [moreOpen, setMoreOpen] = useState(false);
  const sessions = useWorkspaceStore(s => s.sessions);

  return (
    <>
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 safe-area-bottom"
        style={{
          backgroundColor: 'var(--color-glass-bg)',
          borderTop: '1px solid var(--color-glass-border)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        <div className="flex items-center justify-around h-14 px-2">
          {MOBILE_TABS.map(({ id, icon: Icon, label }) => {
            const isActive = currentPage === id;
            return (
              <button
                key={id}
                onClick={() => onNavigate(id)}
                className="relative flex flex-col items-center justify-center gap-0.5 flex-1 h-full rounded-xl transition-all duration-200 active:scale-[0.92]"
                style={{
                  color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  backgroundColor: isActive ? 'var(--color-accent-subtle)' : 'transparent',
                }}
              >
                {isActive && (
                  <div
                    className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] rounded-full"
                    style={{
                      backgroundColor: 'var(--color-accent)',
                      boxShadow: '0 0 8px var(--color-accent-glow)',
                    }}
                  />
                )}
                <div className="relative">
                  <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                  {id === 'chat' && sessions.length > 0 && (
                    <span
                      className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
                      style={{ backgroundColor: 'var(--color-success)' }}
                    />
                  )}
                </div>
                <span
                  className="text-[11px] font-medium truncate"
                  style={{ color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)' }}
                >
                  {label}
                </span>
              </button>
            );
          })}

          <button
            onClick={() => setMoreOpen(true)}
            className="relative flex flex-col items-center justify-center gap-0.5 flex-1 h-full rounded-xl transition-all duration-200 active:scale-[0.92]"
            style={{
              color: MORE_ITEMS.some(item => item.id === currentPage) ? 'var(--color-accent)' : 'var(--color-text-muted)',
              backgroundColor: MORE_ITEMS.some(item => item.id === currentPage) ? 'var(--color-accent-subtle)' : 'transparent',
            }}
          >
            {MORE_ITEMS.some(item => item.id === currentPage) && (
              <div
                className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] rounded-full"
                style={{
                  backgroundColor: 'var(--color-accent)',
                  boxShadow: '0 0 8px var(--color-accent-glow)',
                }}
              />
            )}
            <MoreHorizontal size={20} strokeWidth={MORE_ITEMS.some(item => item.id === currentPage) ? 2.5 : 2} />
            <span className="text-[11px] font-medium" style={{ color: 'var(--color-text-muted)' }}>
              更多
            </span>
          </button>
        </div>
      </nav>

      {moreOpen && (
        <Drawer.Root open={moreOpen} onOpenChange={setMoreOpen}>
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
              <div className="p-4 space-y-2">
                {MORE_ITEMS.map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => {
                      onNavigate(id);
                      setMoreOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 active:scale-[0.98]"
                    style={{
                      color: currentPage === id ? 'var(--color-accent)' : 'var(--color-text-primary)',
                      backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'var(--color-bg-surface-2)',
                    }}
                  >
                    <Icon size={20} />
                    <span className="font-medium">{label}</span>
                  </button>
                ))}
              </div>
            </Drawer.Content>
          </Drawer.Portal>
        </Drawer.Root>
      )}
    </>
  );
}
