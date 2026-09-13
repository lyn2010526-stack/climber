import { useState, useEffect, useCallback, Suspense, lazy } from 'react';
import {
  PanelLeftClose, PanelLeft, Search,
} from 'lucide-react';
import { ClimberMark } from './components/brand/ClimberMark';
import { GlobalSearch } from './components/workspace/GlobalSearch';
import { PageTransition } from './components/workspace/PageTransition';
import { IOsToaster } from './components/ios';
import { ThemeToggle } from './components/ui/ThemeToggle';
import CommandPalette from './components/workspace/CommandPalette';
import { AdaptiveMobileLayout } from './components/layout/AdaptiveMobileLayout';
import { MobileChatPage } from './pages/MobileChatPage';
import { MobileFactoryPage } from './pages/mobile/MobileFactoryPage';
import { MobileClusterPage } from './pages/mobile/MobileClusterPage';
import { MobileTasksPage } from './pages/mobile/MobileTasksPage';
import { useI18n } from './i18n';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { useIsMobile } from './layout/breakpoints';
import { useSidebarState } from './layout/useSidebarState';
import { CORE_NAV_ITEMS_BASE, ALL_NAV_ITEMS_BASE, NAV_ITEM_IDS } from './navigation/navConfig';
import type { Page } from './navigation/navConfig';

const WorkspaceLayout = lazy(() => import('./components/workspace/WorkspaceLayout').then(m => ({ default: m.WorkspaceLayout })));
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
const DemoVisualHierarchy = lazy(() => import('./pages/DemoVisualHierarchy'));
const AuthApiKeysPage = lazy(() => import('./pages/AuthApiKeysPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));

const VALID_PAGES = new Set([...NAV_ITEM_IDS, 'demo']);

function getPageFromHash(): Page {
  const hash = window.location.hash.replace('#', '');
  return VALID_PAGES.has(hash as Page) ? (hash as Page) : 'chat';
}

function PageFallback() {
  const { t } = useI18n();
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
        <div className="w-5 h-5 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }} />
        <span className="text-xs">{t('common.loading')}</span>
      </div>
    </div>
  );
}

export default function App() {
  const { t } = useI18n();
  const CORE_NAV_ITEMS = CORE_NAV_ITEMS_BASE.map(item => ({ ...item, label: item.label ?? t(item.labelKey!) }));
  const ALL_NAV_ITEMS = ALL_NAV_ITEMS_BASE.map(item => ({ ...item, label: item.label ?? t(item.labelKey!) }));
  const [currentPage, setCurrentPage] = useState<Page>(getPageFromHash);
  const { open: sidebarOpen, toggle: toggleSidebar } = useSidebarState();
  const [activeOverlay, setActiveOverlay] = useState<'search' | 'commands' | null>(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    const onHashChange = () => setCurrentPage(getPageFromHash());
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

  const navigate = useCallback((page: Page) => {
    setCurrentPage(page);
    window.location.hash = page;
  }, []);

  const renderPage = () => {
    if (isMobile) {
      switch (currentPage) {
        case 'dashboard': return <DashboardPage />;
        case 'chat': return <MobileChatPage />;
        case 'factory': return <MobileFactoryPage />;
        case 'cluster': return <MobileClusterPage />;
        case 'tasks': return <MobileTasksPage />;
        case 'agents': return <AgentsPage />;
        case 'settings': return <SettingsPage />;
      }
    }
    switch (currentPage) {
      case 'dashboard': return <DashboardPage />;
      case 'chat': return <WorkspaceLayout />;
      case 'agents': return <AgentsPage />;
      case 'workflows': return <WorkflowsPage />;
      case 'crews': return <ClusterPage />;
      case 'apikeys': return <ApiKeysPage />;
      case 'authapikeys': return <AuthApiKeysPage />;
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
      case 'demo': return <DemoVisualHierarchy />;
    }
  };

  return (
    <div className="app-shell flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      {isMobile ? (
        <AdaptiveMobileLayout currentPage={currentPage} onNavigate={(page) => navigate(page as Page)}>
          <Suspense fallback={<PageFallback />}>
            <PageTransition transitionKey={currentPage}>
              {renderPage()}
            </PageTransition>
          </Suspense>
        </AdaptiveMobileLayout>
      ) : (
        <>
          <aside
            aria-label={t('sidebar.main_nav')}
            className="relative flex shrink-0 flex-col"
            style={{
              width: sidebarOpen ? 'var(--desktop-sidebar-width)' : 'var(--sidebar-collapsed-width)',
              backgroundColor: 'var(--color-bg-surface-1)',
              borderRight: '1px solid var(--color-border-subtle)',
              transition: 'width 180ms ease',
            }}
          >
            <div className="flex items-center px-3 shrink-0" style={{ height: 'var(--header-height)', borderBottom: '1px solid var(--color-border-subtle)' }}>
              {sidebarOpen && (
                <div className="flex items-center gap-2.5">
                  <div className="workspace-mark">
                    <ClimberMark size={16} className="text-white" />
                  </div>
                  <span className="text-sm font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>Climber</span>
                </div>
              )}
              <button
                onClick={toggleSidebar}
                aria-label={sidebarOpen ? t('sidebar.collapse') : t('sidebar.expand')}
                aria-expanded={sidebarOpen}
                className="ml-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
              >
                {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeft size={16} />}
              </button>
            </div>

            <div className="p-3">
              <button
                onClick={() => setActiveOverlay('search')}
                aria-label={t('sidebar.global_search')}
                className="flex h-11 w-full items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-border-default)] hover:text-[var(--color-text-secondary)]"
              >
                <Search size={14} />
                {sidebarOpen && (
                  <div className="flex items-center gap-2 flex-1">
                    <span>{t('common.search')}...</span>
                    <kbd className="ml-auto text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
                      backgroundColor: 'var(--color-bg-surface-3)',
                      color: 'var(--color-text-muted)',
                      border: '1px solid var(--color-border-subtle)'
                    }}>⌘K</kbd>
                  </div>
                )}
              </button>
            </div>

            <nav className="flex-1 overflow-y-auto px-2.5 py-2" aria-label={t('sidebar.workspace')}>
              <div className="space-y-0.5">
                {CORE_NAV_ITEMS.map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => navigate(id)}
                    aria-label={label}
                    aria-current={currentPage === id ? 'page' : undefined}
                    title={sidebarOpen ? undefined : label}
                    className="relative flex h-11 w-full items-center gap-3 rounded-lg border px-3 text-sm transition-colors"
                    style={{
                      color: currentPage === id ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                      backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'transparent',
                      borderColor: currentPage === id ? 'var(--color-border-accent)' : 'transparent',
                    }}
                  >
                    {currentPage === id && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full" style={{
                        backgroundColor: 'var(--color-accent)',
                        boxShadow: '0 0 8px var(--color-accent-glow)'
                      }} />
                    )}
                    <div className="p-1.5 rounded-md transition-colors" style={{
                      backgroundColor: currentPage === id ? 'var(--color-accent-subtle)' : 'transparent',
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

              {sidebarOpen && <p className="px-3 pt-4 text-xs leading-5 text-[var(--color-text-muted)]">{t('common.command_hint')}</p>}
            </nav>

            <div className="p-3 space-y-2 shrink-0" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
              {sidebarOpen && (
                <LanguageSwitcher showFlag compact />
              )}
              <div className="flex items-center justify-between px-1">
                {sidebarOpen && <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{t('common.theme')}</span>}
                <ThemeToggle />
              </div>
            </div>
          </aside>

          <main id="main-content" className="min-w-0 flex-1 overflow-hidden flex flex-col relative" style={{ backgroundColor: 'var(--color-bg-page)' }}>
            <header className="desktop-context-bar">
              <div className="min-w-0">
                <p className="workspace-eyebrow">Workspace</p>
                <p className="truncate text-sm font-semibold text-[var(--color-text-primary)]">{ALL_NAV_ITEMS.find(item => item.id === currentPage)?.label ?? currentPage}</p>
              </div>
              <button className="context-command" onClick={() => setActiveOverlay('commands')} aria-label={t('sidebar.command_menu')}>
                <Search size={14} /><span>Command menu</span><kbd>⌘K</kbd>
              </button>
            </header>

            <Suspense fallback={<PageFallback />}>
              <PageTransition transitionKey={currentPage}>
                {renderPage()}
              </PageTransition>
            </Suspense>
          </main>

          <GlobalSearch isOpen={activeOverlay === 'search'} onClose={() => setActiveOverlay(null)} />
          <CommandPalette isOpen={activeOverlay === 'commands'} onClose={() => setActiveOverlay(null)} onNavigate={(page) => navigate(page as Page)} />
          <IOsToaster position="top-center" theme="dark" />
        </>
      )}
    </div>
  );
}
