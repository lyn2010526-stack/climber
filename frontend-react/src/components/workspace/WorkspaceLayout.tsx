import { Group, Panel, Separator } from 'react-resizable-panels';
import { SessionSidebar } from './SessionSidebar';
import { ControlBar } from './ControlBar';
import { RightPanel } from './RightPanel';
import { useEffect, useState } from 'react';
import { useWorkspaceStore } from '../../store/workspace';
import { ChatPage } from '../../pages/ChatPage';

export function WorkspaceLayout() {
  const { rightPanelOpen } = useWorkspaceStore();
  const [compactWorkspace, setCompactWorkspace] = useState(() => window.innerWidth < 1024);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1023px)');
    const updateLayout = () => setCompactWorkspace(media.matches);
    media.addEventListener('change', updateLayout);
    return () => media.removeEventListener('change', updateLayout);
  }, []);

  const showRightPanel = rightPanelOpen && !compactWorkspace;

  return (
    <section className="flex min-h-0 flex-1 flex-col" aria-label="对话工作区" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      <ControlBar />
      <div className="flex min-w-0 flex-1 overflow-hidden">
        <SessionSidebar />
        <div className="flex min-w-0 flex-1 overflow-hidden">
          <Group orientation="horizontal">
            <Panel defaultSize={showRightPanel ? 70 : 100} minSize={40}>
              <ChatPage />
            </Panel>
            {showRightPanel && (
              <>
                 <Separator className="w-1 bg-[var(--color-border-subtle)] transition-colors duration-150 hover:bg-[var(--color-border-accent)] focus-visible:bg-[var(--color-accent)]" />
                <Panel defaultSize={30} minSize={20} maxSize={40}>
                  <RightPanel />
                </Panel>
              </>
            )}
          </Group>
        </div>
      </div>
    </section>
  );
}
