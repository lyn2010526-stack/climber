import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskHistoryPage } from '../TaskHistoryPage';
import TaskMonitorPage from '../TaskMonitorPage';
import { ReasoningHistoryPage } from '../ReasoningHistoryPage';
import TracesPage from '../TracesPage';
import { ReasoningPage } from '../ReasoningPage';
import { api } from '../../api';
import i18n from '../../i18n/config';

vi.mock('../../api', () => ({ api: {
  listTasks: vi.fn(), getTask: vi.fn(), createTask: vi.fn(), stopTask: vi.fn(), listReasoningHistory: vi.fn(),
} }));
vi.mock('../../components/tracing/TraceViewer', () => ({ default: () => <div>trace-controls</div> }));
vi.mock('../../components/workspace/ReasoningPanel', () => ({ ReasoningPanel: () => <div>reasoning-controls</div> }));

const task = { task_id: 'task-1', objective: 'Inspect logs', status: 'running', progress: 1, total_steps: 3, created_at: '2026-09-26T08:00:00Z' };

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
  vi.resetAllMocks();
  vi.mocked(api.listTasks).mockResolvedValue([task]);
  vi.mocked(api.getTask).mockResolvedValue(task);
  vi.mocked(api.listReasoningHistory).mockResolvedValue([]);
});

describe('task 14 compact logs', () => {
  it('filters history and opens the original task detail API', async () => {
    render(<TaskHistoryPage />);
    const table = await screen.findByRole('table');
    expect(within(table).getByText('Inspect logs')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'failed' } });
    expect(screen.queryByText('Inspect logs')).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '' } });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'task-1' } });
    fireEvent.click(screen.getByRole('button', { name: '打开: Inspect logs' }));
    await screen.findByText('任务详情');
    expect(api.getTask).toHaveBeenCalledWith('task-1');
  });

  it('retries a failed history request without showing an empty success state', async () => {
    vi.mocked(api.listTasks).mockRejectedValueOnce(new Error('offline'));
    render(<TaskHistoryPage />);
    await screen.findByRole('alert');
    expect(screen.queryByText('暂无数据')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    await screen.findByText('Inspect logs');
    expect(api.listTasks).toHaveBeenCalledTimes(2);
  });

  it('preserves reasoning duration, zero confidence and nullable trace IDs', async () => {
    vi.mocked(api.listReasoningHistory).mockResolvedValue([{ trace_id: null, task: 'Compare paths', mode: 'tree', candidates: 2, best_confidence: 0, coverage_score: 0, duration_ms: 1250, created_at: null }]);
    render(<ReasoningHistoryPage />);
    await screen.findByText('Compare paths');
    expect(screen.getByText('1.3s')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '打开: Compare paths' }));
    expect(screen.getByText('覆盖率')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '返回' }));
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('refreshes task detail after cancelling with the same API contract', async () => {
    vi.mocked(api.stopTask).mockResolvedValue({ cancelled: true, task_id: 'task-1' });
    render(<TaskMonitorPage />);
    const cancel = await screen.findByRole('button', { name: '取消' });
    vi.mocked(api.getTask).mockResolvedValue({ ...task, status: 'cancelled' });
    fireEvent.click(cancel);
    await waitFor(() => expect(api.stopTask).toHaveBeenCalledWith('task-1'));
    await waitFor(() => expect(screen.queryByRole('button', { name: '取消' })).not.toBeInTheDocument());
    expect(api.getTask).toHaveBeenCalledTimes(2);
  });

  it('ignores a stale task detail response after switching selection', async () => {
    vi.mocked(api.listTasks).mockResolvedValue([task, { ...task, task_id: 'task-2', objective: 'Second task' }]);
    let resolveFirst!: (value: typeof task) => void;
    vi.mocked(api.getTask).mockImplementation(id => id === 'task-1'
      ? new Promise(resolve => { resolveFirst = resolve; })
      : Promise.resolve({ ...task, task_id: 'task-2', objective: 'Second task' }));
    render(<TaskMonitorPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Second task/ }));
    await screen.findByRole('heading', { name: 'Second task' });
    await act(async () => resolveFirst(task));
    expect(screen.getByRole('heading', { name: 'Second task' })).toBeInTheDocument();
  });

  it('keeps trace and reasoning controls mounted inside translated page shells', () => {
    const view = render(<TracesPage />);
    expect(screen.getByRole('heading', { name: '链路追踪' })).toBeInTheDocument();
    expect(screen.getByText('trace-controls')).toBeInTheDocument();
    view.unmount();
    render(<ReasoningPage />);
    expect(screen.getByRole('heading', { name: '推理' })).toBeInTheDocument();
    expect(screen.getByText('reasoning-controls')).toBeInTheDocument();
  });
});
