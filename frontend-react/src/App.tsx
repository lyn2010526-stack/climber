import { useState, useEffect, useCallback, Suspense } from 'react';
import {
  MessageSquare, Bot, Network, Cpu, BarChart3,
  PanelLeftClose, PanelLeft, Sparkles, Search, Bell, Menu, X,
  Settings, Workflow, Terminal, Key, Activity, FlaskConical, DollarSign,
  Puzzle, Package, Clock, Users, History,
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

type Page = 'chat' | 'agents' | 'workflows' | 'crews' | 'apikeys' | 'skills' | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins' | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost' | 'plugin-manage' | 'settings' | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal';

const CORE_NAV_ITEMS: { id: Page; icon: typeof MessageSquare; label: string; group?: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', group: 'main' },
  { id: 'factory', icon: Sparkles, label: '自主执行', group: 'main' },
  { id: 'cluster', icon: Network, label: '集群协作', group: 'main' },
  { id: 'tasks', icon: Cpu, label: '任务监控', group: 'main' },
  { id: 'agents', icon: Bot, label: '智能体', group: 'manage' },
  { id: 'settings', icon: Settings, label: '设置', group: 'config' },
];

const ALL_NAV_ITEMS: { id: Page; icon: typeof MessageSquare; label: string; group?: string; keywords?: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', group: 'main', keywords: 'home workspace dashboard 工作台' },
  { id: 'factory', icon: Sparkles, label: '自主执行', group: 'main', keywords: 'auto agent execute 自主执行' },
  { id: 'cluster', icon: Network, label: '集群协作', group: 'main', keywords: 'multi agent team 集群协作' },
  { id: 'tasks', icon: Cpu, label: '任务监控', group: 'main', keywords: 'monitor task running 任务监控' },
  { id: 'task-history', icon: History, label: '任务历史', group: 'main', keywords: 'history past 任务历史' },
  { id: 'reasoning', icon: Activity, label: '推理引擎', group: 'main', keywords: 'reason think 推理引擎' },
  { id: 'reasoning-history', icon: History, label: '推理历史', group: 'main', keywords: 'reasoning history 推理历史' },
  { id: 'agents', icon: Bot, label: '智能体', group: 'manage', keywords: 'agent config 智能体' },
  { id: 'workflows', icon: Workflow, label: '工作流', group: 'manage', keywords: 'workflow dag 工作流' },
  { id: 'crews', icon: Users, label: '团队协作', group: 'manage', keywords: 'crew team 团队协作' },
  { id: 'scheduler', icon: Clock, label: '定时任务', group: 'manage', keywords: 'cron schedule 定时任务' },
  { id: 'plugins', icon: Puzzle, label: '插件市场', group: 'config', keywords: 'plugin marketplace 插件市场' },
  { id: 'plugin-manage', icon: Package, label: '插件管理', group: 'config', keywords: 'plugin manage installed 插件管理' },
  { id: 'skills', icon: Package, label: '技能中心', group: 'config', keywords: 'skill tool 技能中心' },
  { id: 'notifications', icon: Bell, label: '通知中心', group: 'config', keywords: 'notification alert 通知中心' },
  { id: 'doctor', icon: Activity, label: '系统诊断', group: 'config', keywords: 'health debug 系统诊断' },
  { id: 'mcp', icon: Terminal, label: 'MCP 市场', group: 'config', keywords: 'mcp protocol tool  MCP 市场' },
  { id: 'apikeys', icon: Key, label: 'API 密钥', group: 'config', keywords: 'api key secret API 密钥' },
  { id: 'stats', icon: BarChart3, label: '数据统计', group: 'config', keywords: 'stats analytics chart 数据统计' },
  { id: 'traces', icon: Activity, label: '链路追踪', group: 'config', keywords: 'trace debug 链路追踪' },
  { id: 'eval', icon: FlaskConical, label: '效果评估', group: 'config', keywords: 'eval benchmark 效果评估' },
  { id: 'cost', icon: DollarSign, label: '成本控制', group: 'config', keywords: 'cost billing token 成本控制' },
  { id: 'settings', icon: Settings, label: '系统设置', group: 'config', keywords: 'settings config preference 系统设置' },
  { id: 'terminal', icon: Terminal, label: '终端沙箱', group: 'config', keywords: 'terminal shell 终端沙箱' },
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeOverlay, setActiveOverlay] = useState<'search' | 'commands' | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

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
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setMobileMenuOpen(false);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navigate = useCallback((page: Page) => {
    setCurrentPage(page as Page);
    window.location.hash = page;
    if (isMobile) {
      setMobileMenuOpen(false);
    }
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
      case 'crews': return <ClusterPage />;
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

  return (
    <div className="app-shell flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      {isMobile ? (
        <MobileLayout currentPage={currentPage} onNavigate={(page) => navigate(page as any)}>
          <Suspense fallback={<PageFallback />}>
            <PageTransition transitionKey={currentPage}>
              {renderPage()}
            </PageTransition>
          </Suspense>
        </MobileLayout>
      ) : (
        <>
          {/* Mobile Overlay */}
          {mobileMenuOpen && (
            <div
              className="mobile-overlay md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
          )}

          {/* Sidebar */}
          <aside className={`
            fixed md:relative inset-y-0 left-0 z-50
            ${sidebarOpen ? 'w-60' : 'w-16'}
            flex flex-col transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
            ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          `} style={{
            backgroundColor: 'var(--color-bg-surface-1)',
            borderRight: '1px solid var(--color-border-subtle)',
          }}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
          {sidebarOpen && (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-2xl flex items-center justify-center" style={{
                background: 'linear-gradient(135deg, var(--color-accent), #8B5CF6)',
                boxShadow: '0 0 20px var(--color-accent-glow)'
              }}>
                <Sparkles size={16} className="text-white" />
              </div>
              <span className="text-sm font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>Climber</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
            aria-expanded={sidebarOpen}
            className="ml-auto p-2 rounded-xl transition-all duration-200 active:scale-[0.95] hidden md:flex"
            style={{ color: 'var(--color-text-muted)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
              e.currentTarget.style.color = 'var(--color-text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--color-text-muted)';
            }}
          >
            {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeft size={16} />}
          </button>
          <button
            onClick={() => setMobileMenuOpen(false)}
            aria-label="关闭导航菜单"
            className="ml-auto p-2 rounded-xl transition-all duration-200 active:scale-[0.95] md:hidden"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Search trigger */}
        <div className="p-3">
          <button
            onClick={() => setActiveOverlay('search')}
            aria-label="全局搜索"
            className="w-full flex items-center gap-3 px-3 py-2 rounded-2xl text-sm transition-all duration-200 active:scale-[0.98]"
            style={{
              color: 'var(--color-text-muted)',
              border: '1px solid var(--color-border-subtle)',
              backgroundColor: 'var(--color-bg-surface-2)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-border-default)';
              e.currentTarget.style.color = 'var(--color-text-secondary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
              e.currentTarget.style.color = 'var(--color-text-muted)';
            }}
          >
            <Search size={14} />
            {sidebarOpen && (
              <div className="flex items-center gap-2 flex-1">
                <span>搜索...</span>
                <kbd className="ml-auto text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
                  backgroundColor: 'var(--color-bg-surface-3)',
                  color: 'var(--color-text-muted)',
                  border: '1px solid var(--color-border-subtle)'
                }}>搜索</kbd>
              </div>
            )}
          </button>
        </div>

        {/* Core Navigation */}
        <nav className="flex-1 py-3 px-2.5 overflow-y-auto">
          <div className="space-y-0.5">
            {CORE_NAV_ITEMS.map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => navigate(id)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm
                  transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] border relative
                `}
                style={{
                  color: currentPage === id ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'transparent',
                  borderColor: currentPage === id ? 'var(--color-border-accent)' : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (currentPage !== id) {
                    e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentPage !== id) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--color-text-muted)';
                  }
                }}
              >
                {currentPage === id && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full" style={{
                    backgroundColor: 'var(--color-accent)',
                    boxShadow: '0 0 8px var(--color-accent-glow)'
                  }} />
                )}
                <div className={`
                  p-1.5 rounded-xl transition-all duration-200
                  ${currentPage === id ? '' : ''}
                `} style={{
                  backgroundColor: currentPage === id ? 'rgba(94,106,210,0.15)' : 'var(--color-bg-surface-2)',
                  color: currentPage === id ? 'var(--color-accent)' : 'var(--color-text-muted)',
                }}>
                  <Icon size={14} />
                </div>
                {sidebarOpen && (
                  <span className="font-medium">{label}</span>
                )}
              </button>
            ))}
          </div>

          {/* Separator */}
          {sidebarOpen && (
            <div className="my-4 mx-2" style={{ borderBottom: '1px solid var(--color-border-subtle)' }} />
          )}

          {/* More pages list (compact) */}
          {sidebarOpen && (
            <div className="space-y-0.5">
              {ALL_NAV_ITEMS.filter(item => !CORE_NAV_ITEMS.find(core => core.id === item.id)).slice(0, 8).map(({ id, icon: Icon, label }) => (
                <button
                  key={id}
                  onClick={() => navigate(id)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-2xl text-sm transition-all duration-200"
                  style={{
                    color: currentPage === id ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                    backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'transparent',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = currentPage === id ? 'var(--color-accent-subtle)' : 'transparent';
                    e.currentTarget.style.color = currentPage === id ? 'var(--color-text-primary)' : 'var(--color-text-muted)';
                  }}
                >
                  <div className="p-1.5 rounded-xl" style={{
                    backgroundColor: 'var(--color-bg-surface-2)',
                    color: 'var(--color-text-muted)',
                  }}>
                    <Icon size={13} />
                  </div>
                  <span className="text-xs">{label}</span>
                </button>
              ))}
            </div>
          )}
        </nav>

        {/* Bottom: Theme + Cmd+K */}
        <div className="p-3 space-y-2" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
          {sidebarOpen && (
            <button
              onClick={() => setActiveOverlay('commands')}
              aria-label="打开命令面板"
              className="w-full flex items-center gap-3 px-3 py-2 rounded-2xl text-xs transition-all duration-200 active:scale-[0.98]"
              style={{
                color: 'var(--color-text-muted)',
                border: '1px solid var(--color-border-subtle)',
                backgroundColor: 'var(--color-bg-surface-2)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-border-default)';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                e.currentTarget.style.color = 'var(--color-text-muted)';
              }}
            >
              <Search size={13} />
              <span className="flex-1 text-left">命令面板</span>
              <kbd className="text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
                backgroundColor: 'var(--color-bg-surface-3)',
                color: 'var(--color-text-muted)',
                border: '1px solid var(--color-border-subtle)'
              }}>⌘K</kbd>
            </button>
          )}
          <div className="flex items-center justify-between px-1">
            {sidebarOpen && <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>主题</span>}
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col relative" style={{ backgroundColor: 'var(--color-bg-page)' }}>
        {/* Mobile Header */}
        <div className="md:hidden h-12 flex items-center px-4" style={{
          borderBottom: '1px solid var(--color-border-subtle)',
          backgroundColor: 'rgba(10,10,15,0.9)',
          backdropFilter: 'blur(24px)',
        }}>
          <button
            onClick={() => setMobileMenuOpen(true)}
            aria-label="打开导航菜单"
            aria-expanded={mobileMenuOpen}
            className="p-2 rounded-xl transition-all duration-200 active:scale-[0.95]"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <Menu size={20} />
          </button>
          <div className="ml-3 flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl flex items-center justify-center" style={{
              background: 'linear-gradient(135deg, var(--color-accent), #8B5CF6)',
            }}>
              <Sparkles size={14} className="text-white" />
            </div>
            <span className="text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>Climber</span>
          </div>
        </div>

        <Suspense fallback={<PageFallback />}>
          <PageTransition transitionKey={currentPage}>
            {renderPage()}
          </PageTransition>
        </Suspense>
      </main>

        <GlobalSearch isOpen={activeOverlay === 'search'} onClose={() => setActiveOverlay(null)} />
        <CommandPalette isOpen={activeOverlay === 'commands'} onClose={() => setActiveOverlay(null)} onNavigate={(page) => navigate(page as Page)} />
      </>
    )}
  </div>
  );
}
