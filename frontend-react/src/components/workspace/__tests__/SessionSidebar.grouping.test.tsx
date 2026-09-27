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
const DAY_MS = 24 * 60 * 60 * 1000;

const START_OF_TODAY = new Date().setHours(0, 0, 0, 0);
const TWO_DAYS_AGO = START_OF_TODAY - 2 * DAY_MS;
const TWENTY_DAYS_AGO = START_OF_TODAY - 20 * DAY_MS;

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.init({ lng: 'zh-CN', fallbackLng: 'zh-CN', resources: { 'zh-CN': { translation: zh } } });
  useWorkspaceStore.setState({ sessions: [], sessionsLoaded: true, loadingSessions: false, activeSessionId: null });
  vi.mocked(api.listAgents).mockResolvedValue([{ id: 'agent', name: 'Agent' }]);
  vi.mocked(api.listSessions).mockResolvedValue([]);
  vi.mocked(api.deleteSession).mockResolvedValue({});
});
afterEach(cleanup);

function renderSidebar() {
  return render(<I18nextProvider i18n={i18n}><SessionSidebar /></I18nextProvider>);
}

/** Seeded through the store, so the `created_at` these rows carry is the one the buckets read. */
function seed(...rows: Array<{ id: string; title: string; status?: string; createdAt: number }>) {
  useWorkspaceStore.getState().loadSessions(
    rows.map((row) => ({
      id: row.id,
      title: row.title,
      status: row.status ?? 'idle',
      created_at: new Date(row.createdAt).toISOString(),
    })) as never,
  );
}

function seedThreeBuckets() {
  seed(
    { id: 'today', title: '晨会纪要', createdAt: Date.now() },
    { id: 'week', title: '本周复盘', createdAt: TWO_DAYS_AGO },
    { id: 'old', title: '上个月的方案', createdAt: TWENTY_DAYS_AGO },
  );
}

/**
 * A group header is the one button whose name is the group label followed by
 * its count. Anchoring on that keeps it apart from a session row, whose name
 * is the title followed by its status.
 */
function groupHeader(label: string) {
  return screen.getByRole('button', { name: new RegExp(`^${label}\\d+$`) });
}

/**
 * A session row's name starts with its title. The trailing delete button names
 * itself "删除会话 <title>", so anchoring at the start keeps the two apart.
 */
function sessionRow(title: string) {
  return screen.getByRole('button', { name: new RegExp(`^${title}`) });
}

describe('SessionSidebar grouping', () => {
  it('orders the groups by date and reports a count on each', () => {
    seedThreeBuckets();
    renderSidebar();

    const list = screen.getByRole('list', { name: '会话' });
    const headers = within(list).getAllByRole('button', { expanded: true });
    expect(headers.map((header) => header.textContent)).toEqual(['今天1', '最近 7 天1', '更早1']);
    // The grouped reading order is the order the rows appear in.
    expect(within(list).getAllByRole('listitem').map((row) => row.textContent)).toEqual([
      expect.stringContaining('晨会纪要'),
      expect.stringContaining('本周复盘'),
      expect.stringContaining('上个月的方案'),
    ]);
  });

  it('renders the backend updated_at and keeps an unreported time explicit', async () => {
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'reported', title: '有更新时间', status: 'idle', created_at: new Date().toISOString(), updated_at: '2026-09-26T09:41:00Z' },
      { id: 'missing', title: '无更新时间', status: 'idle', created_at: new Date().toISOString() },
    ] as any);
    useWorkspaceStore.setState({ sessionsLoaded: false });
    renderSidebar();

    await waitFor(() => expect(screen.getByText('有更新时间')).toBeInTheDocument());
    expect(screen.getByTitle(/空闲.*09:41|idle.*09:41/)).toBeInTheDocument();
    expect(screen.getByTitle(/未上报/)).toBeInTheDocument();
  });

  it('renders no header for a bucket the backend reported nothing for', () => {
    // A header standing over zero rows is the shape that made a whole page of
    // sessions unreachable in the reference implementation.
    seed({ id: 'only', title: 'Only row', createdAt: Date.now() });
    renderSidebar();

    const list = screen.getByRole('list', { name: '会话' });
    expect(within(list).getAllByRole('button', { expanded: true })).toHaveLength(1);
    expect(screen.queryByRole('button', { name: /^\u66f4\u65e9\d+$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^\u6700\u8fd1 7 \u5929\d+$/ })).not.toBeInTheDocument();
  });

  it('collapses a group on request and restores it on a second request', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    const header = groupHeader('今天');
    expect(header).toHaveAttribute('aria-expanded', 'true');
    await user.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'false');
    expect(document.getElementById(header.getAttribute('aria-controls')!)).not.toBeVisible();
    // A collapsed group hides its rows rather than taking them out of the DOM,
    // so the check is visibility: the markup stays mounted and unclickable.
    expect(screen.getAllByText('晨会纪要')[0]).not.toBeVisible();
    expect(sessionRow('本周复盘')).toBeInTheDocument();

    await user.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'true');
    expect(sessionRow('晨会纪要')).toBeInTheDocument();
  });

  it('keeps the group headers inside the one scroll viewport the rows scroll in', () => {
    seedThreeBuckets();
    renderSidebar();

    const list = screen.getByRole('list', { name: '会话' });
    const scroller = list.parentElement!;
    expect(scroller).toHaveClass('flex-1', 'overflow-y-auto');
    // The headers live in the same viewport, so a group that grows scrolls
    // with its rows rather than pinning itself against the container.
    expect(within(scroller).getByRole('button', { name: /^\u4eca\u5929\d+$/ })).toBeInTheDocument();
  });

  it('walks the grouped order with the vertical keys and stops at both ends', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    await waitFor(() => expect(screen.getByRole('button', { name: '新建会话' })).toBeEnabled());
    await user.click(sessionRow('晨会纪要'));
    await user.keyboard('{ArrowDown}');
    expect(sessionRow('本周复盘')).toHaveFocus();
    await user.keyboard('{ArrowDown}');
    expect(sessionRow('上个月的方案')).toHaveFocus();
    // The last row has no successor, so the key does not wrap and does not throw.
    await user.keyboard('{ArrowDown}');
    expect(sessionRow('上个月的方案')).toHaveFocus();
    await user.keyboard('{Home}');
    expect(sessionRow('晨会纪要')).toHaveFocus();
    await user.keyboard('{ArrowUp}');
    expect(sessionRow('晨会纪要')).toHaveFocus();
  });

  it('steps over a collapsed group rather than stranding the walk', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    await waitFor(() => expect(screen.getByRole('button', { name: '新建会话' })).toBeEnabled());
    // Collapse the middle group, so its row has nothing to focus.
    await user.click(groupHeader('最近 7 天'));
    // The collapsed row is still mounted, so clicking it would press a control
    // the reader cannot see. The walk is asserted on the two reachable rows.
    await user.click(sessionRow('晨会纪要'));
    await user.keyboard('{ArrowDown}');
    expect(sessionRow('上个月的方案')).toHaveFocus();
    await user.keyboard('{ArrowUp}');
    expect(sessionRow('晨会纪要')).toHaveFocus();
  });
});

describe('SessionSidebar filtering', () => {
  it('keeps the filter behind a disclosure and reveals it on request', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: '筛选会话' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('searchbox', { name: '搜索会话标题' })).toBeInTheDocument();
  });

  it('narrows the list to the titles that match and restores it on clearing', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    await user.click(screen.getByRole('button', { name: '筛选会话' }));
    await user.type(screen.getByRole('searchbox', { name: '搜索会话标题' }), '复盘');

    const list = screen.getByRole('list', { name: '会话' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);
    expect(within(list).getByText('本周复盘')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '清除筛选' }));
    expect(within(screen.getByRole('list', { name: '会话' })).getAllByRole('listitem')).toHaveLength(3);
  });

  it('offers only the statuses the loaded list actually carries', async () => {
    const user = userEvent.setup();
    seed(
      { id: 'a', title: 'A', status: 'idle', createdAt: Date.now() },
      { id: 'b', title: 'B', status: 'running', createdAt: Date.now() },
    );
    renderSidebar();

    await user.click(screen.getByRole('button', { name: '筛选会话' }));
    const select = screen.getByRole('combobox', { name: '按状态筛选' });
    // The option values are the statuses `SessionOut` reports, so the control
    // can never be read as offering a state the list does not contain.
    expect(within(select).getAllByRole('option').map((option) => (option as HTMLOptionElement).value))
      .toEqual(['all', 'idle', 'running']);
    // "completed" is a real status the backend may report, but this list holds
    // no such row, so it is not offered.
    expect(within(select).queryByRole('option', { name: /completed/ })).not.toBeInTheDocument();
  });

  it('states the empty result and offers a way out when the filter excludes everything', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    await user.click(screen.getByRole('button', { name: '筛选会话' }));
    await user.type(screen.getByRole('searchbox', { name: '搜索会话标题' }), 'zzz-no-such-session');

    // A filter that excludes everything is a page with no rows, not a missing
    // page: the list region still stands and creation is still reachable.
    const list = screen.getByRole('list', { name: '会话' });
    expect(list).toBeInTheDocument();
    expect(within(list).queryAllByRole('listitem')).toHaveLength(0);
    expect(screen.getByRole('status')).toHaveTextContent('没有匹配当前筛选的会话');
    expect(screen.getByRole('status')).toHaveTextContent('共 3 个会话被当前筛选排除');

    const create = screen.getByRole('button', { name: '新建会话' });
    await waitFor(() => expect(create).toBeEnabled());
    await user.click(screen.getByRole('button', { name: '添加 · 会话' }));
    expect(create).toHaveFocus();

    // The way out of the empty page restores every row. It sits inside the empty
    // state itself, so the reader never has to hunt for it back at the filter.
    const emptyState = screen.getByRole('status');
    await user.click(within(emptyState).getByRole('button', { name: '清除筛选' }));
    expect(within(screen.getByRole('list', { name: '会话' })).getAllByRole('listitem')).toHaveLength(3);
  });

  it('does not claim the list is empty when a filter has not excluded anything', () => {
    renderSidebar();
    // The "no data" state belongs to an empty list; with a filter closed and no
    // rows reported, that is the one true statement about the page.
    expect(screen.getByRole('status')).toHaveTextContent(zh.common.no_data);
  });
});

describe('SessionSidebar delete confirmation', () => {
  it('states that the delete cannot be undone before anything is sent', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    vi.mocked(api.deleteSession).mockResolvedValue({});
    renderSidebar();

    await user.click(screen.getByRole('button', { name: '删除会话 晨会纪要' }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('晨会纪要');
    // The backend has no restore, archive or soft-delete route, so the dialog
    // says the operation is permanent rather than promising an undo.
    expect(dialog).toHaveTextContent('将被永久删除');
    expect(dialog).toHaveTextContent('后端没有恢复接口，此操作无法撤销');
    expect(api.deleteSession).not.toHaveBeenCalled();
  });

  it('keeps the session and returns focus to the action when the confirmation is cancelled', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    const action = screen.getByRole('button', { name: '删除会话 晨会纪要' });
    await user.click(action);
    await user.click(screen.getByRole('button', { name: '取消' }));

    expect(api.deleteSession).not.toHaveBeenCalled();
    expect(sessionRow('晨会纪要')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '删除会话 晨会纪要' })).toHaveFocus();
  });

  it('closes on Escape without sending a request', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    renderSidebar();

    await user.click(screen.getByRole('button', { name: '删除会话 晨会纪要' }));
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(api.deleteSession).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '删除会话 晨会纪要' })).toHaveFocus();
  });

  it('sends the delete only on confirmation and hands focus to the neighbouring row', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    // The backend answers the refetch that follows the delete with the two rows
    // that are left, so the handover is checked against the list as it really
    // lands rather than against the pre-delete snapshot.
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'week', title: '本周复盘', status: 'idle', created_at: new Date(TWO_DAYS_AGO).toISOString() },
      { id: 'old', title: '上个月的方案', status: 'idle', created_at: new Date(TWENTY_DAYS_AGO).toISOString() },
    ]);
    renderSidebar();

    const action = screen.getByRole('button', { name: '删除会话 晨会纪要' });
    action.focus();
    await user.click(action);
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));

    await waitFor(() => expect(api.deleteSession).toHaveBeenCalledWith('today'));
    // The successor is read off the visible order, so it is a row that is
    // really on screen, and the deletion does not leave focus on the document.
    // The refetch that follows the delete still carries it.
    await waitFor(() => expect(sessionRow('本周复盘')).toHaveFocus());
    expect(document.activeElement).not.toBe(document.body);
  });

  it('hands focus to the group header when the neighbouring row sits in a collapsed group', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    // The row that is left in the collapsed group after the delete, so the
    // handover is checked against the list that really lands: the group, its
    // header and its hidden row are all still there after the refetch.
    vi.mocked(api.listSessions).mockResolvedValue([
      { id: 'week', title: '本周复盘', status: 'idle', created_at: new Date(TWO_DAYS_AGO).toISOString() },
      { id: 'old', title: '上个月的方案', status: 'idle', created_at: new Date(TWENTY_DAYS_AGO).toISOString() },
    ]);
    renderSidebar();

    // Collapse the group the neighbour lives in. Its row stays mounted but
    // hidden, so it cannot hold focus and the handover has to go to the header.
    await user.click(groupHeader('最近 7 天'));
    const action = screen.getByRole('button', { name: '删除会话 晨会纪要' });
    action.focus();
    await user.click(action);
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));

    await waitFor(() => expect(api.deleteSession).toHaveBeenCalledWith('today'));
    // The row is unmounted, so focus falls through to the header of the group
    // the neighbour belongs to rather than to the document body.
    await waitFor(() => expect(groupHeader('最近 7 天')).toHaveFocus());
    expect(document.activeElement).not.toBe(document.body);
  });

  it('reports a failed delete and leaves the row focusable for a retry', async () => {
    const user = userEvent.setup();
    seedThreeBuckets();
    vi.mocked(api.deleteSession).mockRejectedValue(new Error('offline'));
    renderSidebar();

    const action = screen.getByRole('button', { name: '删除会话 晨会纪要' });
    action.focus();
    await user.click(action);
    await user.click(screen.getByRole('button', { name: '删除', exact: true }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('删除会话失败'));
    expect(screen.getByRole('button', { name: '删除会话 晨会纪要' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '删除会话 晨会纪要' })).toHaveFocus();
  });
});
