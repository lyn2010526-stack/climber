import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useWorkspaceStore, type Session } from '../../../store/workspace';
import { ControlBar } from '../ControlBar';

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

describe('ControlBar right panel tab buttons', () => {
  it('renders entries for all right panel tabs including diff, toolcalls and reasoning', () => {
    render(<ControlBar />);
    expect(screen.getByRole('button', { name: '配置面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Diff面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '工具面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'DAG面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '链路面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '推理面板' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '文件面板' })).toBeInTheDocument();
  });

  it('disables session-bound tabs and shows hint title without active session', () => {
    render(<ControlBar />);
    for (const name of ['Diff面板', '工具面板', '推理面板']) {
      const button = screen.getByRole('button', { name });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('title', 'Select a session');
    }
    expect(screen.getByRole('button', { name: '配置面板' })).toBeEnabled();
  });

  it('enables session-bound tabs when a session is active', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.getByRole('button', { name: 'Diff面板' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '工具面板' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '推理面板' })).toBeEnabled();
  });

  it('marks the active tab with aria-pressed', () => {
    render(<ControlBar />);
    const config = screen.getByRole('button', { name: '配置面板' });
    const diff = screen.getByRole('button', { name: 'Diff面板' });
    expect(config).toHaveAttribute('aria-pressed', 'true');
    expect(diff).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows the active session title', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    expect(screen.getByText('会话 Alpha')).toBeInTheDocument();
  });
});
