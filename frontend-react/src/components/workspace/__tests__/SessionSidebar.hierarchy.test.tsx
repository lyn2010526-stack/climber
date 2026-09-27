import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
  vi.mocked(api.listSessions).mockResolvedValue([]);
});
afterEach(() => { vi.restoreAllMocks(); });

function seed(...sessions: Array<{ id: string; title: string; status?: string }>) {
  useWorkspaceStore.getState().loadSessions(
    sessions.map((session, index) => ({
      id: session.id,
      title: session.title,
      status: (session.status ?? 'idle') as 'idle',
      createdAt: index,
    })) as never,
  );
}

function renderSidebar() {
  return render(<I18nextProvider i18n={i18n}><SessionSidebar /></I18nextProvider>);
}

describe('SessionSidebar hierarchy', () => {
  it('gives the session list the scrolling body and keeps creation on one row', () => {
    seed({ id: 'a', title: 'Alpha' }, { id: 'b', title: 'Beta' });
    const { container } = renderSidebar();
    const list = screen.getByRole('list', { name: '会话' });
    const scroller = list.parentElement!;
    expect(scroller).toHaveClass('flex-1', 'overflow-y-auto');
    // The list header carries the only heading in the sidebar.
    expect(screen.getAllByRole('heading')).toHaveLength(1);
    const create = screen.getByRole('button', { name: '新建会话' });
    const config = screen.getByRole('button', { name: '创建配置' });
    expect(create.parentElement).toBe(config.parentElement);
    expect(container.querySelector('.session-sidebar')).toBeInTheDocument();
  });

  it('keeps creation configuration closed until it is asked for', async () => {
    seed({ id: 'a', title: 'Alpha' });
    renderSidebar();
    const toggle = screen.getByRole('button', { name: '创建配置' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).not.toHaveAttribute('aria-controls');
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0);
  });

  it('sinks the checkpoint history under the list and only materialises it on demand', async () => {
    useWorkspaceStore.getState().loadSessions([
      { id: 'a', title: 'Alpha', status: 'idle' },
    ] as never);
    useWorkspaceStore.getState().setActiveSession('a');
    act(() => {
      useWorkspaceStore.setState((state) => ({
        sessions: state.sessions.map(session => session.id === 'a'
          ? { ...session, messages: [{ id: 'm1', role: 'user', content: 'hi', timestamp: 1, type: 'message' }] }
          : session),
      }));
    });
    renderSidebar();
    const toggle = screen.getByRole('button', { name: '检查点历史' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    // The panel is not in the document at all while the list is the body.
    expect(screen.queryByText('暂无检查点')).not.toBeInTheDocument();
    fireEvent.click(toggle);
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!)!;
    expect(within(panel).getByText('message')).toBeInTheDocument();
    // The drawer sits under the list rather than between rows of it.
    const list = screen.getByRole('list', { name: '会话' });
    expect(panel.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
    fireEvent.click(toggle);
    expect(screen.queryByText('暂无检查点')).not.toBeInTheDocument();
    expect(screen.queryByText('message')).not.toBeInTheDocument();
  });

  it('reports every row status in the accessible name', () => {
    seed({ id: 'a', title: 'Alpha', status: 'running' }, { id: 'b', title: 'Beta' });
    renderSidebar();
    expect(screen.getByRole('button', { name: 'Alpha 运行中' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Beta 空闲' })).toBeInTheDocument();
  });

  it('keeps one heading for the list and one for nothing else', async () => {
    seed({ id: 'a', title: 'Alpha' });
    renderSidebar();
    await waitFor(() => expect(screen.getByRole('list', { name: '会话' })).toBeInTheDocument());
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('会话');
  });
});
