import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    sendNotification: vi.fn().mockResolvedValue({ ok: true }),
    testNotification: vi.fn().mockResolvedValue({ ok: true }),
  },
}));

import { NotificationsPage } from '../NotificationsPage';

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('通知中心')).toBeDefined();
  });

  it('renders custom notification form', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('发送自定义通知')).toBeDefined();
  });

  it('renders title input with default value', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const input = screen.getByDisplayValue('Climber 通知测试');
    expect(input).toBeDefined();
  });

  it('renders message textarea with default value', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const textarea = screen.getByDisplayValue('这是一条测试通知');
    expect(textarea).toBeDefined();
  });

  it('updates title on change', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const input = screen.getByDisplayValue('Climber 通知测试');
    fireEvent.change(input, { target: { value: 'New Title' } });
    expect(screen.getByDisplayValue('New Title')).toBeDefined();
  });

  it('updates message on change', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const textarea = screen.getByDisplayValue('这是一条测试通知');
    fireEvent.change(textarea, { target: { value: 'New message' } });
    expect(screen.getByDisplayValue('New message')).toBeDefined();
  });

  it('sends custom notification', async () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('发送通知'));
    await waitFor(() => {
      expect(api.sendNotification).toHaveBeenCalledWith('Climber 通知测试', '这是一条测试通知');
    });
  });

  it('shows success result after sending', async () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('发送通知'));
    await waitFor(() => {
      expect(screen.getByText('通知已发送')).toBeDefined();
    });
  });

  it('shows error result on failure', async () => {
    vi.mocked(api.sendNotification).mockRejectedValue(new Error('Network error'));
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('发送通知'));
    await waitFor(() => {
      expect(screen.getByText(/发送失败/)).toBeDefined();
    });
  });

  it('sends test notification', async () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('系统测试'));
    await waitFor(() => {
      expect(api.testNotification).toHaveBeenCalled();
    });
  });

  it('disables send button when title is empty', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const input = screen.getByDisplayValue('Climber 通知测试');
    fireEvent.change(input, { target: { value: '' } });
    expect(screen.getByRole('button', { name: '发送通知' })).toBeDisabled();
  });

  it('disables send button when message is empty', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    const textarea = screen.getByDisplayValue('这是一条测试通知');
    fireEvent.change(textarea, { target: { value: '' } });
    expect(screen.getByRole('button', { name: '发送通知' })).toBeDisabled();
  });

  it('renders notification tips', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('通知说明')).toBeDefined();
  });
});
