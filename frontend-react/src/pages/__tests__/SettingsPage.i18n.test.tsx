import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import i18n from '../../i18n/config';
import { api } from '../../api';
import { SettingsPage } from '../SettingsPage';
import en from '../../locales/en.json';
import zhCN from '../../locales/zh-CN.json';

vi.mock('../../api', () => ({
  api: {
    getCurrentUser: vi.fn(),
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    getAuthHealth: vi.fn(),
    changePassword: vi.fn(),
  },
}));

const originalLanguage = i18n.language;
const settings = {
  autonomous_agent_mode: false, token_throttle_mcp_enabled: false,
  mcp_ready: true, mcp_status: 'connected',
  notifications: { email_address: 'tester@example.com', webhook_configured: true },
};

beforeEach(async () => {
  vi.mocked(api.getCurrentUser).mockResolvedValue({ id: 1, username: 'tester', email: 'tester@example.com', role: 'user' });
  vi.mocked(api.getSettings).mockResolvedValue(settings);
  vi.mocked(api.updateSettings).mockResolvedValue(settings);
  vi.mocked(api.getAuthHealth).mockResolvedValue({ authentication_enabled: true, auth_method: 'token' });
  await i18n.changeLanguage('en');
});

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  await i18n.changeLanguage(originalLanguage);
});

describe('Settings with production i18n', () => {
  it('keeps the English and Chinese settings keys in sync', () => {
    expect(Object.keys(en.settings).sort()).toEqual(Object.keys(zhCN.settings).sort());
    for (const value of Object.values(en.settings)) expect(value).not.toMatch(/[\u3400-\u9fff]/);
  });

  it('renders profile, models, notifications, security and about in English', async () => {
    const { container } = render(<SettingsPage />);
    expect(await screen.findByText('Basic Information')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter username')).toBeDisabled();
    expect(screen.getByRole('navigation', { name: 'Settings sections' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(en.settings.profile_save_notice);

    fireEvent.click(screen.getByRole('button', { name: 'API Settings' }));
    expect(await screen.findByText('Execution Mode')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('switch', { name: 'Autonomous Agent Mode' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Settings saved');

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }));
    expect(await screen.findByText('Email Notifications')).toBeInTheDocument();
    expect(screen.getByLabelText('Notification Email Address')).toHaveValue('tester@example.com');
    expect(screen.getByPlaceholderText('Configured; enter a new URL to replace it')).toBeInTheDocument();
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    fireEvent.click(screen.getByRole('button', { name: 'Clear Saved Webhook' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));
    expect(confirm).toHaveBeenLastCalledWith(en.settings.webhook_clear_confirm);
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }));
    expect(confirm).toHaveBeenLastCalledWith(en.settings.reset_confirm);
    fireEvent.click(screen.getByRole('button', { name: 'Keep Existing Webhook' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Configuration saved.');

    fireEvent.click(screen.getByRole('button', { name: 'Security' }));
    expect(await screen.findByText('Authentication method: token')).toBeInTheDocument();
    expect(screen.getByText('Authentication enabled')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Change Password' }));
    expect(screen.getByLabelText('Current Password')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter new password (at least 6 characters)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Advanced' }));
    expect(screen.getByText('Version not reported')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'GitHub Repository' })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[\u3400-\u9fff]|settings\./);
  });

  it('updates password validation on language changes while preserving form values', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Security' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Change Password' }));
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'secret1' } });
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'secret2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Change' }));
    expect(screen.getByRole('alert')).toHaveTextContent(en.settings.password_mismatch);
    await act(async () => { await i18n.changeLanguage('zh-CN'); });
    expect(screen.getByRole('alert')).toHaveTextContent(zhCN.settings.password_mismatch);
    expect(screen.getByLabelText('新密码')).toHaveValue('secret1');
    expect(api.getAuthHealth).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText('新密码'), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText('确认新密码'), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: '确认修改' }));
    expect(screen.getByRole('alert')).toHaveTextContent(zhCN.settings.password_too_short);
    await act(async () => { await i18n.changeLanguage('en'); });
    expect(screen.getByRole('alert')).toHaveTextContent(en.settings.password_too_short);
    expect(api.changePassword).not.toHaveBeenCalled();
  });

  it('translates missing notification configuration without reloading on language changes', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({});
    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(en.settings.notifications_missing);
    await act(async () => { await i18n.changeLanguage('zh-CN'); });
    expect(screen.getByRole('alert')).toHaveTextContent(zhCN.settings.notifications_missing);
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
    expect(api.getSettings).toHaveBeenCalledTimes(1);
  });

  it('translates fallback load errors and preserves server error messages', async () => {
    vi.mocked(api.getCurrentUser).mockRejectedValueOnce(null).mockRejectedValueOnce(new Error('Server unavailable'));
    render(<SettingsPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(en.settings.profile_load_failed);
    await act(async () => { await i18n.changeLanguage('zh-CN'); });
    expect(screen.getByRole('alert')).toHaveTextContent(zhCN.settings.profile_load_failed);
    expect(api.getCurrentUser).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Server unavailable');
  });
});
