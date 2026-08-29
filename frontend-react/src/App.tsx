import { useState, useEffect, useCallback, Suspense, lazy } from 'react';
import {
  MessageSquare, Bot, Network, Cpu, BarChart3,
  Mountain, Search, Bell, Menu,
  Settings, Workflow, Terminal, Key, Activity, FlaskConical, DollarSign,
  Puzzle, Package, Clock, History,
} from 'lucide-react';
const WorkspaceLayout = lazy(() => import('./components/workspace/WorkspaceLayout').then(m => ({ default: m.WorkspaceLayout })));
const GlobalSearch = lazy(() => import('./components/workspace/GlobalSearch').then(m => ({ default: m.GlobalSearch })));
import { PageTransition } from './components/workspace/PageTransition';
import { ThemeToggle } from './components/ui/ThemeToggle';
const CommandPalette = lazy(() => import('./components/workspace/CommandPalette'));
const MobileLayout = lazy(() => import('./components/mobile/MobileLayout').then(m => ({ default: m.MobileLayout })));
const MobileChatPage = lazy(() => import('./pages/MobileChatPage').then(m => ({ default: m.MobileChatPage })));
import { ErrorBoundary } from './components/ErrorBoundary';

const AgentsPage = lazy(() => import('./pages/AgentsPage').then(m => ({ default: m.AgentsPage })));
const WorkflowsPage = lazy(() => import('./pages/WorkflowsPage').then(m => ({ default: m.WorkflowsPage })));
const ApiKeysPage = lazy(() => import('./pages/ApiKeysPage').then(m => ({ default: m.ApiKeysPage })));
const StatsPage = lazy(() => import('./pages/StatsPage').then(m => ({ default: m.StatsPage })));
const SkillsPage = lazy(() => import('./pages/SkillsPage').then(m => ({ default: m.SkillsPage })));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage').then(m => ({ default: m.NotificationsPage })));
const DoctorPage = lazy(() => import('./pages/DoctorPage').then(m => ({ default: m.DoctorPage })));
const MCPPage = lazy(() => import('./pages/MCPPage').then(m => ({ default: m.MCPPage })));
const FactoryModePage = lazy(() => import('./pages/FactoryModePage').then(m => ({ default: m.FactoryModePage })));
const PluginsPage = lazy(() => import('./pages/PluginsPage').then(m => ({ default: m.PluginsPage })));
const SchedulerPage = lazy(() => import('./pages/SchedulerPage').then(m => ({ default: m.SchedulerPage })));
const ClusterPage = lazy(() => import('./pages/ClusterPage').then(m => ({ default: m.ClusterPage })));
const TracesPage = lazy(() => import('./pages/TracesPage'));
const EvalPage = lazy(() => import('./pages/EvalPage'));
const CostPage = lazy(() => import('./pages/CostPage'));
const PluginPage = lazy(() => import('./pages/PluginPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const TaskMonitorPage = lazy(() => import('./pages/TaskMonitorPage'));
const TaskHistoryPage = lazy(() => import('./pages/TaskHistoryPage').then(m => ({ default: m.TaskHistoryPage })));
const ReasoningPage = lazy(() => import('./pages/ReasoningPage').then(m => ({ default: m.ReasoningPage })));
const ReasoningHistoryPage = lazy(() => import('./pages/ReasoningHistoryPage').then(m => ({ default: m.ReasoningHistoryPage })));
const TerminalPage = lazy(() => import('./pages/TerminalPage'));

const MobileFactoryPage = lazy(() => import('./pages/mobile/MobileFactoryPage').then(m => ({ default: m.MobileFactoryPage })));
const MobileClusterPage = lazy(() => import('./pages/mobile/MobileClusterPage').then(m => ({ default: m.MobileClusterPage })));
const MobileTasksPage = lazy(() => import('./pages/mobile/MobileTasksPage').then(m => ({ default: m.MobileTasksPage })));
const MobileAgentsPage = lazy(() => import('./pages/mobile/MobileAgentsPage').then(m => ({ default: m.MobileAgentsPage })));
const MobileNotificationsPage = lazy(() => import('./pages/mobile/MobileNotificationsPage').then(m => ({ default: m.MobileNotificationsPage })));
const MobileWorkflowsPage = lazy(() => import('./pages/mobile/MobileWorkflowsPage').then(m => ({ default: m.MobileWorkflowsPage })));
const MobileSchedulerPage = lazy(() => import('./pages/mobile/MobileSchedulerPage').then(m => ({ default: m.MobileSchedulerPage })));

type Page = 'chat' | 'agents' | 'workflows' | 'apikeys' | 'skills' | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins' | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost' | 'plugin-manage' | 'settings' | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal';

const CORE_NAV: { id: Page; icon: typeof MessageSquare; label: string; description: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', description: '对话与执行' },
  { id: 'factory', icon: Activity, label: '自主执行', description: '长任务与计划' },
  { id: 'tasks', icon: Cpu, label: '任务监控', description: '实时运行状态' },
];

const ALL_NAV_ITEMS: { id: Page; icon: typeof MessageSquare; label: string; keywords?: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', keywords: 'home workspace dashboard 工作台' },
  { id: 'factory', icon: Activity, label: '自主执行', keywords: 'auto agent execute 自主执行' },
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
      <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
        <div className="w-5 h-5 border-2 rounded-full animate-spin border-[var(--color-accent)] border-t-transparent" />
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
        case 'apikeys': return <ApiKeysPage />;
        case 'skills': return <SkillsPage />;
        case 'doctor': return <DoctorPage />;
        case 'mcp': return <MCPPage />;
        case 'stats': return <StatsPage />;
        case 'plugins': return <PluginsPage />;
        case 'plugin-manage': return <PluginPage />;
        case 'traces': return <TracesPage />;
        case 'eval': return <EvalPage />;
        case 'cost': return <CostPage />;
        case 'settings': return <SettingsPage />;
        case 'terminal': return <TerminalPage />;
        case 'task-history': return <TaskHistoryPage />;
        case 'reasoning': return <ReasoningPage />;
        case 'reasoning-history': return <ReasoningHistoryPage />;
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
    <div className="app-shell flex h-screen overflow-hidden bg-[var(--color-bg-page)]">
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
          <aside className="relative z-50 hidden w-[232px] shrink-0 flex-col border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] md:flex">
            <div className="flex h-14 shrink-0 items-center gap-3 px-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--color-border-default)] bg-[var(--color-text-primary)] text-[var(--color-text-inverse)]">
                <Mountain size={16} strokeWidth={2.25} />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold tracking-[-0.01em] text-[var(--color-text-primary)]">Climber</div>
                <div className="truncate text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-muted)]">AI workspace</div>
              </div>
            </div>

            <nav className="flex-1 overflow-y-auto px-2.5 py-3">
              <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">Workspace</div>
              <div className="space-y-0.5">
              {CORE_NAV.map(({ id, icon: Icon, label, description }) => {
                const isActive = currentPage === id;
                return (
                  <button
                    key={id}
                    onClick={() => navigate(id)}
                    aria-current={isActive ? 'page' : undefined}
                    className="relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-[var(--color-accent)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] data-[active=false]:text-[var(--color-text-secondary)] data-[active=true]:bg-[var(--color-accent-subtle)]"
                    data-active={isActive}
                  >
                    <Icon size={17} strokeWidth={isActive ? 2.5 : 2} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-xs font-semibold text-[var(--color-text-primary)]">{label}</span>
                      <span className="mt-0.5 block text-[10px] text-[var(--color-text-muted)]">{description}</span>
                    </span>
                    {isActive && (
                      <div className="absolute left-0 h-5 w-0.5 rounded-full bg-[var(--color-accent)]" />
                    )}
                  </button>
                );
              })}
              </div>
              <div className="mb-1 mt-6 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">Explore</div>
              <div className="space-y-0.5">
                {ALL_NAV_ITEMS.filter(item => !CORE_NAV.some(core => core.id === item.id) && ['cluster', 'agents', 'workflows', 'scheduler', 'skills', 'notifications'].includes(item.id)).map(({ id, icon: Icon, label }) => (
                  <button key={id} onClick={() => navigate(id)} aria-current={currentPage === id ? 'page' : undefined} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-[var(--color-accent)] transition-colors hover:bg-[var(--color-bg-surface-2)] data-[active=false]:text-[var(--color-text-secondary)] data-[active=true]:bg-[var(--color-accent-subtle)]" data-active={currentPage === id}>
                    <Icon size={15} />
                    <span className="text-xs font-medium">{label}</span>
                  </button>
                ))}
              </div>
              <div className="mb-1 mt-6 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">System</div>
              <button onClick={() => navigate('settings')} aria-current={currentPage === 'settings' ? 'page' : undefined} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-[var(--color-accent)] transition-colors hover:bg-[var(--color-bg-surface-2)] data-[active=false]:text-[var(--color-text-secondary)] data-[active=true]:bg-[var(--color-accent-subtle)]" data-active={currentPage === 'settings'}>
                <Settings size={15} />
                <span className="text-xs font-medium">系统设置</span>
              </button>
            </nav>

            {/* Bottom actions */}
            <div className="space-y-0.5 border-t border-[var(--color-border-subtle)] p-2.5">
              {/* Search */}
              <button
                onClick={() => setActiveOverlay('search')}
                onMouseEnter={() => setHoveredNav('search')}
                onMouseLeave={() => setHoveredNav(null)}
                aria-label="全局搜索"
                  className="relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
                  data-hovered={hoveredNav === 'search'}
               >
                  <Search size={16} />
                  <span className="text-xs font-medium">全局搜索</span><kbd className="ml-auto rounded border border-[var(--color-border-default)] px-1.5 py-0.5 font-mono text-[9px]">/</kbd>
                 {hoveredNav === 'search' && (
                   <div className="nav-tooltip absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded-lg text-xs whitespace-nowrap z-[200] pointer-events-none"
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
                  className="relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
                  data-hovered={hoveredNav === 'commands'}
               >
                  <Menu size={16} />
                  <span className="text-xs font-medium">命令面板</span><kbd className="ml-auto rounded border border-[var(--color-border-default)] px-1.5 py-0.5 font-mono text-[9px]">⌘K</kbd>
                 {hoveredNav === 'commands' && (
                   <div className="nav-tooltip absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 rounded-lg text-xs whitespace-nowrap z-[200] pointer-events-none"
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
          <main className="flex-1 overflow-hidden flex flex-col relative bg-[var(--color-bg-page)]">
            {/* Mobile header */}
            <div className="md:hidden h-12 flex items-center px-3 border-b border-[var(--color-border-subtle)] bg-[rgba(17,17,19,0.9)] backdrop-blur-[24px]">
              <button
                onClick={() => setMobileMenuOpen(true)}
                aria-label="打开导航菜单"
                aria-expanded={mobileMenuOpen}
                className="p-2 rounded-lg transition-all duration-200 active:scale-[0.95] text-[var(--color-text-muted)]"
              >
                <Menu size={18} />
              </button>
              <div className="ml-2.5 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--color-text-primary)] text-[var(--color-text-inverse)]">
                  <Mountain size={12} />
                </div>
                <span className="text-sm font-semibold text-[var(--color-text-primary)]">Climber</span>
              </div>
            </div>

            {/* Page title bar (non-chat pages only) */}
            {!['chat'].includes(currentPage) && activeNavItem && (
              <div className="hidden md:flex items-center gap-3 px-6 h-12 border-b shrink-0 border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]"
              >
                <div className="flex items-center gap-2">
                  <div className="rounded-md bg-[var(--color-accent-subtle)] p-1.5 text-[var(--color-accent)]">
                    <activeNavItem.icon size={14} />
                  </div>
                  <span className="text-sm font-semibold text-[var(--color-text-primary)]">{activeNavItem.label}</span>
                </div>
                {hoverNavItem && hoverNavItem.id !== activeNavItem.id && (
                  <span className="text-xs text-[var(--color-text-muted)]">{hoverNavItem.label}</span>
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

          <Suspense fallback={null}>
            <GlobalSearch isOpen={activeOverlay === 'search'} onClose={() => setActiveOverlay(null)} />
          </Suspense>
          <Suspense fallback={null}>
            <CommandPalette isOpen={activeOverlay === 'commands'} onClose={() => setActiveOverlay(null)} onNavigate={(page) => navigate(page as Page)} />
          </Suspense>
        </>
      )}
    </div>
  );
}
