import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { hashPin } from '../../../hooks/useAppLock';
import { LockScreen } from '../LockScreen';
import {
  installCredentialsStub,
  installPlatformAuthenticator,
  removeCredentialsStub,
  removePlatformAuthenticatorStub,
  resetPrivacyStorage,
  setupPrivacyHarness,
} from './harness';

beforeEach(async () => {
  await setupPrivacyHarness();
  resetPrivacyStorage();
});

afterEach(() => {
  cleanup();
  removePlatformAuthenticatorStub();
  removeCredentialsStub();
});

function pressDigits(digits: string): void {
  for (const digit of digits.split('')) {
    fireEvent.click(screen.getByRole('button', { name: `数字 ${digit}` }));
  }
}

async function renderLockedScreen(onUnlock: () => void, extra?: Partial<Parameters<typeof LockScreen>[0]>) {
  const stored = await hashPin('135790');
  render(
    <LockScreen
      pinHash={stored ?? ''}
      onUnlock={onUnlock}
      webAuthnAvailable={extra?.webAuthnAvailable}
      onWebAuthnUnlock={extra?.onWebAuthnUnlock}
    />,
  );
}

describe('LockScreen', () => {
  it('renders the iOS keypad, six dots, and the device-local hint', async () => {
    await renderLockedScreen(vi.fn());
    for (const digit of '0123456789'.split('')) {
      expect(screen.getByRole('button', { name: `数字 ${digit}` })).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument();
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 0 位，共 6 位');
    expect(screen.getByText('密码与人脸数据仅保存在本机')).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: '隐私锁屏' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '使用人脸识别解锁' })).toBeNull();
  });

  it('unlocks when the correct passcode is entered', async () => {
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    pressDigits('135790');
    await waitFor(() => {
      expect(onUnlock).toHaveBeenCalledTimes(1);
    });
  });

  it('shows the wrong-passcode error, shakes, and clears the entry', async () => {
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    pressDigits('000000');
    expect(await screen.findByText('密码不正确')).toBeInTheDocument();
    expect(document.querySelector('[data-shake="true"]')).not.toBeNull();
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 0 位，共 6 位');
    expect(onUnlock).not.toHaveBeenCalled();
  });

  it('deletes the last digit with the backspace key', async () => {
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    pressDigits('13');
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 2 位，共 6 位');
    fireEvent.click(screen.getByRole('button', { name: '删除' }));
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 1 位，共 6 位');
    expect(onUnlock).not.toHaveBeenCalled();
  });

  it('accepts hardware keyboard digits and Backspace', async () => {
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    for (const key of ['1', '3', '5']) {
      fireEvent.keyDown(window, { key });
    }
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 3 位，共 6 位');
    fireEvent.keyDown(window, { key: 'Backspace' });
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 2 位，共 6 位');
  });

  it('offers face unlock when ready and degrades to the passcode on failure', async () => {
    const onUnlock = vi.fn();
    const onWebAuthnUnlock = vi.fn().mockRejectedValue(new Error('NotAllowedError'));
    await renderLockedScreen(onUnlock, { webAuthnAvailable: true, onWebAuthnUnlock });
    const face = screen.getByRole('button', { name: '使用人脸识别解锁' });
    fireEvent.click(face);
    await waitFor(() => {
      expect(onWebAuthnUnlock).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByText('人脸识别不可用，请输入密码')).toBeInTheDocument();
    expect(onUnlock).not.toHaveBeenCalled();
    pressDigits('135790');
    await waitFor(() => {
      expect(onUnlock).toHaveBeenCalledTimes(1);
    });
  });

  it('unlocks when face verification succeeds', async () => {
    const onUnlock = vi.fn();
    const onWebAuthnUnlock = vi.fn().mockResolvedValue(true);
    await renderLockedScreen(onUnlock, { webAuthnAvailable: true, onWebAuthnUnlock });
    fireEvent.click(screen.getByRole('button', { name: '使用人脸识别解锁' }));
    await waitFor(() => {
      expect(onUnlock).toHaveBeenCalledTimes(1);
    });
  });

  it('hides the face button when WebAuthn is unavailable', async () => {
    await renderLockedScreen(vi.fn());
    expect(screen.queryByRole('button', { name: '使用人脸识别解锁' })).toBeNull();
    expect(screen.queryByText('使用人脸识别解锁')).toBeNull();
  });
});

describe('platform authenticator detection', () => {
  it('keeps the gate usable when the authenticator query throws', async () => {
    installPlatformAuthenticator(true);
    installCredentialsStub();
    const { isPlatformAuthenticatorAvailable } = await import('../../../hooks/useAppLock');
    await expect(isPlatformAuthenticatorAvailable()).resolves.toBe(true);
    removePlatformAuthenticatorStub();
    await expect(isPlatformAuthenticatorAvailable()).resolves.toBe(false);
    removeCredentialsStub();
  });
});
