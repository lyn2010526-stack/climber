import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';

vi.mock('../../TaskMonitorPage', () => ({
  default: () => <div>Tasks Content</div>,
}));

describe('MobileTasksPage', () => {
  it('renders page header', () => {
    render(<MobileTasksPage />);
    expect(screen.getByText('任务监控')).toBeDefined();
  });

  it('renders TaskMonitorPage content', () => {
    render(<MobileTasksPage />);
    expect(screen.getByText('Tasks Content')).toBeDefined();
  });
});
