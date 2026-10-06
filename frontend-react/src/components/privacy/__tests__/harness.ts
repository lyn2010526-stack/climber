import { webcrypto } from 'node:crypto';
import { vi } from 'vitest';
import i18n from '../../../i18n/config';

/**
 * Shared harness for the privacy lock tests:
 * - jsdom ships `crypto.getRandomValues` but no Web Crypto `subtle`, so the
 *   global is swapped for Node's WebCrypto when `subtle` is missing. The
 *   production code reads `globalThis.crypto` in both real browsers and here.
 * - Language is pinned to zh-CN so text assertions are deterministic.
 */
export async function setupPrivacyHarness(): Promise<void> {
  const env = globalThis as { crypto?: Crypto };
  if (!env.crypto?.subtle) {
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: webcrypto as unknown as Crypto,
    });
  }
  await i18n.changeLanguage('zh-CN');
}

export function resetPrivacyStorage(): void {
  window.localStorage.clear();
  window.sessionStorage.clear();
}

export type CredentialsStub = {
  create: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
};

export function installCredentialsStub(): CredentialsStub {
  const stub: CredentialsStub = { create: vi.fn(), get: vi.fn() };
  Object.defineProperty(window.navigator, 'credentials', {
    configurable: true,
    value: stub,
  });
  return stub;
}

export function removeCredentialsStub(): void {
  const nav = window.navigator as { credentials?: CredentialsStub };
  delete nav.credentials;
}

export function installPlatformAuthenticator(available: boolean): ReturnType<typeof vi.fn> {
  const check = vi.fn().mockResolvedValue(available);
  class StubPublicKeyCredential {
    static isUserVerifyingPlatformAuthenticatorAvailable = check;
  }
  Object.defineProperty(window, 'PublicKeyCredential', {
    configurable: true,
    value: StubPublicKeyCredential,
  });
  return check;
}

export function removePlatformAuthenticatorStub(): void {
  const env = window as { PublicKeyCredential?: unknown };
  delete env.PublicKeyCredential;
}

export function fakeCredential(): { id: string; rawId: Uint8Array; type: string } {
  return {
    id: 'test-credential',
    rawId: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]),
    type: 'public-key',
  };
}

export const FAKE_CREDENTIAL_BASE64 = btoa(String.fromCharCode(1, 2, 3, 4, 5, 6, 7, 8));
