import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ReactNode } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

const storeState = {
  sessions: [],
  activeSessionId: null,
  rightPanelTab: 'config',
  rightPanelOpen: true,
  focusMode: false,
  expertMode: false,
  permissionMode: 'sandbox',
  autonomyLevel: 3,
  tasks: [],
  snapshots: [],
  setActiveSession: vi.fn(),
  setRightPanelTab: vi.fn(),
  toggleRightPanel: vi.fn(),
  toggleFocusMode: vi.fn(),
  toggleExpertMode: vi.fn(),
  setPermissionMode: vi.fn(),
  setAutonomyLevel: vi.fn(),
  setTasks: vi.fn(),
  addMessage: vi.fn(),
  updateSession: vi.fn(),
  addSnapshot: vi.fn(),
  createSession: vi.fn(),
  deleteSession: vi.fn(),
};

vi.mock('../../../store/workspace', () => ({
  useWorkspaceStore: () => storeState,
}));

vi.mock('../../../layout/breakpoints', () => ({
  useIsFullDesktop: () => true,
  useIsMobile: () => false,
  useIsCompactDesktop: () => false,
}));

vi.mock('../../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('react-resizable-panels', () => ({
  Group: ({ children }: { children?: ReactNode }) => <div data-testid="panel-group">{children}</div>,
  Panel: ({ children }: { children?: ReactNode }) => <div data-testid="panel">{children}</div>,
  Separator: () => <div data-testid="panel-separator" />,
}));

vi.mock('../../workspace/ControlBar', () => ({
  ControlBar: () => <div data-testid="control-bar" />,
}));

vi.mock('../../workspace/SessionSidebar', () => ({
  SessionSidebar: () => <div data-testid="session-sidebar" />,
}));

vi.mock('../../workspace/RightPanel', () => ({
  RightPanel: () => <div data-testid="right-panel" />,
}));

vi.mock('../../../pages/ChatPage', () => ({
  ChatPage: () => <div data-testid="chat-page" />,
}));

import { WorkspaceLayout } from '../WorkspaceLayout';

describe('WorkspaceLayout focus mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState.focusMode = false;
    storeState.rightPanelOpen = true;
  });

  it('renders sidebar and right panel when focus mode is off', () => {
    render(<WorkspaceLayout />);
    expect(screen.getByTestId('session-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('right-panel')).toBeInTheDocument();
    expect(screen.getByTestId('chat-page')).toBeInTheDocument();
  });

  it('hides sidebar and right panel and keeps chat full width when focus mode is on', () => {
    storeState.focusMode = true;
    render(<WorkspaceLayout />);
    expect(screen.queryByTestId('session-sidebar')).not.toBeInTheDocument();
    expect(screen.queryByTestId('right-panel')).not.toBeInTheDocument();
    expect(screen.queryByTestId('panel-separator')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-page')).toBeInTheDocument();
    expect(screen.getAllByTestId('panel')).toHaveLength(1);
  });

  it('exits focus mode on Escape', () => {
    storeState.focusMode = true;
    render(<WorkspaceLayout />);
    fireEvent.keyDown(document.body, { key: 'Escape' });
    expect(storeState.toggleFocusMode).toHaveBeenCalledTimes(1);
  });

  it('ignores Escape while typing in an input', () => {
    storeState.focusMode = true;
    render(
      <div>
        <WorkspaceLayout />
        <input data-testid="composer" />
      </div>,
    );
    fireEvent.keyDown(screen.getByTestId('composer'), { key: 'Escape' });
    expect(storeState.toggleFocusMode).not.toHaveBeenCalled();
  });

  it('keeps Escape inert outside focus mode', () => {
    render(<WorkspaceLayout />);
    fireEvent.keyDown(document.body, { key: 'Escape' });
    expect(storeState.toggleFocusMode).not.toHaveBeenCalled();
  });
});
