import { useEffect } from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { SessionSidebar } from './SessionSidebar';
import { ControlBar } from './ControlBar';
import { RightPanel } from './RightPanel';
import { useI18n } from '../../i18n';
import { useIsFullDesktop } from '../../layout/breakpoints';
import { useWorkspaceStore } from '../../store/workspace';
import { ChatPage } from '../../pages/ChatPage';

const RIGHT_PANEL_WIDTH = 360;
const RIGHT_PANEL_MIN = 280;
const RIGHT_PANEL_MAX = 460;

export function WorkspaceLayout() {
  const { t } = useI18n();
  const { rightPanelOpen, focusMode, toggleFocusMode } = useWorkspaceStore();
  const isFullDesktop = useIsFullDesktop();

  const showRightPanel = rightPanelOpen && isFullDesktop && !focusMode;

  useEffect(() => {
    if (!focusMode) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target as HTMLElement | null;
      // Escape during text input belongs to the editor; only exit focus mode from neutral focus
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
      toggleFocusMode();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [focusMode, toggleFocusMode]);

  if (focusMode) {
    return (
      <section className="flex min-h-0 flex-1 flex-col" aria-label={t('sidebar.workspace')} style={{ backgroundColor: 'var(--color-bg-page)' }}>
        <ControlBar />
        <div className="flex min-w-0 flex-1 overflow-hidden">
          <Group orientation="horizontal">
            <Panel>
              <ChatPage />
            </Panel>
          </Group>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col" aria-label={t('sidebar.workspace')} style={{ backgroundColor: 'var(--color-bg-page)' }}>

      <ControlBar />
      <div className="flex min-w-0 flex-1 overflow-hidden">
        <SessionSidebar />
        <div className="flex min-w-0 flex-1 overflow-hidden">
          <Group orientation="horizontal">
            <Panel minSize={40}>
              <ChatPage />
            </Panel>
            {showRightPanel && (
              <>
                <Separator className="w-1 bg-[var(--color-border-subtle)] transition-colors duration-150 hover:bg-[var(--color-border-accent)] focus-visible:bg-[var(--color-accent)]" />
                <Panel defaultSize={`${RIGHT_PANEL_WIDTH}px`} minSize={`${RIGHT_PANEL_MIN}px`} maxSize={`${RIGHT_PANEL_MAX}px`} groupResizeBehavior="preserve-pixel-size">
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
