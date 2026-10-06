import { describe, it, expect, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useWorkspaceStore, type Session } from '../../../store/workspace';
import { ControlBar } from '../ControlBar';
import i18n from '../../../i18n/config';

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

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
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

describe('ControlBar slim (anchored workspace wiring)', () => {
  it('renders the slim strip with session actions and drops the full-bar furniture', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar variant="slim" />);

    const bar = screen.getByTestId('anchored-control-bar');
    expect(bar).toHaveAttribute('data-variant', 'slim');
    expect(bar).toHaveAttribute('aria-orientation', 'horizontal');
    // Slim keeps the session actions…
    expect(screen.getByRole('button', { name: '停止生成' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '复制记录' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '进入专注模式' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '更多' })).toBeInTheDocument();
    // …but none of the full-bar furniture the anchored layout already owns.
    expect(screen.queryByRole('button', { name: '运行面板' })).toBeNull();
    expect(screen.queryByTestId('right-panel-toggle')).toBeNull();
    expect(screen.queryByText('会话 Alpha')).toBeNull();
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('saves a snapshot of the active session from the slim bar', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar variant="slim" />);
    fireEvent.click(screen.getByRole('button', { name: '复制记录' }));
    expect(useWorkspaceStore.getState().snapshots).toHaveLength(1);
    expect(useWorkspaceStore.getState().snapshots[0]).toMatchObject({ sessionId: 's1' });
  });

  it('toggles expert mode from the slim bar popover', async () => {
    const user = userEvent.setup();
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar variant="slim" />);
    await user.click(screen.getByRole('button', { name: '更多' }));
    await user.click(screen.getByRole('button', { name: '专家模式' }));
    expect(useWorkspaceStore.getState().expertMode).toBe(true);
  });

  it('toggles focus mode with the documented Escape contract intact', () => {
    render(<ControlBar variant="slim" />);
    const focus = screen.getByRole('button', { name: '进入专注模式' });
    expect(focus).toHaveAttribute('aria-keyshortcuts', 'Escape');
    fireEvent.click(focus);
    expect(useWorkspaceStore.getState().focusMode).toBe(true);
    expect(screen.getByRole('button', { name: '退出专注模式' })).toHaveAttribute('aria-pressed', 'true');
  });
});
