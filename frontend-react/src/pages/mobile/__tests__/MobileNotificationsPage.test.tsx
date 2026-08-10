import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileNotificationsPage } from '../MobileNotificationsPage';

vi.mock('../../../api', () => ({
  api: {
    listNotifications: vi.fn().mockResolvedValue([]),
    sendNotification: vi.fn(),
    testNotification: vi.fn(),
    clearNotifications: vi.fn(),
  },
}));

describe('MobileNotificationsPage', () => {
  it('renders page header', () => {
    render(<MobileNotificationsPage />);
    expect(screen.getByText('通知中心')).toBeDefined();
  });

  it('renders send form and empty history', () => {
    render(<MobileNotificationsPage />);
    expect(screen.getByText('发送')).toBeDefined();
    expect(screen.getByText('系统测试')).toBeDefined();
    expect(screen.getByText(/暂无通知记录/)).toBeDefined();
  });
});
