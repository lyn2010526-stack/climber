import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '../../api';
import i18n from '../../i18n';
import { consumeTaskEvents, getGroupTaskSnapshot, listTaskGroups, TaskStreamError, type TaskEvent } from './taskApi';
import { TaskTracePanel } from './TaskTracePanel';

vi.mock('../../api', () => ({ api: { listTasks: vi.fn(), listTraces: vi.fn(), getTask: vi.fn() } }));
vi.mock('./taskApi', async importOriginal => ({ ...await importOriginal<typeof import('./taskApi')>(), consumeTaskEvents: vi.fn(), listTaskGroups: vi.fn(), getGroupTaskSnapshot: vi.fn() }));
beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('zh-CN');
  vi.mocked(listTaskGroups).mockResolvedValue([]);
  vi.mocked(consumeTaskEvents).mockImplementation(() => new Promise(() => {}));
});
afterEach(() => { vi.useRealTimers(); });
const task = { task_id: 't', objective: 'live task', status: 'running', progress: 0, total_steps: 2 };

it('loads real task details only on inspection and preserves reported zero and structured results', async () => {
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(api.getTask).mockResolvedValue({ ...task, result: { count: 0, output: 'actual output' }, error: 'actual error' });
  render(<TaskTracePanel kind="tasks" />);
  const summary = (await screen.findByText('live task')).closest('summary')!;
  expect(api.getTask).not.toHaveBeenCalled();
  fireEvent.click(summary);
  await screen.findByText(/actual output/);
  expect(api.getTask).toHaveBeenCalledWith('t');
  expect(screen.getByText(/actual output/)).toHaveTextContent('"count": 0');
  expect(screen.getByText('actual error')).toBeInTheDocument();
  expect(summary.closest('details')).toHaveAttribute('open');
});

it('keeps missing fields unreported and retries failed detail requests', async () => {
  vi.mocked(api.listTasks).mockResolvedValue([{ ...task, objective: '' }]);
  vi.mocked(api.getTask).mockRejectedValueOnce(new Error('detail offline')).mockResolvedValueOnce({ ...task, objective: '' });
  render(<TaskTracePanel kind="tasks" />);
  fireEvent.click((await screen.findByText('t')).closest('summary')!);
  expect(await screen.findByRole('alert')).toHaveTextContent('detail offline');
  fireEvent.click(screen.getByRole('button', { name: '重试详情' }));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect(screen.getAllByText('未上报')).toHaveLength(3);
});

it('ignores an outstanding detail response after its task disappears', async () => {
  vi.useFakeTimers();
  let finish!: (detail: Awaited<ReturnType<typeof api.getTask>>) => void;
  vi.mocked(api.listTasks).mockResolvedValueOnce([task]).mockResolvedValue([]);
  vi.mocked(api.getTask).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  await act(async () => { fireEvent.click(screen.getByText('live task').closest('summary')!); });
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  await act(async () => { finish({ ...task, result: { output: 'stale result' } }); });
  expect(screen.queryByText(/stale result/)).toBeNull();
  expect(screen.getByText('后端暂无记录')).toBeInTheDocument();
});

it('inspects group snapshot fields without inventing a goal from its display name', async () => {
  vi.mocked(api.listTraces).mockResolvedValue([]);
  vi.mocked(listTaskGroups).mockResolvedValue([{ id: 'g', name: 'group' }]);
  vi.mocked(getGroupTaskSnapshot).mockResolvedValue({ group_id: 'g', history_scope: 'process_recent', task_tree: { task_id: 'root', nodes: [
    { node_id: 'root', parent_id: null, task_name: 'display name', status: 'completed', elapsed_ms: 0, metadata: { result: { value: 0 }, error: 'reported error' } } as Parameters<typeof import('./taskApi').buildGroupTaskForest>[0][number],
  ] } });
  render(<TaskTracePanel kind="traces" />);
  await screen.findByRole('option', { name: 'group' });
  fireEvent.change(screen.getByLabelText('选择群组'), { target: { value: 'g' } });
  const summary = await screen.findByText(/display name/);
  expect(summary).toHaveTextContent('0ms');
  expect(summary.closest('details')).not.toHaveAttribute('open');
  fireEvent.click(summary);
  expect(summary.closest('details')).toHaveAttribute('open');
  expect(within(summary.closest('details')!).getByText('未上报')).toBeInTheDocument();
  expect(screen.getByText(/"value": 0/)).toBeInTheDocument();
  expect(screen.getByText('reported error')).toBeInTheDocument();
});

it('moves lanes from real events, shows failure and aborts on session switch and unmount', async () => {
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  const { rerender, unmount } = render(<TaskTracePanel kind="tasks" sessionId="a" />);
  await screen.findByText('live task');
  const [, signal, consume] = vi.mocked(consumeTaskEvents).mock.calls[0];
  const event: TaskEvent = { type: 'task_update', task_id: 't', protocol_version: 1, epoch: 'a', sequence: 2, data: { status: 'failed', error: 'real failure' } };
  act(() => consume({ ...event, type: 'snapshot', sequence: 1, data: task }));
  act(() => consume(event));
  expect(within(screen.getByRole('region', { name: '已完成' })).getByText('live task')).toBeInTheDocument();
  expect(screen.getByText('real failure')).toBeInTheDocument();
  act(() => consume({ ...event, sequence: 1, data: { status: 'running' } }));
  expect(within(screen.getByRole('region', { name: '已完成' })).getByText('live task')).toBeInTheDocument();
  rerender(<TaskTracePanel kind="tasks" sessionId="b" />);
  expect(signal.aborted).toBe(true);
  await waitFor(() => expect(consumeTaskEvents).toHaveBeenCalledTimes(2));
  unmount();
  expect(vi.mocked(consumeTaskEvents).mock.calls[1][1].aborted).toBe(true);
});

it('reports stream failure and reconnects through retry with a fresh snapshot', async () => {
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(consumeTaskEvents).mockRejectedValueOnce(new Error('stream offline')).mockImplementationOnce(async (_id, _signal, consume) => {
    consume({ type: 'snapshot', task_id: 't', protocol_version: 1, epoch: 'new', sequence: 1, data: { ...task, status: 'completed' } });
  });
  render(<TaskTracePanel kind="tasks" />);
  expect(await screen.findByRole('alert')).toHaveTextContent('stream offline');
  fireEvent.click(screen.getByText('重试'));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect(within(screen.getByRole('region', { name: '已完成' })).getByText('live task')).toBeInTheDocument();
});

it('selects an explicit account group, renders real parent links and keeps session traces isolated', async () => {
  vi.mocked(api.listTraces).mockResolvedValue([
    { id: 'a', session_id: 'a', name: 'my trace', status: 'success', duration_ms: 4, spans: [] },
    { id: 'b', session_id: 'b', name: 'other trace', status: 'success', duration_ms: 8, spans: [] },
  ]);
  vi.mocked(listTaskGroups).mockResolvedValue([{ id: 'g', name: 'real group' }]);
  vi.mocked(getGroupTaskSnapshot).mockResolvedValue({ group_id: 'g', history_scope: 'process_recent', task_tree: { task_id: 'root-task', nodes: [
    { node_id: 'root', parent_id: null, task_name: 'parent work', status: 'running', elapsed_ms: 20 },
    { node_id: 'child', parent_id: 'root', task_name: 'child work', status: 'failed', elapsed_ms: 10 },
  ] } });
  render(<TaskTracePanel kind="traces" sessionId="a" />);
  await screen.findByText(/my trace/);
  expect(screen.queryByText(/other trace/)).toBeNull();
  await screen.findByRole('option', { name: 'real group' });
  expect(getGroupTaskSnapshot).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('选择群组'), { target: { value: 'g' } });
  const parent = await screen.findByText(/parent work/);
  const child = screen.getByText(/child work/);
  expect(parent.closest('li')).toContainElement(child);
  expect(child.closest('details')).toHaveClass('text-[var(--color-error)]');
  expect(getGroupTaskSnapshot).toHaveBeenCalledWith('g', expect.any(AbortSignal));
});

it('preserves a newer live update when an older discovery request finishes', async () => {
  let finish!: (rows: typeof task[]) => void;
  vi.mocked(api.listTasks).mockResolvedValueOnce([task]).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  vi.useFakeTimers();
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  expect(screen.getByText('live task')).toBeInTheDocument();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  const consume = vi.mocked(consumeTaskEvents).mock.calls[0][2];
  act(() => consume({ type: 'snapshot', task_id: 't', protocol_version: 1, epoch: 'a', sequence: 2, data: task }));
  act(() => consume({ type: 'task_update', task_id: 't', protocol_version: 1, epoch: 'a', sequence: 3, data: { status: 'completed' } }));
  await act(async () => { finish([task]); });
  expect(within(screen.getByRole('region', { name: '已完成' })).getByText('live task')).toBeInTheDocument();
  expect(consumeTaskEvents).toHaveBeenCalledTimes(1);
});

it('bounds disconnect retries even when every connection receives a snapshot before EOF', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(consumeTaskEvents).mockImplementation(async (_id, _signal, consume) => {
    consume({ type: 'snapshot', task_id: 't', protocol_version: 1, epoch: 'a', sequence: 1, data: task });
  });
  const { unmount } = await act(async () => render(<TaskTracePanel kind="tasks" />));
  expect(consumeTaskEvents).toHaveBeenCalledTimes(1);
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(2);
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(3);
  await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(4);
  expect(screen.getByRole('alert')).toHaveTextContent('自动重连已停止');
  await act(async () => { await vi.advanceTimersByTimeAsync(120000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(4);
  unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it('respects 429 Retry-After and cancels pending backoff on unmount', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(consumeTaskEvents).mockRejectedValue(new TaskStreamError('HTTP 429', true, 30000));
  let unmount!: () => void;
  await act(async () => { ({ unmount } = render(<TaskTracePanel kind="tasks" />)); });
  expect(screen.getByRole('alert')).toHaveTextContent('30 秒');
  await act(async () => { await vi.advanceTimersByTimeAsync(29999); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(1);
  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(2);
  unmount();
  await act(async () => { await vi.advanceTimersByTimeAsync(120000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(2);
  expect(vi.getTimerCount()).toBe(0);
});

it('stops automatic retries for permission errors and allows an explicit retry', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(consumeTaskEvents).mockRejectedValue(new TaskStreamError('HTTP 403', false));
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(1);
  await act(async () => { fireEvent.click(screen.getByText('重试')); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(2);
});

it('requires a fresh connection snapshot, ignores old frames, and preserves SSE state across later lists', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  const consume = vi.mocked(consumeTaskEvents).mock.calls[0][2];
  const frame: TaskEvent = { type: 'task_update', task_id: 't', epoch: 'a', sequence: 10, protocol_version: 1, data: { progress: 2 } };
  act(() => consume(frame));
  expect(screen.getByText('running · 0/2')).toBeInTheDocument();
  act(() => consume({ ...frame, type: 'snapshot', data: { ...task, progress: 1 } }));
  act(() => consume({ ...frame, sequence: 9 }));
  expect(() => consume({ ...frame, epoch: 'old', sequence: 100 })).toThrow('进程标识变化');
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.getByText('running · 1/2')).toBeInTheDocument();
});

it('stops rather than retrying earlier than an excessive server Retry-After', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(consumeTaskEvents).mockRejectedValue(new TaskStreamError('HTTP 429', true, 300000));
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  await act(async () => { await vi.advanceTimersByTimeAsync(180000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('alert')).toHaveTextContent('自动重连已停止');
});

it('clears disconnected task errors when the task disappears from discovery', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValueOnce([task]).mockResolvedValue([]);
  vi.mocked(consumeTaskEvents).mockRejectedValue(new TaskStreamError('HTTP 403', false));
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  expect(screen.getByRole('alert')).toHaveTextContent('HTTP 403');
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.getByText('后端暂无记录')).toBeInTheDocument();
});

it('empty discovery aborts subscriptions and clears errors, then starts a fresh task subscription on reappearance', async () => {
  vi.useFakeTimers();
  vi.mocked(api.listTasks).mockResolvedValueOnce([task]).mockResolvedValueOnce([]).mockResolvedValueOnce([task]);
  await act(async () => { render(<TaskTracePanel kind="tasks" />); });
  const [, signal, consume] = vi.mocked(consumeTaskEvents).mock.calls[0];
  act(() => consume({ type: 'snapshot', task_id: 't', epoch: 'a', sequence: 10, protocol_version: 1, data: { ...task, status: 'paused' } }));
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(signal.aborted).toBe(true);
  expect(screen.getByText('后端暂无记录')).toBeInTheDocument();
  act(() => consume({ type: 'snapshot', task_id: 't', epoch: 'old', sequence: 100, protocol_version: 1, data: task }));
  expect(screen.queryByText('live task')).toBeNull();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(consumeTaskEvents).toHaveBeenCalledTimes(2);
});

it('keeps truly empty tasks empty without a stream or a fabricated success indicator', async () => {
  vi.mocked(api.listTasks).mockResolvedValue([]);
  render(<TaskTracePanel kind="tasks" />);
  await screen.findByText('后端暂无记录');
  expect(consumeTaskEvents).not.toHaveBeenCalled();
  expect(screen.queryByText(/实时.*成功|已连接/)).toBeNull();
});

it('ignores the old group response and resets explicit group selection on session change', async () => {
  let finish!: (snapshot: Awaited<ReturnType<typeof getGroupTaskSnapshot>>) => void;
  vi.mocked(api.listTraces).mockResolvedValue([]);
  vi.mocked(listTaskGroups).mockResolvedValue([{ id: 'old', name: 'old group' }, { id: 'new', name: 'new group' }]);
  vi.mocked(getGroupTaskSnapshot).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce({
    group_id: 'new', history_scope: 'process_recent', task_tree: { task_id: '', nodes: [{ node_id: 'new', parent_id: null, task_name: 'new work', status: 'running', elapsed_ms: 1 }] },
  });
  const { rerender } = render(<TaskTracePanel kind="traces" sessionId="a" />);
  await screen.findByRole('option', { name: 'old group' });
  fireEvent.change(screen.getByLabelText('选择群组'), { target: { value: 'old' } });
  await waitFor(() => expect(getGroupTaskSnapshot).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText('选择群组'), { target: { value: 'new' } });
  await screen.findByText(/new work/);
  expect(vi.mocked(getGroupTaskSnapshot).mock.calls[0][1].aborted).toBe(true);
  await act(async () => { finish({ group_id: 'old', history_scope: 'process_recent', task_tree: { task_id: '', nodes: [{ node_id: 'old', parent_id: null, task_name: 'stale work', status: 'running', elapsed_ms: 1 }] } }); });
  expect(screen.queryByText(/stale work/)).toBeNull();
  rerender(<TaskTracePanel kind="traces" sessionId="b" />);
  expect(screen.getByLabelText('选择群组')).toHaveValue('');
  expect(screen.queryByText(/new work/)).toBeNull();
});

it('reports group snapshot failures and retries the selected group', async () => {
  vi.mocked(api.listTraces).mockResolvedValue([]);
  vi.mocked(listTaskGroups).mockResolvedValue([{ id: 'g', name: 'group' }]);
  vi.mocked(getGroupTaskSnapshot).mockRejectedValueOnce(new Error('snapshot offline')).mockResolvedValueOnce({ group_id: 'g', task_tree: { task_id: '', nodes: [] }, history_scope: 'process_recent' });
  render(<TaskTracePanel kind="traces" />);
  await screen.findByRole('option', { name: 'group' });
  fireEvent.change(screen.getByLabelText('选择群组'), { target: { value: 'g' } });
  expect(await screen.findByRole('alert')).toHaveTextContent('snapshot offline');
  fireEvent.click(screen.getByText('重试群组'));
  await screen.findByText('当前进程暂无群组任务树');
  expect(screen.queryByRole('alert')).toBeNull();
});
