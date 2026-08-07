import { useState } from 'react';
import {
  Activity, BarChart3, Bot, ChevronUp, Cpu, DollarSign, FileCode,
  FlaskConical, History, Key, MessageSquare, MoreHorizontal, Network,
  Package, Puzzle, Settings, Sparkles, Terminal, Workflow, X,
} from 'lucide-react';

const PRIMARY_ITEMS = [
  { id: 'dashboard', label: '概览', icon: Activity },
  { id: 'chat', label: '对话', icon: MessageSquare },
  { id: 'agents', label: '智能体', icon: Bot },
  { id: 'workflows', label: '工作流', icon: Workflow },
];

const MORE_ITEMS = [
  { id: 'tasks', label: '任务监控', icon: Cpu },
  { id: 'factory', label: '自主执行', icon: Sparkles },
  { id: 'cluster', label: '集群', icon: Network },
  { id: 'task-history', label: '任务历史', icon: History },
  { id: 'reasoning', label: '推理', icon: Activity },
  { id: 'reasoning-history', label: '推理历史', icon: History },
  { id: 'scheduler', label: '调度', icon: History },
  { id: 'skills', label: '技能', icon: Package },
  { id: 'plugins', label: '插件', icon: Puzzle },
  { id: 'plugin-manage', label: '插件管理', icon: Package },
  { id: 'apikeys', label: 'API 密钥', icon: Key },
  { id: 'mcp', label: 'MCP', icon: Terminal },
  { id: 'stats', label: '统计', icon: BarChart3 },
  { id: 'traces', label: '链路', icon: Activity },
  { id: 'eval', label: '评测', icon: FlaskConical },
  { id: 'cost', label: '成本', icon: DollarSign },
  { id: 'doctor', label: '诊断', icon: Activity },
  { id: 'settings', label: '设置', icon: Settings },
  { id: 'terminal', label: '终端', icon: FileCode },
];

export function AdaptiveMobileLayout({ children, currentPage, onNavigate }: {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  const currentItem = [...PRIMARY_ITEMS, ...MORE_ITEMS].find(item => item.id === currentPage);
  const moreActive = MORE_ITEMS.some(item => item.id === currentPage);

  const navigate = (page: string) => {
    onNavigate(page);
    setMoreOpen(false);
  };

  return (
    <div className="mobile-workspace-shell">
      <header className="mobile-context-bar safe-area-top">
        <div className="workspace-mark" aria-hidden="true"><Sparkles size={15} /></div>
        <div className="min-w-0 flex-1">
          <p className="workspace-eyebrow"><span>Climber</span> workspace</p>
          <h1 className="truncate text-sm font-semibold text-[var(--color-text-primary)]">{currentItem?.label ?? '工作区'}</h1>
        </div>
      </header>

      <main id="main-content" className="mobile-content">{children}</main>

      <nav className="mobile-bottom-nav safe-area-bottom" aria-label="移动端主导航">
        {PRIMARY_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = currentPage === id;
          return (
            <button key={id} onClick={() => navigate(id)} aria-current={active ? 'page' : undefined} className="mobile-nav-item">
              <Icon size={19} strokeWidth={active ? 2.4 : 1.8} />
              <span>{label}</span>
            </button>
          );
        })}
        <button onClick={() => setMoreOpen(true)} aria-expanded={moreOpen} aria-current={moreActive ? 'page' : undefined} className="mobile-nav-item" data-active={moreActive || undefined}>
          <MoreHorizontal size={19} />
          <span>更多</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="mobile-sheet-layer" role="presentation" onClick={() => setMoreOpen(false)}>
          <section className="mobile-nav-sheet" role="dialog" aria-modal="true" aria-label="全部工作区入口" onClick={event => event.stopPropagation()}>
            <div className="mobile-sheet-header">
              <div>
                <p className="workspace-eyebrow">Workspace</p>
                <h2 className="text-base font-semibold">全部入口</h2>
              </div>
              <button className="icon-button" onClick={() => setMoreOpen(false)} aria-label="关闭全部入口"><X size={18} /></button>
            </div>
            <div className="mobile-more-grid">
              {MORE_ITEMS.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => navigate(id)} aria-current={currentPage === id ? 'page' : undefined}>
                  <Icon size={18} />
                  <span>{label}</span>
                  <ChevronUp size={14} className="rotate-90 text-[var(--color-text-muted)]" />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
