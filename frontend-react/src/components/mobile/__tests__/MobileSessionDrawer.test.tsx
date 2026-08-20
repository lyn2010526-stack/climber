import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileSessionDrawer } from '../MobileSessionDrawer';

const { setActiveSession, createSession, listAgents } = vi.hoisted(() => ({
  setActiveSession: vi.fn(),
  createSession: vi.fn(),
  listAgents: vi.fn().mockResolvedValue([{ id: 'agent-1', name: 'Agent 1' }]),
}));

const sessionState = vi.hoisted(() => ({
  sessions: [] as Array<{
    id: string;
    title: string | null;
    status: string;
    created_at: string;
    updated_at: string;
  }>,
  loading: false,
  error: null as string | null,
}));

vi.mock('../../../store/workspace', () => ({
  useWorkspaceStore: () => ({
    activeSessionId: 'session-1',
    setActiveSession,
  }),
}));

vi.mock('../../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: sessionState.sessions,
    loading: sessionState.loading,
    error: sessionState.error,
    createSession,
  }),
}));

vi.mock('../../../api', () => ({
  api: {
    listAgents,
  },
}));

describe('MobileSessionDrawer', () => {
  beforeEach(() => {
    setActiveSession.mockClear();
    createSession.mockReset();
    listAgents.mockClear();
    sessionState.sessions = [
      { id: 'session-1', title: '会话 1', status: 'idle', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
      { id: 'session-2', title: null, status: 'running', created_at: '2026-01-02T00:00:00Z', updated_at: '2026-01-02T00:00:00Z' },
    ];
    sessionState.loading = false;
    sessionState.error = null;
  });

  const renderDrawer = (onOpenChange = vi.fn()) =>
    render(<MobileSessionDrawer open onOpenChange={onOpenChange} />);

  it('renders session list', () => {
    renderDrawer();
    expect(screen.getByText('会话 1')).toBeDefined();
    expect(screen.getByText('Untitled')).toBeDefined();
    expect(screen.getByText('2 个会话')).toBeDefined();
  });

  it('renders loading state', () => {
    sessionState.loading = true;
    renderDrawer();
    expect(screen.getByText('加载中...')).toBeDefined();
  });

  it('renders empty state', () => {
    sessionState.sessions = [];
    renderDrawer();
    expect(screen.getByText('暂无会话，点击上方新建')).toBeDefined();
  });

  it('selects a session on click and closes the drawer', () => {
    const onOpenChange = vi.fn();
    renderDrawer(onOpenChange);
    fireEvent.click(screen.getByText('会话 1'));
    expect(setActiveSession).toHaveBeenCalledWith('session-1');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('creates a new session, selects it and closes the drawer', async () => {
    createSession.mockResolvedValue({ id: 'session-new', title: '会话 3', status: 'idle', created_at: '' });
    const onOpenChange = vi.fn();
    renderDrawer(onOpenChange);
    fireEvent.click(screen.getByText('新建会话'));
    await waitFor(() => expect(createSession).toHaveBeenCalled());
    await waitFor(() => expect(setActiveSession).toHaveBeenCalledWith('session-new'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
