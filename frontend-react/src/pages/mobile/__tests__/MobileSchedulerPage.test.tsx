import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileSchedulerPage } from '../MobileSchedulerPage';

vi.mock('../../../api', () => ({
  api: {
    listSchedulerTasks: vi.fn().mockResolvedValue([]),
    createSchedulerTask: vi.fn(),
    updateSchedulerTask: vi.fn(),
    deleteSchedulerTask: vi.fn(),
  },
}));

describe('MobileSchedulerPage', () => {
  it('renders page header', async () => {
    render(<MobileSchedulerPage />);
    expect(screen.getByText('定时任务')).toBeDefined();
    expect(await screen.findByText(/暂无定时任务/)).toBeDefined();
  });

  it('renders add button and empty state', async () => {
    render(<MobileSchedulerPage />);
    expect(screen.getByText('添加任务')).toBeDefined();
    expect(await screen.findByText(/暂无定时任务/)).toBeDefined();
  });
});
