import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MobileNotificationsPage } from '../MobileNotificationsPage';

const { listNotifications } = vi.hoisted(() => ({
  listNotifications: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api', () => ({
  api: {
    listNotifications,
    sendNotification: vi.fn(),
    testNotification: vi.fn(),
    clearNotifications: vi.fn(),
  },
}));

describe('MobileNotificationsPage', () => {
  it('renders page header', async () => {
    render(<MobileNotificationsPage />);
    expect(screen.getByText('通知中心')).toBeDefined();
    await waitFor(() => expect(listNotifications).toHaveBeenCalled());
  });

  it('renders send form and empty history', async () => {
    render(<MobileNotificationsPage />);
    expect(screen.getByText('发送')).toBeDefined();
    expect(screen.getByText('系统测试')).toBeDefined();
    expect(screen.getByText(/暂无通知记录/)).toBeDefined();
    await waitFor(() => expect(listNotifications).toHaveBeenCalled());
  });
});
