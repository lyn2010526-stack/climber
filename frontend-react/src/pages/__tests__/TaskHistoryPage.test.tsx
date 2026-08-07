import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TaskHistoryPage } from '../TaskHistoryPage';

vi.mock('../../api', () => ({
  api: {
    listTasks: vi.fn().mockResolvedValue([]),
    getTask: vi.fn().mockResolvedValue(null),
  },
}));

describe('TaskHistoryPage', () => {
  it('renders without crashing', () => {
    const { container } = render(<TaskHistoryPage />);
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    render(<TaskHistoryPage />);
    expect(screen.getByText('加载任务历史...')).toBeDefined();
  });
});
