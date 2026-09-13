import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';

vi.mock('../../TaskMonitorPage', () => ({
  default: () => <div>Tasks Content</div>,
}));

describe('MobileTasksPage', () => {
  it('renders TaskMonitorPage content', async () => {
    render(<MobileTasksPage />);
    await waitFor(() => {
      expect(screen.getByText('Tasks Content')).toBeDefined();
    });
  });
});
