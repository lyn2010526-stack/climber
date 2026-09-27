import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useWorkspaceStore, type Session } from '../../../store/workspace';
import { ControlBar } from '../ControlBar';

vi.mock('../../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's1',
  title: '会话 Alpha',
  status: 'idle',
  messages: [],
  activeSkills: [],
  activeTools: [],
  modelConfig: { provider: 'openai', modelId: 'gpt-4o', temperature: 0.7, maxTokens: 4096 },
  tokenUsage: { used: 0, limit: 200000 },
  createdAt: Date.now(),
  ...overrides,
});

beforeEach(() => {
  useWorkspaceStore.setState({
    sessions: [],
    sessionsLoaded: false,
    loadingSessions: false,
    activeSessionId: null,
    rightPanelTab: 'config',
    rightPanelOpen: true,
    focusMode: false,
    expertMode: false,
    permissionMode: 'sandbox',
    autonomyLevel: 3,
    tasks: [],
    snapshots: [],
  });
});

describe('ControlBar', () => {
  it('keeps one inspector switch and leaves group navigation to the panel', () => {
    render(<ControlBar />);
    expect(screen.getByRole('toolbar')).toHaveAttribute('aria-orientation', 'horizontal');
    expect(screen.getByRole('button', { name: 'right_panel.title' })).toHaveAttribute('aria-pressed', 'true');
    // The four groups are reached inside the panel, so the bar repeats none of them.
    for (const id of ['overview', 'execution', 'changes', 'activity']) {
      expect(screen.queryByRole('button', { name: `right_panel.groups.${id}` })).not.toBeInTheDocument();
    }
    expect(screen.queryByRole('button', { name: 'right_panel.sections.dag' })).not.toBeInTheDocument();
  });

  it('toggles the inspector with the single switch', () => {
    render(<ControlBar />);
    const inspector = screen.getByRole('button', { name: 'right_panel.title' });
    fireEvent.click(inspector);
    expect(useWorkspaceStore.getState().rightPanelOpen).toBe(false);
    expect(inspector).toHaveAttribute('aria-pressed', 'false');
    expect(inspector).not.toHaveAttribute('aria-controls');
    fireEvent.click(inspector);
    expect(useWorkspaceStore.getState().rightPanelOpen).toBe(true);
    expect(inspector).toHaveAttribute('aria-controls', 'workspace-inspector');
  });

  it('enables session actions only when a session is active', () => {
    render(<ControlBar />);
    for (const name of ['agents.pause', 'chat.stop_generation', '保存快照']) {
      expect(screen.getByRole('button', { name })).toBeDisabled();
    }
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    for (const name of ['chat.stop_generation', '保存快照']) {
      expect(screen.getAllByRole('button', { name })[1]).toBeEnabled();
    }
  });

  it('shows the active session title', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.getByText('会话 Alpha')).toBeInTheDocument();
  });

  it('creates a snapshot from the bar as a session level action', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    fireEvent.click(screen.getByRole('button', { name: '保存快照' }));
    expect(useWorkspaceStore.getState().snapshots).toHaveLength(1);
    expect(useWorkspaceStore.getState().snapshots[0]).toMatchObject({ sessionId: 's1' });
  });

  it('keeps run policy in a keyboard accessible popover and restores focus', async () => {
    const user = userEvent.setup();
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.queryByRole('button', { name: '专家模式' })).not.toBeInTheDocument();
    const more = screen.getByRole('button', { name: 'sidebar.more' });
    await user.click(more);
    expect(screen.getByRole('dialog', { name: 'sidebar.more' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '专家模式' }));
    expect(screen.getByRole('button', { name: '专家模式' })).toHaveAttribute('aria-pressed', 'true');
    await user.keyboard('{Escape}');
    expect(more).toHaveFocus();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('names focus mode with the key that actually leaves it', () => {
    render(<ControlBar />);
    const focus = screen.getByRole('button', { name: '进入专注模式' });
    expect(focus).toHaveAttribute('aria-keyshortcuts', 'Escape');
    expect(focus).toHaveAttribute('title', '进入专注模式 (Esc)');
    fireEvent.click(focus);
    const exit = screen.getByRole('button', { name: '退出专注模式' });
    expect(exit).toHaveAttribute('aria-keyshortcuts', 'Escape');
    expect(exit).toHaveAttribute('title', '退出专注模式 (Esc)');
    expect(exit).toHaveAttribute('aria-pressed', 'true');
  });

  it('retains session actions and exposes bounded token usage', () => {
    useWorkspaceStore.setState({ sessions: [makeSession({ status: 'running', tokenUsage: { used: 300, limit: 200 } })], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
    fireEvent.click(screen.getByRole('button', { name: 'agents.pause' }));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('paused');
    fireEvent.click(screen.getByRole('button', { name: 'agents.resume' }));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('running');
    fireEvent.click(screen.getByRole('button', { name: 'chat.stop_generation' }));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('completed');
  });

  it('groups the session actions under the sessions label', () => {
    render(<ControlBar />);
    const group = screen.getByRole('group', { name: 'navigation.sessions' });
    expect(group).toContainElement(screen.getByRole('button', { name: 'chat.stop_generation' }));
  });
});
