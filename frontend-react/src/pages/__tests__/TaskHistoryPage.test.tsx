import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskHistoryPage } from '../TaskHistoryPage';

const apiMocks = vi.hoisted(() => ({
  listTasks: vi.fn(),
  getTask: vi.fn(),
}));

vi.mock('../../api', () => ({ api: apiMocks }));

describe('TaskHistoryPage loading errors', () => {
  beforeEach(() => {
    Object.values(apiMocks).forEach(mock => mock.mockReset());
  });

  it('shows a retryable error instead of an empty history when loading fails', async () => {
    const user = userEvent.setup();
    apiMocks.listTasks
      .mockRejectedValueOnce(new Error('Service unavailable'))
      .mockResolvedValueOnce([]);

    render(<TaskHistoryPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('加载任务历史失败');
    expect(screen.queryByText('暂无任务记录')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试加载任务历史' }));

    expect(await screen.findByText('暂无任务记录')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(apiMocks.listTasks).toHaveBeenCalledTimes(2);
  });

  it('opens a task from the keyboard-accessible history item', async () => {
    const user = userEvent.setup();
    const task = {
      id: 'task-12345678',
      description: '键盘打开任务',
      status: 'completed',
      created_at: '2026-08-27T00:00:00Z',
    };
    apiMocks.listTasks.mockResolvedValue([task]);
    apiMocks.getTask.mockResolvedValue(task);

    render(<TaskHistoryPage />);

    const taskItem = await screen.findByRole('button', { name: /键盘打开任务/ });
    taskItem.focus();
    await user.keyboard('{Enter}');

    expect(await screen.findByText('任务详情')).toBeInTheDocument();
    expect(apiMocks.getTask).toHaveBeenCalledWith(task.id);
  });
});
