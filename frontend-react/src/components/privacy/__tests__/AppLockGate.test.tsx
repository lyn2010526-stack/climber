import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppLockGate } from '../AppLockGate';
import { PRIVACY_STORAGE_KEYS, hashPin } from '../../../hooks/useAppLock';
import {
  FAKE_CREDENTIAL_BASE64,
  fakeCredential,
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
  vi.useRealTimers();
});

async function enterDigits(user: ReturnType<typeof userEvent.setup>, digits: string): Promise<void> {
  for (const digit of digits.split('')) {
    await user.click(screen.getByRole('button', { name: `数字 ${digit}` }));
  }
}

describe('AppLockGate', () => {
  it('renders PinSetup first and unlocks after a consistent passcode', async () => {
    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    expect(screen.getByText('请输入六位数字密码')).toBeInTheDocument();
    expect(screen.queryByTestId('app-content')).toBeNull();
    await enterDigits(user, '135790');
    await waitFor(() => {
      expect(screen.getByText('请再次输入以确认')).toBeInTheDocument();
    });
    await enterDigits(user, '135790');
    await waitFor(() => {
      expect(screen.getByTestId('app-content')).toBeInTheDocument();
    });
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toMatch(/^v1\./);
  });

  it('renders the lock screen while locked and keeps children unmounted', async () => {
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, (await hashPin('135790')) ?? '');
    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    expect(screen.getByText('Climber 已锁定')).toBeInTheDocument();
    expect(screen.queryByTestId('app-content')).toBeNull();
    await enterDigits(user, '135790');
    await waitFor(() => {
      expect(screen.getByTestId('app-content')).toBeInTheDocument();
    });
    expect(window.sessionStorage.getItem(PRIVACY_STORAGE_KEYS.session)).toBe('1');
  });

  it('shows the face button when a platform credential is registered and unlocks with it', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockResolvedValue(fakeCredential());
    credentials.get.mockResolvedValue({ id: 'test-credential', type: 'public-key' });
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.credential, FAKE_CREDENTIAL_BASE64);
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, (await hashPin('135790')) ?? '');

    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    const faceButton = await screen.findByRole('button', { name: '使用人脸识别解锁' });
    await user.click(faceButton);
    await waitFor(() => {
      expect(screen.getByTestId('app-content')).toBeInTheDocument();
    });
    expect(credentials.get).toHaveBeenCalledTimes(1);
  });

  it('degrades to the passcode when the WebAuthn assertion fails', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.get.mockRejectedValue(new Error('NotAllowedError'));
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.credential, FAKE_CREDENTIAL_BASE64);
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, (await hashPin('135790')) ?? '');

    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    const faceButton = await screen.findByRole('button', { name: '使用人脸识别解锁' });
    await user.click(faceButton);
    await waitFor(() => {
      expect(screen.getByTestId('pin-error')).toHaveTextContent('人脸识别不可用，请输入密码');
    });
    expect(screen.queryByTestId('app-content')).toBeNull();
    await enterDigits(user, '135790');
    await waitFor(() => {
      expect(screen.getByTestId('app-content')).toBeInTheDocument();
    });
    expect(credentials.get).toHaveBeenCalledTimes(1);
  });

  it('keeps rendering children when no lock is configured after a skip', () => {
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.skipped, '1');
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
  });

  it('passes autoLockMs down so the gate re-locks while idle', async () => {
    vi.useFakeTimers();
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, (await hashPin('135790')) ?? '');
    window.sessionStorage.setItem(PRIVACY_STORAGE_KEYS.session, '1');
    render(
      <AppLockGate autoLockMs={2000}>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2001);
    });
    expect(screen.getByText('Climber 已锁定')).toBeInTheDocument();
  });
});
