import { Group, Panel, Separator } from 'react-resizable-panels';
import { SessionSidebar } from './SessionSidebar';
import { ControlBar } from './ControlBar';
import { RightPanel } from './RightPanel';
import { useWorkspaceStore } from '../../store/workspace';
import { ChatPage } from '../../pages/ChatPage';

export function WorkspaceLayout() {
  const rightPanelOpen = useWorkspaceStore(s => s.rightPanelOpen);

  return (
    <div className="flex-1 flex flex-col" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      <ControlBar />
      <div className="flex-1 flex overflow-hidden">
        <SessionSidebar />
        <div className="flex-1 flex overflow-hidden">
          <Group orientation="horizontal">
            <Panel defaultSize={rightPanelOpen ? 70 : 100} minSize={40}>
              <ChatPage />
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
    </div>
  );
}