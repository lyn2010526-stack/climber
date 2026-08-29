import { useState } from 'react';
import { Drawer } from 'vaul';
import { MessageSquare, Sparkles, Network, Cpu, Bot, Settings, Bell, Workflow, CalendarClock, MoreHorizontal, History, Activity, Puzzle, Package, Key, BarChart3, FlaskConical, DollarSign, Terminal } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspace';
const MOBILE_TABS: { id: string; icon: typeof MessageSquare; label: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台' },
  { id: 'factory', icon: Sparkles, label: '执行' },
  { id: 'tasks', icon: Cpu, label: '任务' },
  { id: 'agents', icon: Bot, label: '智能体' },
];

const MORE_ITEMS: { id: string; icon: typeof Settings; label: string }[] = [
  { id: 'cluster', icon: Network, label: '集群协作' },
  { id: 'task-history', icon: History, label: '任务历史' },
  { id: 'reasoning', icon: Activity, label: '推理引擎' },
  { id: 'reasoning-history', icon: History, label: '推理历史' },
  { id: 'notifications', icon: Bell, label: '通知中心' },
  { id: 'workflows', icon: Workflow, label: '工作流' },
  { id: 'scheduler', icon: CalendarClock, label: '调度器' },
  { id: 'skills', icon: Package, label: '技能中心' },
  { id: 'plugins', icon: Puzzle, label: '插件市场' },
  { id: 'plugin-manage', icon: Package, label: '插件管理' },
  { id: 'mcp', icon: Terminal, label: 'MCP 市场' },
  { id: 'apikeys', icon: Key, label: 'API 密钥' },
  { id: 'stats', icon: BarChart3, label: '数据统计' },
  { id: 'traces', icon: Activity, label: '链路追踪' },
  { id: 'eval', icon: FlaskConical, label: '效果评估' },
  { id: 'cost', icon: DollarSign, label: '成本控制' },
  { id: 'doctor', icon: Activity, label: '系统诊断' },
  { id: 'terminal', icon: Terminal, label: '终端沙箱' },
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
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
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
                className="relative flex h-full flex-1 flex-col items-center justify-center gap-0.5 rounded-lg transition-colors duration-150"
                style={{
                  color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  backgroundColor: 'transparent',
                }}
              >
                {isActive && (
                  <div
                    className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] rounded-full"
                    style={{
                      backgroundColor: 'var(--color-accent)',
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
            className="relative flex h-full flex-1 flex-col items-center justify-center gap-0.5 rounded-lg transition-colors duration-150"
            style={{
              color: MORE_ITEMS.some(item => item.id === currentPage) ? 'var(--color-accent)' : 'var(--color-text-muted)',
              backgroundColor: 'transparent',
            }}
          >
            {MORE_ITEMS.some(item => item.id === currentPage) && (
              <div
                className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] rounded-full"
                style={{
                  backgroundColor: 'var(--color-accent)',
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
            <Drawer.Overlay className="fixed inset-0 z-[60] bg-black/45 backdrop-blur-[2px]" />
            <Drawer.Content
              className="fixed inset-x-0 bottom-0 z-[60] mx-auto w-full max-w-lg rounded-t-2xl outline-none"
              style={{
                backgroundColor: 'var(--color-bg-surface-1)',
                borderTop: '1px solid var(--color-border-subtle)',
                paddingBottom: 'env(safe-area-inset-bottom, 0px)',
              }}
            >
              <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-[var(--color-bg-surface-3)]" />
              <div className="p-4 space-y-2">
                {MORE_ITEMS.map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => {
                      onNavigate(id);
                      setMoreOpen(false);
                    }}
                    className="flex w-full items-center gap-3 rounded-lg px-4 py-3 transition-colors duration-150"
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
