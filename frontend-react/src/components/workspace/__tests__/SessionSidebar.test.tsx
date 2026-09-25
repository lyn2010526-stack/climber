import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen, waitFor, fireEvent, within } from '@testing-library/react';
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

let currentOwner = 'owner-a';
let discoveryStatus = 200;

afterEach(() => vi.unstubAllGlobals());

beforeEach(() => {
  vi.clearAllMocks();
  currentOwner = 'owner-a';
  discoveryStatus = 200;
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/v1/auth/me') return Response.json({ id: currentOwner });
    if (url === '/api/v1/api-keys') return Response.json([
      { id: 'key-a', name: 'Saved key', provider: 'openai', is_active: true },
    ]);
    if (url.startsWith('/api/v1/models/discover?')) return Response.json({
      credential_id: 'key-a', provider: 'openai', source: 'provider_api', status: 'ok',
      models: [{ provider: 'openai', model_id: 'discovered-model', label: 'Provider model' }],
    }, { status: discoveryStatus });
    throw new Error(`Unexpected request: ${url}`);
  }));
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
  vi.mocked(api.listAgents).mockResolvedValue([
    { id: 'agent-1', name: 'Nova', provider: 'openai', model_id: 'gpt-4o' },
  ] as any);
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

  it('preserves the Agent model by default and sets the created session active', async () => {
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
    expect(payload.model_settings).toBeNull();
    expect(api.listModels).not.toHaveBeenCalled();
    expect(screen.getByRole('combobox', { name: '模型来源' })).toHaveValue('agent');

    await waitFor(() => {
      const state = useWorkspaceStore.getState();
      expect(state.sessions.map((s) => s.id)).toContain('new-1');
      expect(state.activeSessionId).toBe('new-1');
    });
    const stored = useWorkspaceStore.getState().sessions.find((s) => s.id === 'new-1');
    expect(stored?.modelConfig.provider).toBe('openai');
    expect(stored?.modelConfig.modelId).toBe('gpt-4o');
  });

  async function chooseSavedModel() {
    const createButton = screen.getByRole('button', { name: /新建会话/ });
    await waitFor(() => expect(createButton).toBeEnabled());
    fireEvent.change(screen.getByRole('combobox', { name: '模型来源' }), { target: { value: 'credential' } });
    expect(createButton).toBeDisabled();
    await screen.findByRole('option', { name: 'Saved key (openai)' });
    fireEvent.change(screen.getByRole('combobox', { name: '已保存的模型凭据' }), { target: { value: 'key-a' } });
    await screen.findByRole('option', { name: 'Provider model' });
    expect(createButton).toBeDisabled();
    fireEvent.change(screen.getByRole('combobox', { name: '模型', exact: true }), { target: { value: 'discovered-model' } });
    await waitFor(() => expect(createButton).toBeEnabled());
    return createButton;
  }

  it('submits credential_id with the discovered provider and model', async () => {
    vi.mocked(api.createSession).mockResolvedValue({ id: 'chosen', provider: 'openai', model_id: 'discovered-model' } as any);
    render(<SessionSidebar />);
    fireEvent.click(await chooseSavedModel());
    await waitFor(() => expect(api.createSession).toHaveBeenCalledWith({
      title: '会话 1', agent_id: 'agent-1', model_settings: {
        credential_id: 'key-a', provider: 'openai', model_id: 'discovered-model',
      },
    }));
    expect(api.listModels).not.toHaveBeenCalled();
  });

  it('clears the override when returning to the Agent default', async () => {
    vi.mocked(api.createSession).mockResolvedValue({ id: 'default' } as any);
    render(<SessionSidebar />);
    const createButton = await chooseSavedModel();
    fireEvent.change(screen.getByRole('combobox', { name: '模型来源' }), { target: { value: 'agent' } });
    fireEvent.click(createButton);
    await waitFor(() => expect(api.createSession).toHaveBeenCalledWith(expect.objectContaining({ model_settings: null })));
    expect(screen.queryByRole('combobox', { name: '已保存的模型凭据' })).not.toBeInTheDocument();
  });

  it('blocks a stale selection when identity changes immediately before creation', async () => {
    render(<SessionSidebar />);
    const createButton = await chooseSavedModel();
    currentOwner = 'owner-b';
    fireEvent.click(createButton);
    await screen.findByText('当前用户已变更，请重新选择智能体和模型');
    expect(api.createSession).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole('combobox', { name: '模型来源' })).toHaveValue('agent'));
    expect(screen.queryByRole('option', { name: 'Provider model' })).not.toBeInTheDocument();
  });

  it('resets owner-scoped selections when focus detects an account change', async () => {
    render(<SessionSidebar />);
    await chooseSavedModel();
    currentOwner = 'owner-b';
    fireEvent(window, new Event('focus'));
    await waitFor(() => expect(screen.getByRole('combobox', { name: '模型来源' })).toHaveValue('agent'));
    expect(screen.queryByRole('option', { name: 'Provider model' })).not.toBeInTheDocument();
  });

  it('keeps custom-model creation disabled after discovery fails', async () => {
    discoveryStatus = 503;
    render(<SessionSidebar />);
    const createButton = screen.getByRole('button', { name: /新建会话/ });
    await waitFor(() => expect(createButton).toBeEnabled());
    fireEvent.change(screen.getByRole('combobox', { name: '模型来源' }), { target: { value: 'credential' } });
    await screen.findByRole('option', { name: 'Saved key (openai)' });
    fireEvent.change(screen.getByRole('combobox', { name: '已保存的模型凭据' }), { target: { value: 'key-a' } });
    await screen.findByRole('button', { name: '重试模型发现' });
    expect(createButton).toBeDisabled();
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it('blocks creation when current identity cannot be confirmed', async () => {
    vi.mocked(fetch).mockResolvedValue(Response.json({ detail: 'Unauthorized' }, { status: 401 }));
    render(<SessionSidebar />);
    await screen.findByText('无法确认当前用户，请刷新页面重试');
    expect(screen.getByRole('button', { name: /新建会话/ })).toBeDisabled();
    expect(api.createSession).not.toHaveBeenCalled();
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

  it('preserves the session and selection on delete failure, then allows retry', async () => {
    vi.mocked(api.listSessions).mockResolvedValueOnce([
      { id: 'b1', title: '会话 一', status: 'idle', created_at: null },
    ] as any);
    vi.mocked(api.deleteSession).mockRejectedValueOnce(new Error('Server unavailable'));
    render(<SessionSidebar />);
    fireEvent.click(await screen.findByText('会话 一'));
    const sessions = useWorkspaceStore.getState().sessions;
    fireEvent.click(screen.getByLabelText('删除会话 会话 一'));
    await act(async () => {});

    expect(useWorkspaceStore.getState().sessions).toEqual(sessions);
    expect(useWorkspaceStore.getState().activeSessionId).toBe('b1');
    expect(screen.getByRole('button', { name: /会话 一\s*idle/ })).toHaveAttribute('aria-current', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('删除会话失败，请重试');
    expect(api.listSessions).toHaveBeenCalledTimes(1);

    let resolveDelete!: (value: Awaited<ReturnType<typeof api.deleteSession>>) => void;
    vi.mocked(api.deleteSession).mockReturnValueOnce(new Promise(resolve => { resolveDelete = resolve; }));
    fireEvent.click(screen.getByLabelText('删除会话 会话 一'));
    expect(useWorkspaceStore.getState().sessions).toEqual(sessions);
    expect(useWorkspaceStore.getState().activeSessionId).toBe('b1');
    await act(async () => resolveDelete({ ok: true } as any));
    expect(useWorkspaceStore.getState().sessions).toEqual([]);
    expect(useWorkspaceStore.getState().activeSessionId).toBeNull();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(api.listSessions).toHaveBeenCalledTimes(2);
  });
});
