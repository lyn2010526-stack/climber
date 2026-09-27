import { useEffect } from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { SessionSidebar } from './SessionSidebar';
import { ControlBar } from './ControlBar';
import { RightPanel } from './RightPanel';
import { useI18n } from '../../i18n';
import { useIsWideDesktop } from '../../layout/breakpoints';
import { useWorkspaceStore } from '../../store/workspace';
import { ChatPage } from '../../pages/ChatPage';

const RIGHT_PANEL_WIDTH = 360;
const RIGHT_PANEL_MIN = 280;
const RIGHT_PANEL_MAX = 460;

export function WorkspaceLayout() {
  const { t } = useI18n();
  const { rightPanelOpen, focusMode, toggleFocusMode, toggleRightPanel } = useWorkspaceStore();
  const isWideDesktop = useIsWideDesktop();

  const showRightPanel = rightPanelOpen && isWideDesktop && !focusMode;
  const showRightDrawer = rightPanelOpen && !isWideDesktop && !focusMode;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target as HTMLElement | null;
      // Escape during text input belongs to the editor; only exit focus mode from neutral focus
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
      if (focusMode) toggleFocusMode();
      else if (showRightDrawer) toggleRightPanel();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [focusMode, showRightDrawer, toggleFocusMode, toggleRightPanel]);

  useEffect(() => {
    if (rightPanelOpen) return;
    document.querySelector<HTMLButtonElement>('[data-testid="right-panel-toggle"]')?.focus();
  }, [rightPanelOpen]);

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
          <Group orientation="horizontal" className="min-w-0 flex-1">
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
        {showRightDrawer && (
          <div
            className="relative z-20 flex h-full w-[min(360px,42%)] shrink-0 flex-col border-l border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[-12px_0_28px_rgba(0,0,0,0.16)]"
            data-testid="right-panel-drawer"
            id="workspace-inspector"
            role="dialog"
            aria-label={t('right_panel.title')}
          >
            <RightPanel />
          </div>
        )}
      </div>
    </section>
  );
}
