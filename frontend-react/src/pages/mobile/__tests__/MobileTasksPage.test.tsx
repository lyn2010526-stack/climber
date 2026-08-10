import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';

vi.mock('../../../api', () => ({
  api: {
    listTasks: vi.fn().mockResolvedValue([]),
    createTask: vi.fn(),
    cancelTask: vi.fn(),
  },
}));

describe('MobileTasksPage', () => {
  it('renders page header', () => {
    render(<MobileTasksPage />);
    expect(screen.getByText('任务监控')).toBeDefined();
  });

  it('renders empty state', () => {
    render(<MobileTasksPage />);
    expect(screen.getByText(/暂无任务/)).toBeDefined();
  });
});
