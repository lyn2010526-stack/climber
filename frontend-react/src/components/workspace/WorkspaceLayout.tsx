import { Group, Panel, Separator } from 'react-resizable-panels';
import { SessionSidebar } from './SessionSidebar';
import { ControlBar } from './ControlBar';
import { RightPanel } from './RightPanel';
import { useWorkspaceStore } from '../../store/workspace';
import { ChatPage } from '../../pages/ChatPage';

export function WorkspaceLayout() {
  const { rightPanelOpen } = useWorkspaceStore();

  return (
    <div className="flex-1 flex flex-col bg-[#0A0A0F]">
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
                <Separator className="w-px bg-white/10 hover:bg-[#007AFF]/30 transition-colors cursor-col-resize" />
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
