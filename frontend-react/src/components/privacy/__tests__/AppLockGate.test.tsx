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
  it('mounts first-run enrollment over the app and settles unlocked once the passcode is confirmed', async () => {
    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    // The app stays mounted underneath the full-screen enrollment overlay.
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    expect(screen.getByText('请输入六位数字密码')).toBeInTheDocument();
    await enterDigits(user, '135790');
    await screen.findByText('请再次输入以确认');
    await enterDigits(user, '135790');
    await waitFor(() => {
      expect(screen.queryByText('请再次输入以确认')).toBeNull();
    });
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).not.toBeNull();
    expect(window.sessionStorage.getItem(PRIVACY_STORAGE_KEYS.session)).toBe('1');
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
  });

  it('lets the first-run prompt be skipped without configuring a lock', async () => {
    const user = userEvent.setup();
    render(
      <AppLockGate>
        <div data-testid="app-content">secret</div>
      </AppLockGate>,
    );
    await user.click(screen.getByRole('button', { name: '跳过' }));
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: '跳过' })).toBeNull();
    });
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBeNull();
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.skipped)).toBe('1');
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
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

  it('keeps existing PIN protection despite a legacy skip marker and a wrong PIN', async () => {
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.pin, (await hashPin('135790')) ?? '');
    window.localStorage.setItem(PRIVACY_STORAGE_KEYS.skipped, '1');
    const user = userEvent.setup();
    render(<AppLockGate><div data-testid="app-content">secret</div></AppLockGate>);
    await enterDigits(user, '000000');
    await waitFor(() => expect(screen.getByTestId('pin-error')).not.toBeEmptyDOMElement());
    expect(screen.queryByTestId('app-content')).toBeNull();
    expect(window.sessionStorage.getItem(PRIVACY_STORAGE_KEYS.session)).toBeNull();
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
