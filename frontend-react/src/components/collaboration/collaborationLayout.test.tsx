import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { api } from '../../api';
import { ClusterPage } from '../../pages/ClusterPage';

vi.mock('../../api', () => ({
  api: {
    createTask: vi.fn(),
    getTask: vi.fn(),
    stopTask: vi.fn(),
    listGroups: vi.fn(),
    getGroup: vi.fn(),
    addGroupMember: vi.fn(),
    removeGroupMember: vi.fn(),
    createGroup: vi.fn(),
    listGroupMessages: vi.fn(),
    deleteGroup: vi.fn(),
    updateGroupMember: vi.fn(),
    listClusterNodes: vi.fn(),
    createCluster: vi.fn(),
    deleteClusterNode: vi.fn(),
    openGroupWebSocket: vi.fn(() => new WebSocket('ws://localhost')),
  },
}));

const member = { id: 'm1', agent_id: 'a1', role: 'worker', status: 'active' };
const groups = [
  { id: 'g1', name: 'Group 1', topic: 'roadmap', description: '', member_count: 1, status: 'active' },
];

async function openGroup() {
  render(<ClusterPage />);
  fireEvent.click(await screen.findByRole('button', { name: i18n.t('collaboration.groups.enter') }));
  await screen.findByRole('heading', { name: i18n.t('collaboration.heading_task') });
}

/** Drives the group view without duplicating the page's own navigation wiring. */
async function openViaSidebar() {
  await openGroup();
  return screen.getByRole('complementary', { name: i18n.t('collaboration.aria.sidebar') });
}

/** The sidebar section toggle also carries the "Submit task" title; the real
 *  submit control is the form's type="submit" button. */
function submitButton() {
  return screen.getAllByRole('button', { name: i18n.t('collaboration.task.submit') })
    .find(button => (button as HTMLButtonElement).type === 'submit')
    ?? (() => { throw new Error('task submit button not found'); })();
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listGroups).mockResolvedValue(groups);
  vi.mocked(api.getGroup).mockResolvedValue({ members: [member] });
  vi.mocked(api.listGroupMessages).mockResolvedValue({ messages: [] });
  vi.mocked(api.listClusterNodes).mockResolvedValue([] as any);
});
afterEach(cleanup);

describe('collaboration layout', () => {
  it('keeps members and topics in the sidebar and the task in the workspace', async () => {
    const sidebar = await openViaSidebar();

    const sections = Array.from(sidebar.querySelectorAll('section > div > button'));
    const titles = sections.map(node => node.textContent?.trim() ?? '');

    expect(titles.some(title => title.startsWith(i18n.t('collaboration.sidebar.submit_task')))).toBe(true);
    expect(titles.some(title => title.startsWith(i18n.t('collaboration.sidebar.members')))).toBe(true);
    expect(titles.some(title => title.startsWith(i18n.t('collaboration.sidebar.topic')))).toBe(true);

    // Membership and topic never render as workspace sections.
    expect(sidebar.querySelector('#group-task-heading')).toBeNull();
    expect(screen.getByRole('complementary', { name: i18n.t('collaboration.aria.sidebar') })).toBe(sidebar);
    expect(screen.getByRole('heading', { name: i18n.t('collaboration.heading_task') })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: i18n.t('collaboration.aria.group_discussion') })).toBeInTheDocument();
  });

  it('shows a single task input panel inside the sidebar', async () => {
    const sidebar = await openViaSidebar();

    expect(screen.getAllByLabelText(i18n.t('collaboration.task.objective_label'))).toHaveLength(1);
    expect(sidebar.contains(screen.getByLabelText(i18n.t('collaboration.task.objective_label')))).toBe(true);
    expect(sidebar.contains(submitButton())).toBe(true);
  });

  it('renders the group topic in the sidebar rather than the workspace header', async () => {
    const sidebar = await openViaSidebar();

    expect(sidebar.textContent).toContain('roadmap');
    expect(screen.getByRole('complementary', { name: i18n.t('collaboration.aria.sidebar') })).toBe(sidebar);
  });

  it('keeps the member list in the sidebar with its count from the backend', async () => {
    const sidebar = await openViaSidebar();

    await waitFor(() => expect(sidebar.textContent).toContain('a1'));
    expect(sidebar.textContent).toContain('1');
  });
});

describe('task surface', () => {
  it('submits the supported task contract and renders backend output', async () => {
    vi.mocked(api.createTask).mockResolvedValue({
      task_id: 't1', objective: '', status: 'pending', progress: 0, total_steps: 0,
    });
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 't1', objective: '任务目标内容', status: 'completed', progress: 2, total_steps: 2,
      result: { output: '真实结果' },
    });

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '任务目标内容' } });
    fireEvent.click(submitButton());

    expect(await screen.findByText(/"output": "真实结果"/)).toBeInTheDocument();
    expect(api.createTask).toHaveBeenCalledWith({
      task_type: 'agent_run',
      payload: { group_id: 'g1', objective: '任务目标内容', max_steps: 5 },
    });
  });

  it('has no pause control, no advanced settings and no autocompletion claim', async () => {
    await openViaSidebar();

    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument();
    expect(screen.queryByText('Advanced settings')).not.toBeInTheDocument();
    expect(screen.queryByText(/自动完成/)).not.toBeInTheDocument();
  });

  it('reports Not reported for fields the backend has not sent', async () => {
    // The backend response omits the step counters entirely.
    const withoutCounters = {
      task_id: 't1',
      objective: '目标',
      status: '',
    } as unknown as Awaited<ReturnType<typeof api.getTask>>;
    vi.mocked(api.createTask).mockResolvedValue(withoutCounters);
    vi.mocked(api.getTask).mockResolvedValue(withoutCounters);

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '目标' } });
    fireEvent.click(submitButton());

    const status = await screen.findByRole('status', { name: i18n.t('collaboration.aria.task_status') });
    await waitFor(() => expect(status.textContent).toContain(i18n.t('collaboration.not_reported')));
    expect(status.textContent).toContain(i18n.t('collaboration.steps_progress', { done: i18n.t('collaboration.not_reported'), total: i18n.t('collaboration.not_reported') }));
  });

  it('distinguishes a reported zero from a missing step count', async () => {
    vi.mocked(api.createTask).mockResolvedValue({
      task_id: 't1', objective: '目标', status: 'pending', progress: 0, total_steps: 0,
    });
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 't1', objective: '目标', status: 'pending', progress: 0, total_steps: 0,
    });

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '目标' } });
    fireEvent.click(submitButton());

    const status = await screen.findByRole('status', { name: i18n.t('collaboration.aria.task_status') });
    await waitFor(() => expect(status.textContent).toContain(i18n.t('collaboration.task_status.pending')));
    expect(status.textContent).toContain(i18n.t('collaboration.steps_progress', { done: '0', total: '0' }));
  });

  it('reports unknown backend statuses explicitly', async () => {
    vi.mocked(api.createTask).mockResolvedValue({
      task_id: 't1', objective: '目标', status: 'weird_state', progress: 0, total_steps: 0,
    });
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 't1', objective: '目标', status: 'weird_state', progress: 0, total_steps: 0,
    });

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '目标' } });
    fireEvent.click(submitButton());

    const status = await screen.findByRole('status', { name: i18n.t('collaboration.aria.task_status') });
    await waitFor(() => expect(status.textContent).toContain(i18n.t('collaboration.not_reported')));
  });

  it('retains the draft and shows submission errors', async () => {
    vi.mocked(api.createTask).mockRejectedValue(new Error('提交失败'));

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '保留目标' } });
    fireEvent.click(submitButton());

    expect(await screen.findByRole('alert')).toHaveTextContent('提交失败');
    expect(screen.getByLabelText(i18n.t('collaboration.task.objective_label'))).toHaveValue('保留目标');
  });

  it('cancels through the backend and then reports the confirmed status', async () => {
    const pending = { task_id: 't1', objective: '目标', status: 'pending', progress: 0, total_steps: 5 };
    vi.mocked(api.createTask).mockResolvedValue(pending);
    vi.mocked(api.getTask).mockResolvedValue(pending);
    vi.mocked(api.stopTask).mockResolvedValue({ task_id: 't1', cancelled: true });

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '目标' } });
    fireEvent.click(submitButton());

    const cancel = await screen.findByRole('button', { name: i18n.t('collaboration.cancel.action') });
    vi.mocked(api.getTask).mockResolvedValue({ ...pending, status: 'cancelled' });
    fireEvent.click(cancel);

    expect(await screen.findByText(i18n.t('collaboration.task_status.cancelled'))).toBeInTheDocument();
    expect(api.stopTask).toHaveBeenCalledWith('t1');
  });

  it('surfaces a refused cancellation instead of claiming the task stopped', async () => {
    const pending = { task_id: 't1', objective: '目标', status: 'pending', progress: 0, total_steps: 5 };
    vi.mocked(api.createTask).mockResolvedValue(pending);
    vi.mocked(api.getTask).mockResolvedValue(pending);
    vi.mocked(api.stopTask).mockResolvedValue({ task_id: 't1', cancelled: false });

    await openViaSidebar();
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.task.objective_label')), { target: { value: '目标' } });
    fireEvent.click(submitButton());
    fireEvent.click(await screen.findByRole('button', { name: i18n.t('collaboration.cancel.action') }));

    expect(await screen.findByRole('alert')).toHaveTextContent('任务取消未确认');
    expect(screen.getByRole('button', { name: i18n.t('collaboration.cancel.action') })).toBeInTheDocument();
  });
});

describe('group creation', () => {
  it('sends the template flag to the field the backend reads', async () => {
    vi.mocked(api.createGroup).mockResolvedValue({ id: 'g2' });
    render(<ClusterPage />);
    fireEvent.click(await screen.findByRole('button', { name: i18n.t('collaboration.groups.create') }));
    fireEvent.change(screen.getByLabelText(i18n.t('collaboration.groups.name_label')), { target: { value: '新群组' } });
    fireEvent.click(screen.getByLabelText(new RegExp(i18n.t('collaboration.groups.template_hint').replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))));
    fireEvent.click(screen.getByRole('button', { name: i18n.t('common.create') }));

    await waitFor(() =>
      expect(api.createGroup).toHaveBeenCalledWith({
        name: '新群组',
        topic: '',
        template: 'default',
      }),
    );
    expect(api.createGroup).not.toHaveBeenCalledWith(expect.objectContaining({ description: 'default' }));
  });

  it('labels group status from backend values and reports missing ones', async () => {
    vi.mocked(api.listGroups).mockResolvedValue([
      { id: 'g1', name: 'Group 1', member_count: 3, status: 'active' },
      { id: 'g2', name: 'Group 2', member_count: 0, status: '' },
    ]);
    render(<ClusterPage />);

    const rows = await screen.findAllByRole('heading', { level: 2, name: /^Group \d/ });
    const first = rows[0]!.closest('div')?.parentElement?.textContent ?? '';
    const second = rows[1]!.closest('div')?.parentElement?.textContent ?? '';

    expect(first).toContain('3 members');
    expect(first).toContain('Active');
    expect(second).toContain('0 members');
    expect(second).toContain('Not reported');
  });
});
