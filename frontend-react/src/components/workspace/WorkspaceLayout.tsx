import { useState, Suspense, lazy } from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { Drawer } from 'vaul';
import { X } from 'lucide-react';
import { ControlBar } from './ControlBar';
import { SessionSidebar } from './SessionSidebar';
import { RightPanel } from './RightPanel';
import { useWorkspaceStore } from '../../store/workspace';

const ChatPage = lazy(() => import('../../pages/ChatPage').then(m => ({ default: m.ChatPage })));

export function WorkspaceLayout() {
  const rightPanelOpen = useWorkspaceStore(s => s.rightPanelOpen);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);

  return (
    <div className="flex-1 flex flex-col" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      <ControlBar onToggleSessions={() => setSessionDrawerOpen(true)} />
      <div className="flex-1 flex overflow-hidden">
        <div className="hidden xl:flex">
          <SessionSidebar />
        </div>
        <div className="flex-1 flex overflow-hidden min-w-0">
          <Group orientation="horizontal">
            <Panel defaultSize={100} minSize={40}>
              <Suspense fallback={null}>
                <ChatPage onRequestSession={() => setSessionDrawerOpen(true)} />
              </Suspense>
            </Panel>
            {rightPanelOpen && (
              <>
                <Separator className="w-px transition-colors duration-200 cursor-col-resize" style={{ backgroundColor: 'var(--color-border-subtle)' }} />
                <Panel defaultSize={30} minSize={20} maxSize={40}>
                  <RightPanel />
                </Panel>
              </>
            )}
          </Group>
        </div>
      </div>

      <Drawer.Root open={sessionDrawerOpen} onOpenChange={setSessionDrawerOpen}>
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-[100] bg-black/45 backdrop-blur-[2px]" />
          <Drawer.Content className="fixed bottom-0 left-0 top-0 z-[101] w-72 border-r border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] outline-none">
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-4 h-12 shrink-0" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>会话列表</span>
                <button onClick={() => setSessionDrawerOpen(false)} aria-label="关闭会话列表" className="p-2 rounded-lg transition-all duration-200" style={{ color: 'var(--color-text-muted)' }}>
                  <X size={15} />
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <SessionSidebar inDrawer />
              </div>
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </div>
  );
}
