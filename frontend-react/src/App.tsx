import { useState, useEffect, useCallback, Suspense } from 'react';
import {
  MessageSquare, Bot, Workflow, Users, Key, BarChart3,
  PanelLeftClose, PanelLeft, Server, Brain, Puzzle, Package,
  Clock, Network, Activity, FlaskConical, DollarSign, Settings, Cpu, History,
  Sparkles, Search, Bell, Menu, X, Terminal,
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
import { ThemeToggle } from './components/ui/ThemeToggle';
import TerminalPage from './pages/TerminalPage';

type Page = 'chat' | 'agents' | 'workflows' | 'crews' | 'apikeys' | 'skills' | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins' | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost' | 'plugin-manage' | 'settings' | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal';

const NAV_GROUPS: Record<string, string> = {
  main: '核心功能',
  manage: '管理',
  config: '配置',
};

const navItems: { id: Page; icon: typeof MessageSquare; label: string; group?: string }[] = [
  { id: 'chat', icon: MessageSquare, label: '工作台', group: 'main' },
  { id: 'factory', icon: Brain, label: '自主执行', group: 'main' },
  { id: 'cluster', icon: Network, label: '集群协作', group: 'main' },
  { id: 'tasks', icon: Cpu, label: '任务监控', group: 'main' },
  { id: 'task-history', icon: History, label: '任务历史', group: 'main' },
  { id: 'reasoning', icon: Brain, label: '推理引擎', group: 'main' },
  { id: 'reasoning-history', icon: History, label: '推理历史', group: 'main' },
  { id: 'agents', icon: Bot, label: '智能体', group: 'manage' },
  { id: 'workflows', icon: Workflow, label: '工作流', group: 'manage' },
  { id: 'crews', icon: Users, label: '团队协作', group: 'manage' },
  { id: 'scheduler', icon: Clock, label: '定时任务', group: 'manage' },
  { id: 'plugins', icon: Puzzle, label: '插件市场', group: 'config' },
  { id: 'plugin-manage', icon: Package, label: '插件管理', group: 'config' },
  { id: 'skills', icon: Package, label: '技能中心', group: 'config' },
  { id: 'notifications', icon: Bell, label: '通知中心', group: 'config' },
  { id: 'doctor', icon: Activity, label: '系统诊断', group: 'config' },
  { id: 'mcp', icon: Server, label: 'MCP 市场', group: 'config' },
  { id: 'apikeys', icon: Key, label: 'API 密钥', group: 'config' },
  { id: 'stats', icon: BarChart3, label: '数据统计', group: 'config' },
  { id: 'traces', icon: Activity, label: '链路追踪', group: 'config' },
  { id: 'eval', icon: FlaskConical, label: '效果评估', group: 'config' },
  { id: 'cost', icon: DollarSign, label: '成本控制', group: 'config' },
  { id: 'settings', icon: Settings, label: '系统设置', group: 'config' },
  { id: 'terminal', icon: Terminal, label: '终端沙箱', group: 'config' },
];

const VALID_PAGES = new Set(navItems.map(n => n.id));

function getPageFromHash(): Page {
  const hash = window.location.hash.replace('#', '') || 'chat';
  return VALID_PAGES.has(hash as Page) ? (hash as Page) : 'chat';
}

function PageFallback() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex items-center gap-2 text-gray-500">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs">加载中...</span>
      </div>
    </div>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>(getPageFromHash);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
        setSearchOpen(prev => !prev);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  // Close mobile menu on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navigate = useCallback((page: Page) => {
    window.location.hash = page;
  }, []);

  const renderPage = () => {
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

  const groupedNav = navItems.reduce((acc, item) => {
    const group = item.group || 'other';
    if (!acc[group]) acc[group] = [];
    acc[group].push(item);
    return acc;
  }, {} as Record<string, typeof navItems>);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0A0A0F]">
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
        bg-[#0F0F14]/95 backdrop-blur-2xl border-r border-white/[0.04]
        flex flex-col transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-white/[0.04]">
          {sidebarOpen && (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] flex items-center justify-center shadow-lg shadow-blue-500/20">
                <Sparkles size={16} className="text-white" />
              </div>
              <span className="text-sm font-bold text-white tracking-tight">Climber</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto p-2 rounded-xl hover:bg-white/[0.06] text-gray-400 hover:text-white transition-all duration-200 hidden md:flex active:scale-[0.95]"
          >
            {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeft size={16} />}
          </button>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="ml-auto p-2 rounded-xl hover:bg-white/[0.06] text-gray-400 hover:text-white transition-all duration-200 md:hidden active:scale-[0.95]"
          >
            <X size={16} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2.5 overflow-y-auto space-y-5">
          {Object.entries(groupedNav).map(([group, items]) => (
            <div key={group}>
              {sidebarOpen && group !== 'main' && (
                <div className="px-2 mb-2">
                  <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
                    {NAV_GROUPS[group] || group}
                  </span>
                </div>
              )}
              <div className="space-y-0.5">
                {items.map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => navigate(id)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm
                      transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] group border
                      ${currentPage === id
                        ? 'bg-white/[0.06] text-white shadow-sm shadow-black/20 border-white/[0.08]'
                        : 'text-gray-400 hover:text-white hover:bg-white/[0.03] border-transparent hover:border-white/[0.04]'
                      }
                    `}
                  >
                    <div className={`
                      p-1.5 rounded-xl transition-all duration-200
                      ${currentPage === id
                        ? 'bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-blue-400'
                        : 'bg-white/[0.03] text-gray-500 group-hover:text-gray-300'
                      }
                    `}>
                      <Icon size={14} />
                    </div>
                    {sidebarOpen && (
                      <span className="font-medium">{label}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Search & Theme */}
        <div className="p-3 border-t border-white/[0.04] space-y-2">
          <button
            onClick={() => setSearchOpen(true)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm text-gray-400 hover:text-white hover:bg-white/[0.04] transition-all duration-200 border border-transparent hover:border-white/[0.06] active:scale-[0.98]"
          >
            <div className="p-1.5 rounded-xl bg-white/[0.03] text-gray-500">
              <Search size={14} />
            </div>
            {sidebarOpen && (
                <div className="flex items-center gap-2 flex-1">
                  <span className="font-medium">搜索</span>
                  <kbd className="ml-auto text-[10px] px-1.5 py-0.5 rounded-md bg-white/[0.06] text-gray-500 font-mono border border-white/[0.06]">⌘K</kbd>
                </div>
            )}
          </button>
          <div className="flex items-center justify-between px-1">
            {sidebarOpen && <span className="text-xs text-gray-500">主题</span>}
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col bg-[#0A0A0F] relative">
        {/* Mobile Header */}
        <div className="md:hidden h-12 flex items-center px-4 border-b border-white/[0.04] bg-[#0F0F14]/90 backdrop-blur-xl">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 rounded-xl hover:bg-white/[0.06] text-gray-400 hover:text-white transition-all duration-200 active:scale-[0.95]"
          >
            <Menu size={20} />
          </button>
          <div className="ml-3 flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <span className="text-sm font-bold text-white">Climber</span>
          </div>
        </div>

        <Suspense fallback={<PageFallback />}>
          <div className="flex-1 overflow-hidden page-transition">
            {renderPage()}
          </div>
        </Suspense>
      </main>

      <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
