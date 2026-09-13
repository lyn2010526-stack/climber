import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { useWorkspaceStore } from '../../../store/workspace';

vi.mock('../../../api', () => ({
  api: {
    listSessions: vi.fn(),
    createSession: vi.fn(),
    deleteSession: vi.fn(),
    listAgents: vi.fn(),
    listModels: vi.fn(),
  },
}));

import { api } from '../../../api';
import { SessionSidebar } from '../SessionSidebar';

beforeEach(() => {
  vi.clearAllMocks();
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
  vi.mocked(api.listAgents).mockResolvedValue([{ id: 'agent-1', name: 'Nova' }] as any);
  vi.mocked(api.listModels).mockResolvedValue([
    { provider: 'openai', model_id: 'gpt-4o', label: 'gpt-4o' },
  ] as any);
  vi.mocked(api.listSessions).mockResolvedValue([] as any);
});

describe('SessionSidebar with workspace store', () => {
  it('loads backend sessions into the store and renders them', async () => {
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'b1', title: '会话 一', status: 'idle', created_at: '2026-01-01T00:00:00' },
      { id: 'b2', title: '会话 二', status: 'idle', created_at: '2026-01-02T00:00:00' },
    ] as any);

    render(<SessionSidebar />);

    expect(await screen.findByText('会话 一')).toBeInTheDocument();
    expect(screen.getByText('会话 二')).toBeInTheDocument();
    expect(api.listSessions).toHaveBeenCalledTimes(1);
    expect(useWorkspaceStore.getState().sessions.map((s) => s.id)).toEqual(['b1', 'b2']);
  });

  it('activates clicked session in the shared store', async () => {
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'b1', title: '会话 一', status: 'idle', created_at: null },
    ] as any);

    render(<SessionSidebar />);
    fireEvent.click(await screen.findByText('会话 一'));

    expect(useWorkspaceStore.getState().activeSessionId).toBe('b1');
  });

  it('creates a session via api with model info, sets it active in store', async () => {
    vi.mocked(api.listSessions).mockResolvedValue([] as any);
    vi.mocked(api.createSession).mockResolvedValue({ id: 'new-1', title: '会话 1', status: 'idle' } as any);

    render(<SessionSidebar />);

    const createButton = await screen.findByRole('button', { name: /新建会话/ });
    await waitFor(() => expect(createButton).toBeEnabled());
    fireEvent.click(createButton);

    await waitFor(() => expect(api.createSession).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.createSession).mock.calls[0][0];
    expect(payload.title).toBe('会话 1');
    expect(payload.agent_id).toBe('agent-1');
    expect(payload.model_settings.model_id).toBe('gpt-4o');

    await waitFor(() => {
      const state = useWorkspaceStore.getState();
      expect(state.sessions.map((s) => s.id)).toContain('new-1');
      expect(state.activeSessionId).toBe('new-1');
    });
    const stored = useWorkspaceStore.getState().sessions.find((s) => s.id === 'new-1');
    expect(stored?.modelConfig.provider).toBe('openai');
    expect(stored?.modelConfig.modelId).toBe('gpt-4o');
  });

  it('deletes a session via api and removes it from store', async () => {
    vi.mocked(api.listSessions)
      .mockResolvedValueOnce([{ id: 'b1', title: '会话 一', status: 'idle', created_at: null }] as any)
      .mockResolvedValueOnce([] as any);
    vi.mocked(api.deleteSession).mockResolvedValue({ ok: true } as any);

    render(<SessionSidebar />);
    const item = (await screen.findByText('会话 一')).closest('div');
    fireEvent.click(within(item as HTMLElement).getByLabelText('删除会话 会话 一'));

    await waitFor(() => expect(api.deleteSession).toHaveBeenCalledWith('b1'));
    await waitFor(() => expect(useWorkspaceStore.getState().sessions).toHaveLength(0));
  });
});
