import type { ReactNode } from 'react';
import { useAppLock } from '../../hooks/useAppLock';
import { LockScreen } from './LockScreen';
import { PinSetup } from './PinSetup';

/**
 * Renders the local privacy lock in front of the app.
 *
 * Behaviour:
 * - `setup` (first launch, no passcode and no skip marker): PinSetup handles
 *   enrollment. The children stay mounted underneath the full-screen overlay so
 *   the session is not torn down, and the gate settles into `unlocked` whether
 *   the user confirms a passcode or skips. Settings can re-arm the lock later;
 *   skipping only clears this first-run prompt.
 * - `locked` (passcode exists, session not unlocked): LockScreen — the children
 *   stay unmounted so nothing behind the lock can be read from the DOM.
 * - `unlocked`: the children render, and the hook's auto-lock timer re-arms the
 *   lock after the configured idle delay.
 *
 * All WebAuthn paths degrade to the passcode; a missing or failing platform
 * authenticator only removes the face button, it never breaks the gate.
 */
export interface AppLockGateProps {
  children: ReactNode;
  /** Auto-lock delay in ms while unlocked. 0 disables. Defaults to the stored preference or 5 minutes. */
  autoLockMs?: number;
}

export function AppLockGate({ children, autoLockMs }: AppLockGateProps) {
  const lock = useAppLock({ autoLockMs });

  if (lock.status === 'locked' && lock.pinHash) {
    return (
      <LockScreen
        pinHash={lock.pinHash}
        onUnlock={lock.markUnlocked}
        webAuthnAvailable={lock.canUseWebAuthn}
        onWebAuthnUnlock={lock.unlockWithWebAuthn}
      />
    );
  }

  if (lock.status === 'setup') {
    return (
      <>
        {children}
        <PinSetup onConfirm={lock.setupPin} onSkip={lock.skipSetup} />
      </>
    );
  }

  return <>{children}</>;
}
