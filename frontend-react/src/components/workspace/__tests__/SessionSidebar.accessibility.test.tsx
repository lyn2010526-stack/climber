import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import zh from '../../../locales/zh-CN.json';
import en from '../../../locales/en.json';
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
  await i18n.init({ lng: 'zh-CN', fallbackLng: 'zh-CN', resources: { 'zh-CN': { translation: zh }, en: { translation: en } } });
  useWorkspaceStore.setState({ sessions: [], sessionsLoaded: true, loadingSessions: false, activeSessionId: null });
  vi.mocked(api.listAgents).mockResolvedValue([{ id: 'agent', name: 'Agent' }]);
  vi.mocked(api.listSessions).mockResolvedValue([]);
});
afterEach(cleanup);

function renderSidebar() {
  return render(<I18nextProvider i18n={i18n}><SessionSidebar /></I18nextProvider>);
}

function seedSessions() {
  useWorkspaceStore.getState().loadSessions([
    { id: 'first', title: 'First session', status: 'idle' },
    { id: 'second', title: 'Second session', status: 'running' },
    { id: 'third', title: null, status: 'paused' },
  ]);
  useWorkspaceStore.getState().setActiveSession('first');
}

describe('SessionSidebar accessibility', () => {
  it('prioritizes real sessions and exposes creation options only on demand', async () => {
    seedSessions();
    const user = userEvent.setup();
    renderSidebar();
    const toggle = screen.getByRole('button', { name: '创建配置' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getAllByRole('heading')).toHaveLength(1);
    expect(screen.getByRole('button', { name: '检查点历史' })).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!)!;
    const agent = within(panel).getByRole('combobox', { name: '选择智能体' });
    agent.focus();
    await user.keyboard('{Escape}');
    expect(toggle).toHaveFocus();
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.keyboard('{Enter}');
    expect(agent).toBeVisible();
  });

  it('returns focus to configuration when deleting the last session with creation unavailable', async () => {
    useWorkspaceStore.getState().loadSessions([{ id: 'last', title: 'Last', status: 'idle' }]);
    vi.mocked(api.listAgents).mockResolvedValue([]);
    vi.mocked(api.deleteSession).mockResolvedValue({});
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole('button', { name: '删除会话 Last' }));
    // The backend has no restore route, so the delete is confirmed before it is
    // sent and cancelling keeps the session.
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '取消' }));
    expect(screen.getByRole('button', { name: 'Last 空闲' })).toBeInTheDocument();
    expect(api.deleteSession).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '删除会话 Last' })).toHaveFocus();

    await user.click(screen.getByRole('button', { name: '删除会话 Last' }));
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Last 空闲' })).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: '创建配置' })).toHaveFocus();
    await user.click(screen.getByRole('button', { name: '添加 · 会话' }));
    expect(screen.getByRole('button', { name: '创建配置' })).toHaveFocus();
  });

  it('exposes a labelled list and moves keyboard focus without changing selection', async () => {
    seedSessions();
    const user = userEvent.setup();
    renderSidebar();
    const list = screen.getByRole('list', { name: '会话' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(3);
    await waitFor(() => expect(screen.getByRole('button', { name: '新建会话' })).toBeEnabled());
    const first = screen.getByRole('button', { name: 'First session 空闲' });
    const second = screen.getByRole('button', { name: 'Second session 运行中' });
    first.focus();
    await user.keyboard('{ArrowDown}');
    expect(second).toHaveFocus();
    expect(first).toHaveAttribute('aria-current', 'true');
    await user.keyboard('{Enter}');
    expect(second).toHaveAttribute('aria-current', 'true');
    expect(first).not.toHaveAttribute('aria-current');
    await user.keyboard('{End}');
    expect(screen.getByRole('button', { name: '未命名会话 已暂停' })).toHaveFocus();
    await user.keyboard('{Home}{ArrowUp}');
    expect(first).toHaveFocus();
  });

  it('crosses between the two row stops with the horizontal keys', async () => {
    seedSessions();
    const user = userEvent.setup();
    renderSidebar();
    const trigger = screen.getByRole('button', { name: 'First session 空闲' });
    const action = screen.getByRole('button', { name: '删除会话 First session' });
    expect(trigger).toHaveAttribute('aria-keyshortcuts', 'ArrowUp ArrowDown Home End ArrowRight');
    trigger.focus();
    await user.keyboard('{ArrowRight}');
    expect(action).toHaveFocus();
    await user.keyboard('{ArrowLeft}');
    expect(trigger).toHaveFocus();
    // Row traversal moves focus only, never the selection.
    await user.keyboard('{ArrowDown}');
    expect(screen.getByRole('button', { name: 'Second session 运行中' })).toHaveFocus();
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
  });

  it('keeps the touch action visible and separate from session activation', async () => {
    seedSessions();
    const user = userEvent.setup();
    vi.mocked(api.deleteSession).mockRejectedValue(new Error('offline'));
    renderSidebar();
    const action = screen.getByRole('button', { name: '删除会话 Second session' });
    expect(action).toHaveClass('h-11', 'w-11');
    expect(action.className).not.toMatch(/opacity-0|hidden/);
    expect(action.closest('button')).toBe(action);
    await user.click(action);
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));
    await waitFor(() => expect(api.deleteSession).toHaveBeenCalledWith('second'));
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
    expect(screen.getByRole('alert')).toHaveTextContent('删除会话失败');
    expect(screen.getByRole('button', { name: 'Second session 运行中' })).toBeInTheDocument();
    // A failed delete hands focus back to the action that asked for it, so the
    // retry is one keypress away rather than a hunt.
    expect(screen.getByRole('button', { name: '删除会话 Second session' })).toHaveFocus();
  });

  it('hands focus to the adjacent session after successful deletion', async () => {
    seedSessions();
    const user = userEvent.setup();
    vi.mocked(api.deleteSession).mockResolvedValue({});
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'second', title: 'Second session', status: 'running' },
      { id: 'third', title: null, status: 'paused' },
    ]);
    renderSidebar();
    await user.click(screen.getByRole('button', { name: '删除会话 First session' }));
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'First session 空闲' })).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Second session 运行中' })).toHaveFocus();
  });

  it('distinguishes loading from empty and provides a keyboard-operable creation shortcut', async () => {
    const user = userEvent.setup();
    useWorkspaceStore.setState({ loadingSessions: true });
    renderSidebar();
    expect(screen.getByRole('status')).toHaveTextContent(zh.common.loading_data);
    expect(screen.queryByText(zh.common.no_data)).not.toBeInTheDocument();
    act(() => useWorkspaceStore.setState({ loadingSessions: false }));
    expect(screen.getByRole('status')).toHaveTextContent(zh.common.no_data);
    const create = screen.getByRole('button', { name: '新建会话' });
    await waitFor(() => expect(create).toBeEnabled());
    await user.click(screen.getByRole('button', { name: '添加 · 会话' }));
    expect(create).toHaveFocus();
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it('links checkpoint disclosure to its panel and translates new list labels', async () => {
    seedSessions();
    const user = userEvent.setup();
    renderSidebar();
    const toggle = screen.getByRole('button', { name: '检查点历史' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(document.getElementById(toggle.getAttribute('aria-controls')!)).toHaveTextContent('暂无检查点');
    await user.click(toggle);
    expect(toggle).not.toHaveAttribute('aria-controls');
    await act(async () => { await i18n.changeLanguage('en'); });
    expect(screen.getByRole('list', { name: en.navigation.sessions })).toBeInTheDocument();
    expect(screen.getByText(en.right_panel.summary.untitled)).toBeInTheDocument();
  });
});
