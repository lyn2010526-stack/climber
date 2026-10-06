import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SettingsPage } from '../../../pages/SettingsPage';
import { AppLockGate } from '../AppLockGate';
import { LocalPinSettings } from '../LocalPinSettings';
import { PRIVACY_STORAGE_KEYS, hashPin } from '../../../hooks/useAppLock';
import { resetPrivacyStorage, setupPrivacyHarness } from './harness';

beforeEach(async () => { await setupPrivacyHarness(); resetPrivacyStorage(); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('local PIN settings', () => {
  it('offers enrollment after entering settings and keeps PIN changes local', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ username: 'tester' }), { headers: { 'Content-Type': 'application/json' } }));
    render(<AppLockGate autoLockMs={0}><SettingsPage /></AppLockGate>);
    // First launch mounts the enrollment overlay; decline it so the settings
    // enrollment path stays reachable (the two must not fight each other).
    fireEvent.click(screen.getByRole('button', { name: '跳过' }));
    expect(screen.getByRole('heading', { name: '本地应用锁 PIN' })).toBeInTheDocument();
    expect(screen.getByText(/后端账户密码通过服务器管理/)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    fetchMock.mockClear();
    fireEvent.click(screen.getByRole('button', { name: '设置并启用本地 PIN' }));
    fireEvent.change(screen.getByLabelText('设置本地 PIN'), { target: { value: '135790' } });
    fireEvent.change(screen.getByLabelText('确认本地 PIN'), { target: { value: '135791' } });
    fireEvent.click(screen.getByRole('button', { name: '保存并启用应用锁' }));
    expect(screen.getByRole('alert')).toHaveTextContent('两次 PIN 输入不一致');
    expect(localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBeNull();
    fireEvent.change(screen.getByLabelText('确认本地 PIN'), { target: { value: '135790' } });
    fireEvent.click(screen.getByRole('button', { name: '保存并启用应用锁' }));
    expect(await screen.findByText('本地应用锁已启用')).toBeInTheDocument();
    expect(localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toMatch(/^v1\./);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '立即锁定' }));
    expect(screen.getByText('Climber 已锁定')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '本地应用锁 PIN' })).toBeNull();
  });

  it('preserves the PIN after wrong verification or cancel and removes it after correct verification', async () => {
    const stored = (await hashPin('135790'))!;
    localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, stored);
    sessionStorage.setItem(PRIVACY_STORAGE_KEYS.session, '1');
    render(<LocalPinSettings />);
    fireEvent.click(screen.getByRole('button', { name: '关闭本地应用锁' }));
    fireEvent.change(screen.getByLabelText('当前本地 PIN'), { target: { value: '000000' } });
    fireEvent.click(screen.getByRole('button', { name: '验证并关闭应用锁' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('PIN 验证失败');
    expect(localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBe(stored);
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBe(stored);
    fireEvent.click(screen.getByRole('button', { name: '关闭本地应用锁' }));
    fireEvent.change(screen.getByLabelText('当前本地 PIN'), { target: { value: '135790' } });
    fireEvent.click(screen.getByRole('button', { name: '验证并关闭应用锁' }));
    expect(await screen.findByText(/本地应用锁已关闭/)).toBeInTheDocument();
    expect(localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBeNull();
    expect(sessionStorage.getItem(PRIVACY_STORAGE_KEYS.session)).toBeNull();
    expect(screen.getByRole('button', { name: '设置并启用本地 PIN' })).toBeInTheDocument();
  });
});
