import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationsPage } from '../NotificationsPage';

const apiMocks = vi.hoisted(() => ({
  listNotifications: vi.fn(),
  sendNotification: vi.fn(),
  testNotification: vi.fn(),
  clearNotifications: vi.fn(),
}));

vi.mock('../../api', () => ({ api: apiMocks }));

const notification = {
  id: 'notification-1',
  title: 'Build complete',
  message: 'The build completed successfully.',
};

describe('NotificationsPage history errors', () => {
  beforeEach(() => {
    Object.values(apiMocks).forEach(mock => mock.mockReset());
  });

  it('shows a retryable error instead of an empty history when loading fails', async () => {
    const user = userEvent.setup();
    apiMocks.listNotifications
      .mockRejectedValueOnce(new Error('Service unavailable'))
      .mockResolvedValueOnce([notification]);

    render(<NotificationsPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('加载通知历史失败');
    expect(screen.queryByText('暂无通知记录')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试加载通知历史' }));

    expect(await screen.findByText(notification.title)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('reports clear failures and preserves the current history', async () => {
    const user = userEvent.setup();
    apiMocks.listNotifications.mockResolvedValueOnce([notification]);
    apiMocks.clearNotifications.mockRejectedValueOnce(new Error('Clear failed'));

    render(<NotificationsPage />);

    await user.click(await screen.findByRole('button', { name: '清空' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('清空通知历史失败');
    expect(screen.getByText(notification.title)).toBeInTheDocument();
  });
});
