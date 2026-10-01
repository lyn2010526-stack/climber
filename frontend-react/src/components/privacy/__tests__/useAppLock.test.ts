import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  PRIVACY_STORAGE_KEYS,
  hashPin,
  sha256Hex,
  useAppLock,
} from '../../../hooks/useAppLock';
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

describe('useAppLock state machine', () => {
  it('starts in setup when nothing is stored', () => {
    const { result } = renderHook(() => useAppLock());
    expect(result.current.status).toBe('setup');
    expect(result.current.hasPin).toBe(false);
  });

  it('stores the passcode only as a salted SHA-256 digest', async () => {
    const { result } = renderHook(() => useAppLock());
    let ok = false;
    await act(async () => {
      ok = await result.current.setupPin('135790');
    });
    expect(ok).toBe(true);
    const stored = window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin) ?? '';
    expect(stored).toMatch(/^v1\.[0-9a-f]{32}\.[0-9a-f]{64}$/);
    expect(stored).not.toContain('135790');
    const parts = stored.split('.');
    const salt = parts[1] ?? '';
    const digest = parts[2] ?? '';
    expect(await sha256Hex(`${salt}.135790`)).toBe(digest);
    expect(result.current.status).toBe('unlocked');
  });

  it('rejects passcodes that are not six digits', async () => {
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      expect(await result.current.setupPin('12345')).toBe(false);
    });
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBeNull();
    expect(result.current.status).toBe('setup');
  });

  it('unlockWithPin accepts the right code and rejects the wrong one', async () => {
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(() => {
      result.current.lock();
    });
    expect(result.current.status).toBe('locked');
    await act(async () => {
      expect(await result.current.unlockWithPin('000000')).toBe(false);
    });
    expect(result.current.status).toBe('locked');
    await act(async () => {
      expect(await result.current.unlockWithPin('135790')).toBe(true);
    });
    expect(result.current.status).toBe('unlocked');
  });

  it('keeps the unlock across a refresh and re-locks on lock()', async () => {
    const first = renderHook(() => useAppLock());
    await act(async () => {
      await first.result.current.setupPin('135790');
    });
    const second = renderHook(() => useAppLock());
    expect(second.result.current.status).toBe('unlocked');
    await act(() => {
      second.result.current.lock();
    });
    expect(second.result.current.status).toBe('locked');
    const third = renderHook(() => useAppLock());
    expect(third.result.current.status).toBe('locked');
  });

  it('skipped setup stays unlocked across remounts', () => {
    const first = renderHook(() => useAppLock());
    act(() => {
      first.result.current.skipSetup();
    });
    expect(first.result.current.status).toBe('unlocked');
    const second = renderHook(() => useAppLock());
    expect(second.result.current.status).toBe('unlocked');
    expect(second.result.current.hasPin).toBe(false);
  });

  it('auto-locks after the configured delay and resets on activity', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useAppLock({ autoLockMs: 1000 }));
    await act(async () => {
      await result.current.setupPin('135790');
    });
    expect(result.current.status).toBe('unlocked');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(result.current.status).toBe('unlocked');
    await act(async () => {
      window.dispatchEvent(new Event('pointerdown'));
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(result.current.status).toBe('unlocked');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2);
    });
    expect(result.current.status).toBe('locked');
  });

  it('autoLockMs 0 disables the auto-lock timer', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useAppLock({ autoLockMs: 0 }));
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(result.current.status).toBe('unlocked');
  });

  it('disableLock removes every stored artifact and returns to setup', async () => {
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      await result.current.setupPin('135790');
    });
    act(() => {
      result.current.disableLock();
    });
    expect(result.current.status).toBe('setup');
    expect(result.current.hasPin).toBe(false);
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.pin)).toBeNull();
    expect(window.sessionStorage.getItem(PRIVACY_STORAGE_KEYS.session)).toBeNull();
  });
});

describe('useAppLock WebAuthn', () => {
  it('registers a platform credential and unlocks with it', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockResolvedValue(fakeCredential());
    const { result } = renderHook(() => useAppLock());
    let registered = false;
    await act(async () => {
      registered = await result.current.registerWebAuthn();
    });
    expect(registered).toBe(true);
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.credential)).toBe(
      FAKE_CREDENTIAL_BASE64,
    );
    expect(result.current.canUseWebAuthn).toBe(true);
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(() => {
      result.current.lock();
    });
    expect(result.current.status).toBe('locked');
    credentials.get.mockResolvedValue({ id: 'test-credential', type: 'public-key' });
    let unlocked = false;
    await act(async () => {
      unlocked = await result.current.unlockWithWebAuthn();
    });
    expect(unlocked).toBe(true);
    expect(result.current.status).toBe('unlocked');
    expect(credentials.get).toHaveBeenCalledTimes(1);
    const descriptorList = (credentials.get.mock.calls[0] as unknown[])[0] as {
      publicKey: { allowCredentials: { type: string }[] };
    };
    expect(descriptorList.publicKey.allowCredentials).toHaveLength(1);
    expect(descriptorList.publicKey.allowCredentials[0]?.type).toBe('public-key');
  });

  it('falls back to the passcode when WebAuthn verification fails', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockResolvedValue(fakeCredential());
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      await result.current.registerWebAuthn();
    });
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(() => {
      result.current.lock();
    });
    credentials.get.mockRejectedValue(new Error('NotAllowedError'));
    await act(async () => {
      expect(await result.current.unlockWithWebAuthn()).toBe(false);
    });
    expect(result.current.status).toBe('locked');
    await act(async () => {
      expect(await result.current.unlockWithPin('135790')).toBe(true);
    });
    expect(result.current.status).toBe('unlocked');
  });

  it('treats a null assertion as a failure and keeps the lock', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockResolvedValue(fakeCredential());
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      await result.current.registerWebAuthn();
    });
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(() => {
      result.current.lock();
    });
    credentials.get.mockResolvedValue(null);
    await act(async () => {
      expect(await result.current.unlockWithWebAuthn()).toBe(false);
    });
    expect(result.current.status).toBe('locked');
  });

  it('degrades gracefully when credential creation throws', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockRejectedValue(new Error('NotAllowedError'));
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      expect(await result.current.registerWebAuthn()).toBe(false);
    });
    expect(window.localStorage.getItem(PRIVACY_STORAGE_KEYS.credential)).toBeNull();
    expect(result.current.canUseWebAuthn).toBe(false);
  });

  it('degrades gracefully when the platform authenticator is missing', async () => {
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.canUseWebAuthn).toBe(false);
    await act(async () => {
      expect(await result.current.registerWebAuthn()).toBe(false);
    });
    expect(result.current.canUseWebAuthn).toBe(false);
  });

  it('still unlocks by passcode after a failed registration', async () => {
    installPlatformAuthenticator(true);
    const credentials = installCredentialsStub();
    credentials.create.mockRejectedValue(new Error('InvalidStateError'));
    const { result } = renderHook(() => useAppLock());
    await act(async () => {
      expect(await result.current.registerWebAuthn()).toBe(false);
    });
    await act(async () => {
      await result.current.setupPin('135790');
    });
    await act(() => {
      result.current.lock();
    });
    await act(async () => {
      expect(await result.current.unlockWithPin('135790')).toBe(true);
    });
    expect(result.current.status).toBe('unlocked');
  });
});

describe('hashPin / verifyPin round trip', () => {
  it('verifies the same code against a stored record', async () => {
    const stored = await hashPin('246813');
    expect(stored).toBeTruthy();
    const { verifyPin } = await import('../../../hooks/useAppLock');
    await act(async () => {
      expect(await verifyPin('246813', stored ?? '')).toBe(true);
      expect(await verifyPin('246812', stored ?? '')).toBe(false);
      expect(await verifyPin('246813', 'garbage')).toBe(false);
    });
  });

  it('salts each record so identical codes hash differently', async () => {
    const first = await hashPin('135790');
    const second = await hashPin('135790');
    expect(first).toBeTruthy();
    expect(second).toBeTruthy();
    expect(first).not.toBe(second);
  });
});
