import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Delete, ScanFace } from 'lucide-react';
import { ClimberMark } from '../brand/ClimberMark';
import { useI18n } from '../../i18n';
import { PIN_LENGTH, verifyPin } from '../../hooks/useAppLock';

/**
 * Full-screen privacy lock in the iOS minimal register: a frosted-glass sheet
 * over the blurred app, the Climber mark, six dots, and a circular keypad.
 *
 * Motion discipline (LobeHub design doc): 100–200ms state changes, ~420ms for
 * the error shake, and a `prefers-reduced-motion` fallback that disables the
 * shake entirely.
 *
 * Injected as a <style> tag because the whitelist forbids touching index.css,
 * and the keyframes only exist for these two components (LockScreen, PinSetup).
 */
export const PRIVACY_SHAKE_STYLE = `
@keyframes privacy-lock-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-10px); }
  40% { transform: translateX(8px); }
  60% { transform: translateX(-6px); }
  80% { transform: translateX(4px); }
}
.privacy-lock-shake {
  animation: privacy-lock-shake 420ms var(--ease-spring, ease-in-out);
}
@media (prefers-reduced-motion: reduce) {
  .privacy-lock-shake {
    animation: none;
  }
}
`;

const SHAKE_RESET_MS = 480;

const DIGIT_ROWS: readonly (readonly string[])[] = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
];

export interface PinDotsProps {
  count: number;
  error?: boolean;
  total?: number;
}

/** Six round progress dots; error turns the filled ones to the error hue. */
export function PinDots({ count, error = false, total = PIN_LENGTH }: PinDotsProps) {
  const { t } = useI18n();
  return (
    <div
      className="flex items-center justify-center gap-4"
      data-testid="pin-dots"
      aria-label={t('privacy.dots_aria', { count })}
    >
      {Array.from({ length: total }, (_, index) => {
        const filled = index < count;
        const tone = filled
          ? error
            ? 'border-[var(--color-error)] bg-[var(--color-error)]'
            : 'border-[var(--color-accent)] bg-[var(--color-accent)]'
          : 'border-[var(--color-border-default)] bg-transparent';
        return (
          <span
            key={index}
            className={`h-3 w-3 rounded-full border transition-colors duration-200 ${tone}`}
          />
        );
      })}
    </div>
  );
}

export interface PinPadProps {
  onPress: (digit: string) => void;
  onBackspace: () => void;
  disabled?: boolean;
  /** Bottom-left slot; LockScreen puts the Face ID trigger there. */
  bottomLeft?: ReactNode;
}

/** 3x4 numeric keypad with the iOS press-scale effect on each key. */
export function PinPad({ onPress, onBackspace, disabled = false, bottomLeft }: PinPadProps) {
  const { t } = useI18n();
  const keyClass =
    'flex h-[72px] w-[72px] select-none items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]/70 text-[26px] font-light text-[var(--color-text-primary)] transition-transform duration-100 ease-out active:scale-90 disabled:pointer-events-none disabled:opacity-40';
  return (
    <div className="grid grid-cols-3 gap-x-6 gap-y-4">
      {DIGIT_ROWS.flat().map((digit) => (
        <button
          key={digit}
          type="button"
          className={keyClass}
          disabled={disabled}
          aria-label={t('privacy.keypad_digit', { digit })}
          onClick={() => onPress(digit)}
        >
          {digit}
        </button>
      ))}
      <div className="flex h-[72px] w-[72px] items-center justify-center">{bottomLeft}</div>
      <button
        type="button"
        className={keyClass}
        disabled={disabled}
        aria-label={t('privacy.keypad_digit', { digit: '0' })}
        onClick={() => onPress('0')}
      >
        0
      </button>
      <button
        type="button"
        className={keyClass}
        disabled={disabled}
        aria-label={t('privacy.keypad_delete')}
        onClick={onBackspace}
      >
        <Delete className="h-6 w-6" aria-hidden="true" />
      </button>
    </div>
  );
}

export interface LockScreenProps {
  /** Stored `v1.<salt>.<digest>` record to verify against. */
  pinHash: string;
  onUnlock: () => void;
  /** Face unlock is offered only when the platform authenticator is ready. */
  webAuthnAvailable?: boolean;
  onWebAuthnUnlock?: () => Promise<boolean>;
}

export function LockScreen({
  pinHash,
  onUnlock,
  webAuthnAvailable = false,
  onWebAuthnUnlock,
}: LockScreenProps) {
  const { t } = useI18n();
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [faceBusy, setFaceBusy] = useState(false);
  const shakeTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (shakeTimer.current !== null) window.clearTimeout(shakeTimer.current);
    },
    [],
  );

  const fail = useCallback(
    (message: string) => {
      setError(message);
      setShaking(true);
      if (shakeTimer.current !== null) window.clearTimeout(shakeTimer.current);
      shakeTimer.current = window.setTimeout(() => setShaking(false), SHAKE_RESET_MS);
    },
    [],
  );

  const submit = useCallback(
    async (candidate: string) => {
      if (verifying) return;
      setVerifying(true);
      const ok = await verifyPin(candidate, pinHash);
      setVerifying(false);
      if (ok) {
        onUnlock();
        return;
      }
      setPin('');
      fail(t('privacy.pin_wrong'));
    },
    [verifying, pinHash, onUnlock, t, fail],
  );

  const press = useCallback(
    (digit: string) => {
      if (verifying || pin.length >= PIN_LENGTH) return;
      setError(null);
      const next = `${pin}${digit}`;
      setPin(next);
      if (next.length === PIN_LENGTH) void submit(next);
    },
    [verifying, pin, submit],
  );

  const backspace = useCallback(() => {
    if (verifying) return;
    setError(null);
    setPin((prev) => prev.slice(0, -1));
  }, [verifying]);

  const faceUnlock = useCallback(async () => {
    if (!onWebAuthnUnlock || faceBusy || verifying) return;
    setFaceBusy(true);
    let ok = false;
    try {
      ok = await onWebAuthnUnlock();
    } catch {
      ok = false;
    }
    setFaceBusy(false);
    if (ok) {
      onUnlock();
      return;
    }
    fail(t('privacy.face_unavailable'));
  }, [onWebAuthnUnlock, faceBusy, verifying, onUnlock, t, fail]);

  // Desktop keyboard entry mirrors the keypad: digits press, Backspace deletes.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (/^\d$/.test(event.key)) {
        press(event.key);
        return;
      }
      if (event.key === 'Backspace') {
        event.preventDefault();
        backspace();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [press, backspace]);

  const showFace = webAuthnAvailable && typeof onWebAuthnUnlock === 'function';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('privacy.lock_aria')}
      className="fixed inset-0 z-[var(--z-modal)] flex flex-col items-center justify-center overflow-hidden px-6"
    >
      <style>{PRIVACY_SHAKE_STYLE}</style>
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[var(--color-bg-page)]/80 backdrop-blur-2xl"
      />
      <div className="relative flex w-full max-w-xs flex-col items-center">
        <div className="flex flex-col items-center gap-2">
          <span className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/70 shadow-[var(--shadow-panel)]">
            <ClimberMark size={30} color="var(--color-accent-foreground)" />
          </span>
          <h1 className="mt-2 text-[17px] font-semibold tracking-tight text-[var(--color-text-primary)]">
            {t('privacy.lock_title')}
          </h1>
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            {t('privacy.lock_subtitle')}
          </p>
        </div>

        <div
          className={`mt-7 flex flex-col items-center ${shaking ? 'privacy-lock-shake' : ''}`}
          data-shake={shaking ? 'true' : undefined}
          aria-live="polite"
        >
          <PinDots count={pin.length} error={Boolean(error)} />
          <p
            className="mt-3 h-5 text-center text-[13px] text-[var(--color-error)]"
            data-testid="pin-error"
            role="alert"
          >
            {error}
          </p>
        </div>

        <div className="mt-4">
          <PinPad
            onPress={press}
            onBackspace={backspace}
            disabled={verifying || faceBusy}
            bottomLeft={
              showFace ? (
                <button
                  type="button"
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)] transition-opacity duration-150 active:opacity-80 disabled:opacity-40"
                  disabled={faceBusy || verifying}
                  aria-label={t('privacy.unlock_face')}
                  onClick={() => void faceUnlock()}
                >
                  <ScanFace className="h-5 w-5" aria-hidden="true" />
                </button>
              ) : undefined
            }
          />
        </div>

        {showFace ? (
          <p className="mt-5 text-[13px] font-medium text-[var(--color-accent-foreground)]">
            {faceBusy ? t('privacy.face_verifying') : t('privacy.unlock_face')}
          </p>
        ) : null}

        <p className="mt-6 text-center text-[12px] text-[var(--color-text-muted)]">
          {t('privacy.auto_lock_hint')}
        </p>
      </div>
    </div>
  );
}
