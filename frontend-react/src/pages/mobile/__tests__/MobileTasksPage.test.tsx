import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';

const { listTasks } = vi.hoisted(() => ({
  listTasks: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api', () => ({
  api: {
    listTasks,
    createTask: vi.fn(),
    cancelTask: vi.fn(),
  },
}));

describe('MobileTasksPage', () => {
  it('renders page header', async () => {
    render(<MobileTasksPage />);
    expect(screen.getByText('任务监控')).toBeDefined();
    await waitFor(() => expect(listTasks).toHaveBeenCalled());
  });

  it('renders empty state', async () => {
    render(<MobileTasksPage />);
    expect(screen.getByText(/暂无任务/)).toBeDefined();
    await waitFor(() => expect(listTasks).toHaveBeenCalled());
  });
});
