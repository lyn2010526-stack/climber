import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import zh from '../../../locales/zh-CN.json';
import { useWorkspaceStore } from '../../../store/workspace';
import { api } from '../../../api';
import { SessionSidebar } from '../SessionSidebar';

vi.mock('../../../api', () => ({ api: {
  listSessions: vi.fn(), listAgents: vi.fn(), deleteSession: vi.fn(), createSession: vi.fn(),
} }));
vi.mock('../../../lib/api-client', () => ({ apiClient: { get: vi.fn(async () => ({ id: 'owner' })) } }));

const i18n = createInstance();

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.init({ lng: 'zh-CN', fallbackLng: 'zh-CN', resources: { 'zh-CN': { translation: zh } } });
  useWorkspaceStore.setState({ sessions: [], sessionsLoaded: true, loadingSessions: false, activeSessionId: null });
  vi.mocked(api.listAgents).mockResolvedValue([{ id: 'agent', name: 'Agent' }]);
  // The backend holds three sessions; the list is emptied by the view, which is
  // what a filter that matches nothing leaves behind.
  vi.mocked(api.listSessions).mockResolvedValue([
    { id: 'first', title: 'First session', status: 'idle' },
    { id: 'second', title: 'Second session', status: 'running' },
    { id: 'third', title: 'Third session', status: 'paused' },
  ]);
  useWorkspaceStore.setState({
    loadSessions: () => useWorkspaceStore.setState({ sessions: [], sessionsLoaded: true, loadingSessions: false }),
  });
});
afterEach(cleanup);

function renderSidebar() {
  return render(<I18nextProvider i18n={i18n}><SessionSidebar /></I18nextProvider>);
}

describe('SessionSidebar list reachability', () => {
  it('reaches creation when a filter excludes every session', async () => {
    const user = userEvent.setup();
    renderSidebar();

    // The list itself is still a labelled region with rows of its own, so a
    // zero-row page is an empty page rather than a missing one.
    const list = screen.getByRole('list', { name: zh.navigation.sessions });
    expect(list).toBeInTheDocument();
    expect(within(list).queryAllByRole('listitem')).toHaveLength(0);

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(zh.common.no_data));
    const create = screen.getByRole('button', { name: '新建会话' });
    await waitFor(() => expect(create).toBeEnabled());

    // Creation stays reachable from the empty state and from the header, and
    // focus lands on the control that can actually act.
    await user.click(screen.getByRole('button', { name: `${zh.common.add} · ${zh.navigation.sessions}` }));
    expect(create).toHaveFocus();
    create.blur();
    create.focus();
    expect(create).toHaveFocus();
  });

  it('hands the empty state over to configuration when creation is unavailable', async () => {
    const user = userEvent.setup();
    vi.mocked(api.listAgents).mockResolvedValue([]);
    renderSidebar();

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(zh.common.no_data));
    const create = screen.getByRole('button', { name: '新建会话' });
    await waitFor(() => expect(create).toBeDisabled());
    expect(create).toHaveAttribute('disabled');

    // A disabled primary control cannot hold focus, so the empty state hands it
    // to the control that can open creation instead.
    await user.click(screen.getByRole('button', { name: `${zh.common.add} · ${zh.navigation.sessions}` }));
    expect(screen.getByRole('button', { name: '创建配置' })).toHaveFocus();
  });
});
