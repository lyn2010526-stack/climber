import { useCallback, useEffect, useMemo, useState } from 'react';

/**
 * Local privacy lock: a six-digit passcode plus an optional platform
 * authenticator (Face ID / Touch ID via WebAuthn), stored entirely on device.
 *
 * Storage contract:
 * - The passcode is never stored in plain text. `localStorage` holds a random
 *   salt plus the SHA-256 digest of `salt.passcode`, computed with Web Crypto
 *   `subtle.digest`.
 * - `sessionStorage` records the session unlock, so closing the tab re-arms
 *   the lock while a refresh keeps the user in.
 * - The WebAuthn credential id lives in `localStorage` after registration.
 *
 * Browser API failures are handled; enrollment requires successful persistence.
 */

export type AppLockStatus = 'setup' | 'locked' | 'unlocked';

export const PIN_LENGTH = 6;

const PIN_PATTERN = new RegExp(`^\\d{${PIN_LENGTH}}$`);

export const PRIVACY_STORAGE_KEYS = {
  pin: 'climber.privacy.pinHash',
  skipped: 'climber.privacy.skipped',
  session: 'climber.privacy.sessionUnlocked',
  credential: 'climber.privacy.webauthnCredentialId',
  autoLockMs: 'climber.privacy.autoLockMs',
} as const;

const DEFAULT_AUTO_LOCK_MS = 5 * 60 * 1000;
const LOCK_CHANGED_EVENT = 'climber:privacy-lock-changed';

function notifyLockChanged(): void {
  window.dispatchEvent(new Event(LOCK_CHANGED_EVENT));
}
const WEB_AUTHN_TIMEOUT_MS = 60_000;
const WEB_AUTHN_RP_NAME = 'Climber';
const WEB_AUTHN_USER_NAME = 'climber-local';
const WEB_AUTHN_USER_DISPLAY = 'Climber';

type SafeStorage = Storage | undefined;

function safeStorage(kind: 'local' | 'session'): SafeStorage {
  try {
    if (typeof window === 'undefined') return undefined;
    return kind === 'local' ? window.localStorage : window.sessionStorage;
  } catch {
    return undefined;
  }
}

function readStorage(storage: SafeStorage, key: string): string | null {
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(storage: SafeStorage, key: string, value: string): void {
  if (!storage) return;
  try {
    storage.setItem(key, value);
  } catch {
    // Storage unavailable (private mode): the lock keeps working in memory.
  }
}

function removeStorage(storage: SafeStorage, key: string): void {
  if (!storage) return;
  try {
    storage.removeItem(key);
  } catch {
    // Ignore: nothing we can do without storage access.
  }
}

function assertWebCrypto(): Crypto {
  const webCrypto = globalThis.crypto;
  if (!webCrypto?.getRandomValues || !webCrypto.subtle) {
    throw new Error('Web Crypto unavailable');
  }
  return webCrypto;
}

/** Hex-encode `input` with SHA-256, or `null` when Web Crypto is missing. */
export async function sha256Hex(input: string): Promise<string | null> {
  try {
    const digest = await assertWebCrypto().subtle.digest(
      'SHA-256',
      new TextEncoder().encode(input),
    );
    return Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, '0'),
    ).join('');
  } catch {
    return null;
  }
}

function randomHex(byteLength: number): string | null {
  try {
    const bytes = new Uint8Array(byteLength);
    assertWebCrypto().getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  } catch {
    return null;
  }
}

/** Salt + SHA-256 encoding of a passcode: `v1.<salt>.<digest>`, never plain text. */
export async function hashPin(pin: string): Promise<string | null> {
  const salt = randomHex(16);
  if (!salt) return null;
  const digest = await sha256Hex(`${salt}.${pin}`);
  if (!digest) return null;
  return `v1.${salt}.${digest}`;
}

/** Constant-time-ish comparison of a passcode against a stored `v1.` record. */
export async function verifyPin(pin: string, stored: string): Promise<boolean> {
  const parts = stored.split('.');
  if (parts.length !== 3) return false;
  const [version, salt, expected] = parts;
  if (version !== 'v1' || !salt || !expected) return false;
  const digest = await sha256Hex(`${salt}.${pin}`);
  if (!digest || digest.length !== expected.length) return false;
  let diff = 0;
  for (let index = 0; index < digest.length; index += 1) {
    diff |= digest.charCodeAt(index) ^ expected.charCodeAt(index);
  }
  return diff === 0;
}

function bytesToBase64(bytes: Uint8Array): string | null {
  try {
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
  } catch {
    return null;
  }
}

function base64ToBytes(value: string): Uint8Array<ArrayBuffer> | null {
  try {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  } catch {
    return null;
  }
}

/** True when the current browser exposes a user-verifying platform authenticator. */
export async function isPlatformAuthenticatorAvailable(): Promise<boolean> {
  try {
    if (typeof window === 'undefined') return false;
    const check = window.PublicKeyCredential?.isUserVerifyingPlatformAuthenticatorAvailable;
    if (typeof check !== 'function') return false;
    return await check.call(window.PublicKeyCredential);
  } catch {
    return false;
  }
}

/** Register a platform credential (Face ID / Touch ID) and store its id. */
export async function registerWebAuthnCredential(): Promise<boolean> {
  try {
    if (typeof navigator === 'undefined' || !navigator.credentials) return false;
    const salt = randomHex(32);
    if (!salt) return false;
    const challenge = new Uint8Array(32);
    assertWebCrypto().getRandomValues(challenge);
    const userId = new TextEncoder().encode(salt);
    const credential = await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { name: WEB_AUTHN_RP_NAME },
        user: {
          id: Uint8Array.from(userId),
          name: WEB_AUTHN_USER_NAME,
          displayName: WEB_AUTHN_USER_DISPLAY,
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 },
          { type: 'public-key', alg: -257 },
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'required',
          residentKey: 'preferred',
        },
        timeout: WEB_AUTHN_TIMEOUT_MS,
        attestation: 'none',
      },
    });
    const rawId = (credential as PublicKeyCredential | null)?.rawId;
    if (!rawId) return false;
    const idBase64 = bytesToBase64(new Uint8Array(rawId));
    if (!idBase64) return false;
    writeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.credential, idBase64);
    return true;
  } catch {
    return false;
  }
}

/** Ask the platform authenticator for an assertion bound to the stored credential. */
export async function verifyWebAuthnCredential(credentialIdBase64: string): Promise<boolean> {
  try {
    if (typeof navigator === 'undefined' || !navigator.credentials) return false;
    const id = base64ToBytes(credentialIdBase64);
    if (!id) return false;
    const challenge = new Uint8Array(32);
    assertWebCrypto().getRandomValues(challenge);
    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge,
        allowCredentials: [{ id, type: 'public-key' }],
        userVerification: 'required',
        timeout: WEB_AUTHN_TIMEOUT_MS,
      },
    });
    return Boolean(assertion);
  } catch {
    return false;
  }
}

function readStatusFromStorage(): AppLockStatus {
  const local = safeStorage('local');
  if (!readStorage(local, PRIVACY_STORAGE_KEYS.pin)) {
    return readStorage(local, PRIVACY_STORAGE_KEYS.skipped) === '1' ? 'unlocked' : 'setup';
  }
  return readStorage(safeStorage('session'), PRIVACY_STORAGE_KEYS.session) === '1'
    ? 'unlocked'
    : 'locked';
}

function normalizeAutoLock(ms: number): number {
  return Number.isFinite(ms) && ms > 0 ? Math.floor(ms) : 0;
}

export interface UseAppLockOptions {
  /** Auto-lock delay in ms. 0 disables the timer. Overrides the stored preference. */
  autoLockMs?: number;
}

export interface UseAppLockResult {
  status: AppLockStatus;
  hasPin: boolean;
  pinHash: string | null;
  /** Platform authenticator is present AND a credential is registered. */
  canUseWebAuthn: boolean;
  autoLockMs: number;
  setupPin(pin: string): Promise<boolean>;
  skipSetup(): void;
  unlockWithPin(pin: string): Promise<boolean>;
  unlockWithWebAuthn(): Promise<boolean>;
  registerWebAuthn(): Promise<boolean>;
  markUnlocked(): void;
  lock(): void;
  disableLock(pin: string): Promise<boolean>;
  setAutoLockMs(ms: number): void;
}

export function useAppLock(options: UseAppLockOptions = {}): UseAppLockResult {
  const requestedAutoLockMs = options.autoLockMs;

  const [status, setStatus] = useState<AppLockStatus>(readStatusFromStorage);
  const [pinHash, setPinHash] = useState<string | null>(() =>
    readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin),
  );
  const [credentialId, setCredentialId] = useState<string | null>(() =>
    readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.credential),
  );
  const [platformAvailable, setPlatformAvailable] = useState(false);
  const [autoLockMs, setAutoLockMsState] = useState<number>(() => {
    if (requestedAutoLockMs !== undefined) return normalizeAutoLock(requestedAutoLockMs);
    const stored = readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.autoLockMs);
    if (stored === null) return DEFAULT_AUTO_LOCK_MS;
    const parsed = Number.parseInt(stored, 10);
    return Number.isFinite(parsed) ? normalizeAutoLock(parsed) : DEFAULT_AUTO_LOCK_MS;
  });

  useEffect(() => {
    const sync = () => {
      setPinHash(readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin));
      setCredentialId(readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.credential));
      setStatus(readStatusFromStorage());
      if (requestedAutoLockMs === undefined) {
        const stored = readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.autoLockMs);
        setAutoLockMsState(stored === null ? DEFAULT_AUTO_LOCK_MS : normalizeAutoLock(Number(stored)));
      }
    };
    window.addEventListener(LOCK_CHANGED_EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(LOCK_CHANGED_EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, [requestedAutoLockMs]);

  useEffect(() => {
    let cancelled = false;
    isPlatformAuthenticatorAvailable()
      .then((available) => {
        if (!cancelled) setPlatformAvailable(available);
      })
      .catch(() => {
        if (!cancelled) setPlatformAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (requestedAutoLockMs === undefined) return;
    const next = normalizeAutoLock(requestedAutoLockMs);
    writeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.autoLockMs, String(next));
    setAutoLockMsState(next);
  }, [requestedAutoLockMs]);

  const markUnlocked = useCallback(() => {
    if (!readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin)) return;
    writeStorage(safeStorage('session'), PRIVACY_STORAGE_KEYS.session, '1');
    setStatus((prev) => (prev === 'locked' ? 'unlocked' : prev));
    notifyLockChanged();
  }, []);

  const lock = useCallback(() => {
    removeStorage(safeStorage('session'), PRIVACY_STORAGE_KEYS.session);
    setStatus(readStatusFromStorage());
    notifyLockChanged();
  }, []);

  const setupPin = useCallback(async (pin: string): Promise<boolean> => {
    if (!PIN_PATTERN.test(pin) || readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin)) return false;
    const encoded = await hashPin(pin);
    if (!encoded) return false;
    if (readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin)) return false;
    writeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin, encoded);
    if (readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin) !== encoded) return false;
    removeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.skipped);
    writeStorage(safeStorage('session'), PRIVACY_STORAGE_KEYS.session, '1');
    setPinHash(encoded);
    setStatus('unlocked');
    notifyLockChanged();
    return true;
  }, []);

  const skipSetup = useCallback(() => {
    if (readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin)) return;
    writeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.skipped, '1');
    setStatus('unlocked');
    notifyLockChanged();
  }, []);

  const unlockWithPin = useCallback(
    async (pin: string): Promise<boolean> => {
      const stored = readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.pin);
      if (!stored) return false;
      const ok = await verifyPin(pin, stored);
      if (ok) markUnlocked();
      return ok;
    },
    [markUnlocked],
  );

  const unlockWithWebAuthn = useCallback(async (): Promise<boolean> => {
    const stored = readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.credential);
    if (!stored) return false;
    const ok = await verifyWebAuthnCredential(stored);
    if (ok) markUnlocked();
    return ok;
  }, [markUnlocked]);

  const registerWebAuthn = useCallback(async (): Promise<boolean> => {
    const ok = await registerWebAuthnCredential();
    if (ok) {
      setCredentialId(readStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.credential));
      setPlatformAvailable(true);
      notifyLockChanged();
    }
    return ok;
  }, []);

  const disableLock = useCallback(async (pin: string): Promise<boolean> => {
    const local = safeStorage('local');
    const stored = readStorage(local, PRIVACY_STORAGE_KEYS.pin);
    if (!stored || !PIN_PATTERN.test(pin) || !(await verifyPin(pin, stored))) return false;
    if (readStorage(local, PRIVACY_STORAGE_KEYS.pin) !== stored) return false;
    removeStorage(local, PRIVACY_STORAGE_KEYS.pin);
    if (readStorage(local, PRIVACY_STORAGE_KEYS.pin)) return false;
    removeStorage(local, PRIVACY_STORAGE_KEYS.skipped);
    removeStorage(local, PRIVACY_STORAGE_KEYS.credential);
    removeStorage(local, PRIVACY_STORAGE_KEYS.autoLockMs);
    removeStorage(safeStorage('session'), PRIVACY_STORAGE_KEYS.session);
    setPinHash(null);
    setCredentialId(null);
    setPlatformAvailable(false);
    setStatus('setup');
    notifyLockChanged();
    return true;
  }, []);

  const setAutoLockMs = useCallback((ms: number) => {
    const next = normalizeAutoLock(ms);
    writeStorage(safeStorage('local'), PRIVACY_STORAGE_KEYS.autoLockMs, String(next));
    setAutoLockMsState(next);
    notifyLockChanged();
  }, []);

  // Auto-lock: while unlocked with a passcode set, any activity re-arms the
  // timer; when it expires the session unlock is dropped and the gate locks.
  useEffect(() => {
    if (status !== 'unlocked' || !pinHash || autoLockMs <= 0) return undefined;
    let timer: number | undefined;
    const arm = () => {
      if (timer !== undefined) window.clearTimeout(timer);
      timer = window.setTimeout(lock, autoLockMs);
    };
    const events = ['pointerdown', 'keydown', 'touchstart', 'visibilitychange'] as const;
    for (const event of events) {
      window.addEventListener(event, arm, { passive: true });
    }
    arm();
    return () => {
      if (timer !== undefined) window.clearTimeout(timer);
      for (const event of events) window.removeEventListener(event, arm);
    };
  }, [status, pinHash, autoLockMs, lock]);

  const canUseWebAuthn = useMemo(
    () => platformAvailable && credentialId !== null,
    [platformAvailable, credentialId],
  );

  return {
    status,
    hasPin: pinHash !== null,
    pinHash,
    canUseWebAuthn,
    autoLockMs,
    setupPin,
    skipSetup,
    unlockWithPin,
    unlockWithWebAuthn,
    registerWebAuthn,
    markUnlocked,
    lock,
    disableLock,
    setAutoLockMs,
  };
}
