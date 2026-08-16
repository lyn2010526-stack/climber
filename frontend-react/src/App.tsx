import { useState, useEffect, useCallback, Suspense } from 'react';
import {
  MessageSquare, Bot, Network, Cpu, BarChart3,
  Sparkles, Search, Bell, Menu,
  Settings, Workflow, Terminal, Key, Activity, FlaskConical, DollarSign,
  Puzzle, Package, Clock, History,
} from 'lucide-react';
import { WorkspaceLayout } from './components/workspace/WorkspaceLayout';
import { AgentsPage } from './pages/AgentsPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { ApiKeysPage } from './pages/ApiKeysPage';
import { StatsPage } from './pages/StatsPage';
import { SkillsPage } from './pages/SkillsPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { DoctorPage } from './pages/DoctorPage';
import { MCPPage } from './pages/MCPPage';
import { FactoryModePage } from './pages/FactoryModePage';
import { PluginsPage } from './pages/PluginsPage';
import { SchedulerPage } from './pages/SchedulerPage';
import { ClusterPage } from './pages/ClusterPage';
import TracesPage from './pages/TracesPage';
import EvalPage from './pages/EvalPage';
import CostPage from './pages/CostPage';
import PluginPage from './pages/PluginPage';
import { SettingsPage } from './pages/SettingsPage';
import TaskMonitorPage from './pages/TaskMonitorPage';
import { TaskHistoryPage } from './pages/TaskHistoryPage';
import { ReasoningPage } from './pages/ReasoningPage';
import { ReasoningHistoryPage } from './pages/ReasoningHistoryPage';
import { GlobalSearch } from './components/workspace/GlobalSearch';
import { PageTransition } from './components/workspace/PageTransition';
import { ThemeToggle } from './components/ui/ThemeToggle';
import TerminalPage from './pages/TerminalPage';
import CommandPalette from './components/workspace/CommandPalette';
import { MobileLayout } from './components/mobile/MobileLayout';
import { MobileChatPage } from './pages/MobileChatPage';
import { MobileFactoryPage } from './pages/mobile/MobileFactoryPage';
import { MobileClusterPage } from './pages/mobile/MobileClusterPage';
import { MobileTasksPage } from './pages/mobile/MobileTasksPage';
import { MobileAgentsPage } from './pages/mobile/MobileAgentsPage';
import { MobileNotificationsPage } from './pages/mobile/MobileNotificationsPage';
import { MobileWorkflowsPage } from './pages/mobile/MobileWorkflowsPage';
import { MobileSchedulerPage } from './pages/mobile/MobileSchedulerPage';
import { ErrorBoundary } from './components/ErrorBoundary';

type Page = 'chat' | 'agents' | 'workflows' | 'apikeys' | 'skills' | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins' | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost' | 'plugin-manage' | 'settings' | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal';

const CORE_NAV: { id: Page; icon: typeof MessageSquare; label: string; description: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', description: '对话与执行' },
  { id: 'factory', icon: Sparkles, label: '自主执行', description: '长任务与计划' },
  { id: 'tasks', icon: Cpu, label: '任务监控', description: '实时运行状态' },
];

const ALL_NAV_ITEMS: { id: Page; icon: typeof MessageSquare; label: string; keywords?: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', keywords: 'home workspace dashboard 工作台' },
  { id: 'factory', icon: Sparkles, label: '自主执行', keywords: 'auto agent execute 自主执行' },
  { id: 'cluster', icon: Network, label: '集群协作', keywords: 'multi agent team 集群协作' },
  { id: 'tasks', icon: Cpu, label: '任务监控', keywords: 'monitor task running 任务监控' },
  { id: 'task-history', icon: History, label: '任务历史', keywords: 'history past 任务历史' },
  { id: 'reasoning', icon: Activity, label: '推理引擎', keywords: 'reason think 推理引擎' },
  { id: 'reasoning-history', icon: History, label: '推理历史', keywords: 'reasoning history 推理历史' },
  { id: 'agents', icon: Bot, label: '智能体', keywords: 'agent config 智能体' },
  { id: 'workflows', icon: Workflow, label: '工作流', keywords: 'workflow dag 工作流' },
  { id: 'scheduler', icon: Clock, label: '定时任务', keywords: 'cron schedule 定时任务' },
  { id: 'plugins', icon: Puzzle, label: '插件市场', keywords: 'plugin marketplace 插件市场' },
  { id: 'plugin-manage', icon: Package, label: '插件管理', keywords: 'plugin manage installed 插件管理' },
  { id: 'skills', icon: Package, label: '技能中心', keywords: 'skill tool 技能中心' },
  { id: 'notifications', icon: Bell, label: '通知中心', keywords: 'notification alert 通知中心' },
  { id: 'doctor', icon: Activity, label: '系统诊断', keywords: 'health debug 系统诊断' },
  { id: 'mcp', icon: Terminal, label: 'MCP 市场', keywords: 'mcp protocol tool MCP' },
  { id: 'apikeys', icon: Key, label: 'API 密钥', keywords: 'api key secret API' },
  { id: 'stats', icon: BarChart3, label: '数据统计', keywords: 'stats analytics chart' },
  { id: 'traces', icon: Activity, label: '链路追踪', keywords: 'trace debug 链路追踪' },
  { id: 'eval', icon: FlaskConical, label: '效果评估', keywords: 'eval benchmark 评估' },
  { id: 'cost', icon: DollarSign, label: '成本控制', keywords: 'cost billing token 成本' },
  { id: 'settings', icon: Settings, label: '系统设置', keywords: 'settings config preference' },
  { id: 'terminal', icon: Terminal, label: '终端沙箱', keywords: 'terminal shell 终端' },
];

const VALID_PAGES = new Set(ALL_NAV_ITEMS.map(n => n.id));

function getPageFromHash(): Page {
  const hash = window.location.hash.replace('#', '') || 'chat';
  return VALID_PAGES.has(hash as Page) ? (hash as Page) : 'chat';
}

function PageFallback() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
        <div className="w-5 h-5 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }} />
        <span className="text-xs">加载中...</span>
      </div>
    </div>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>(getPageFromHash);
  const [activeOverlay, setActiveOverlay] = useState<'search' | 'commands' | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hoveredNav, setHoveredNav] = useState<Page | 'search' | 'commands' | null>(null);

  useEffect(() => {
    const onHashChange = () => {
      const page = getPageFromHash();
      setCurrentPage(page);
      setMobileMenuOpen(false);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setActiveOverlay(prev => prev === 'commands' ? null : 'commands');
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navigate = useCallback((page: Page) => {
    setCurrentPage(page as Page);
    window.location.hash = page;
    if (isMobile) setMobileMenuOpen(false);
  }, [isMobile]);

  const renderPage = () => {
    if (isMobile) {
      switch (currentPage) {
        case 'chat': return <MobileChatPage />;
        case 'factory': return <MobileFactoryPage />;
        case 'cluster': return <MobileClusterPage />;
        case 'tasks': return <MobileTasksPage />;
        case 'agents': return <MobileAgentsPage />;
        case 'notifications': return <MobileNotificationsPage />;
        case 'workflows': return <MobileWorkflowsPage />;
        case 'scheduler': return <MobileSchedulerPage />;
        case 'settings': return <SettingsPage />;
        default: return <MobileChatPage />;
      }
    }
    switch (currentPage) {
      case 'chat': return <WorkspaceLayout />;
      case 'agents': return <AgentsPage />;
      case 'workflows': return <WorkflowsPage />;
      case 'apikeys': return <ApiKeysPage />;
      case 'skills': return <SkillsPage />;
      case 'notifications': return <NotificationsPage />;
      case 'doctor': return <DoctorPage />;
      case 'mcp': return <MCPPage />;
      case 'stats': return <StatsPage />;
      case 'factory': return <FactoryModePage />;
      case 'plugins': return <PluginsPage />;
      case 'plugin-manage': return <PluginPage />;
      case 'scheduler': return <SchedulerPage />;
      case 'cluster': return <ClusterPage />;
      case 'traces': return <TracesPage />;
      case 'eval': return <EvalPage />;
      case 'cost': return <CostPage />;
      case 'settings': return <SettingsPage />;
      case 'terminal': return <TerminalPage />;
      case 'tasks': return <TaskMonitorPage />;
      case 'task-history': return <TaskHistoryPage />;
      case 'reasoning': return <ReasoningPage />;
      case 'reasoning-history': return <ReasoningHistoryPage />;
    }
  };

  // 获取当前导航项的完整信息
  const activeNavItem = ALL_NAV_ITEMS.find(n => n.id === currentPage);
  const hoverNavItem = hoveredNav ? ALL_NAV_ITEMS.find(n => n.id === hoveredNav) : null;

  return (
    <div className="app-shell flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      {isMobile ? (
        <MobileLayout currentPage={currentPage} onNavigate={(page) => navigate(page as any)}>
          <Suspense fallback={<PageFallback />}>
            <ErrorBoundary>
              <PageTransition transitionKey={currentPage}>
                {renderPage()}
              </PageTransition>
            </ErrorBoundary>
          </Suspense>
        </MobileLayout>
      ) : (
        <>
          {/* Mobile overlay */}
          {mobileMenuOpen && (
            <div className="mobile-overlay md:hidden" onClick={() => setMobileMenuOpen(false)} />
          )}

          {/* Desktop workspace navigation */}
          <aside className="relative z-50 hidden md:flex flex-col w-[224px] shrink-0"
            style={{
              backgroundColor: 'var(--color-bg-surface-1)',
              borderRight: '1px solid var(--color-border-subtle)',
            }}
          >
            <div className="h-14 flex items-center gap-3 px-4 shrink-0" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{
                backgroundColor: 'var(--color-accent)',
                boxShadow: '0 5px 12px var(--color-accent-glow)',
              }}>
                <Sparkles size={15} className="text-white" strokeWidth={2.5} />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>Climber</div>
                <div className="text-[10px] truncate" style={{ color: 'var(--color-text-muted)' }}>Agent workspace</div>
              </div>
            </div>

            <nav className="flex-1 py-4 px-3 overflow-y-auto">
              <div className="px-2 mb-2 text-[10px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--color-text-muted)' }}>Workspace</div>
              <div className="space-y-1">
              {CORE_NAV.map(({ id, icon: Icon, label, description }) => {
                const isActive = currentPage === id;
                return (
                  <button
                    key={id}
                    onClick={() => navigate(id)}
                    className="relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 text-left"
                    style={{
                      backgroundColor: isActive ? 'var(--color-accent-subtle)' : 'transparent',
                      color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                    }}
                  >
                    <Icon size={17} strokeWidth={isActive ? 2.5 : 2} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-xs font-semibold" style={{ color: isActive ? 'var(--color-accent)' : 'var(--color-text-primary)' }}>{label}</span>
                      <span className="block text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{description}</span>
                    </span>
                    {isActive && (
                      <div className="absolute left-0 w-[3px] h-7 rounded-r-full bg-[var(--color-accent)]" />
                    )}
                  </button>
                );
              })}
              </div>
              <div className="px-2 mt-7 mb-2 text-[10px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--color-text-muted)' }}>Explore</div>
              <div className="space-y-1">
                {ALL_NAV_ITEMS.filter(item => !CORE_NAV.some(core => core.id === item.id) && ['cluster', 'agents', 'workflows', 'scheduler', 'skills', 'notifications'].includes(item.id)).map(({ id, icon: Icon, label }) => (
                  <button key={id} onClick={() => navigate(id)} className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-colors" style={{ color: currentPage === id ? 'var(--color-accent)' : 'var(--color-text-secondary)', backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'transparent' }}>
                    <Icon size={15} />
                    <span className="text-xs font-medium">{label}</span>
                  </button>
                ))}
              </div>
              <div className="px-2 mt-7 mb-2 text-[10px] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--color-text-muted)' }}>System</div>
              <button onClick={() => navigate('settings')} className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-colors" style={{ color: currentPage === 'settings' ? 'var(--color-accent)' : 'var(--color-text-secondary)', backgroundColor: currentPage === 'settings' ? 'var(--color-accent-subtle)' : 'transparent' }}>
                <Settings size={15} />
                <span className="text-xs font-medium">系统设置</span>
              </button>
            </nav>

            {/* Bottom actions */}
            <div className="p-3 space-y-1" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
              {/* Search */}
              <button
                onClick={() => setActiveOverlay('search')}
                onMouseEnter={() => setHoveredNav('search')}
                onMouseLeave={() => setHoveredNav(null)}
                aria-label="搜索"
                 className="relative w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-all duration-150"
                style={{
                  color: hoveredNav === 'search' ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  backgroundColor: hoveredNav === 'search' ? 'var(--color-bg-surface-2)' : 'transparent',
                }}
              >
                 <Search size={16} />
                 <span className="text-xs font-medium">全局搜索</span>
                {hoveredNav === 'search' && (
                  <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded-lg text-xs whitespace-nowrap z-[200] pointer-events-none"
                    style={{ backgroundColor: 'var(--color-bg-surface-3)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)' }}
                  >
                    全局搜索
                  </div>
                )}
              </button>
              {/* Commands */}
              <button
                onClick={() => setActiveOverlay('commands')}
                onMouseEnter={() => setHoveredNav('commands')}
                onMouseLeave={() => setHoveredNav(null)}
                aria-label="命令面板"
                 className="relative w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-all duration-150"
                style={{
                  color: hoveredNav === 'commands' ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  backgroundColor: hoveredNav === 'commands' ? 'var(--color-bg-surface-2)' : 'transparent',
                }}
              >
                 <Menu size={16} />
                 <span className="text-xs font-medium">命令面板</span>
                {hoveredNav === 'commands' && (
                  <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded-lg text-xs whitespace-nowrap z-[200] pointer-events-none"
                    style={{ backgroundColor: 'var(--color-bg-surface-3)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)' }}
                  >
                    命令面板 <kbd className="ml-1 font-mono text-[10px]">⌘K</kbd>
                  </div>
                )}
              </button>
              {/* Theme toggle */}
              <div className="flex items-center justify-end pt-1">
                <ThemeToggle />
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 overflow-hidden flex flex-col relative" style={{ backgroundColor: 'var(--color-bg-page)' }}>
            {/* Mobile header */}
            <div className="md:hidden h-12 flex items-center px-3" style={{
              borderBottom: '1px solid var(--color-border-subtle)',
              backgroundColor: 'rgba(17,17,19,0.9)',
              backdropFilter: 'blur(24px)',
            }}>
              <button
                onClick={() => setMobileMenuOpen(true)}
                aria-label="打开导航菜单"
                aria-expanded={mobileMenuOpen}
                className="p-1.5 rounded-lg transition-all duration-200 active:scale-[0.95]"
                style={{ color: 'var(--color-text-muted)' }}
              >
                <Menu size={18} />
              </button>
              <div className="ml-2.5 flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, var(--color-accent), #8b5cf6)' }}
                >
                  <Sparkles size={12} className="text-white" />
                </div>
                <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Climber</span>
              </div>
            </div>

            {/* Page title bar (non-chat pages only) */}
            {!['chat'].includes(currentPage) && activeNavItem && (
              <div className="hidden md:flex items-center gap-3 px-6 h-12 border-b shrink-0"
                style={{ borderBottom: '1px solid var(--color-border-subtle)', backgroundColor: 'var(--color-bg-surface-1)' }}
              >
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg" style={{ backgroundColor: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
                    <activeNavItem.icon size={14} />
                  </div>
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>{activeNavItem.label}</span>
                </div>
                {hoverNavItem && hoverNavItem.id !== activeNavItem.id && (
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{hoverNavItem.label}</span>
                )}
              </div>
            )}

            <Suspense fallback={<PageFallback />}>
              <ErrorBoundary>
                <PageTransition transitionKey={currentPage}>
                  {renderPage()}
                </PageTransition>
              </ErrorBoundary>
            </Suspense>
          </main>

          <GlobalSearch isOpen={activeOverlay === 'search'} onClose={() => setActiveOverlay(null)} />
          <CommandPalette isOpen={activeOverlay === 'commands'} onClose={() => setActiveOverlay(null)} onNavigate={(page) => navigate(page as Page)} />
        </>
      )}
    </div>
  );
}
