import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { motion, useAnimationControls } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { Delete, ScanFace } from 'lucide-react';
import { useI18n } from '../../i18n';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { PIN_LENGTH, verifyPin } from '../../hooks/useAppLock';
import {
  LOCK_EASE,
  LOCK_ENTRANCE_MS,
  LOCK_UNLOCK_MS,
  lockSec,
} from './lockTiming';
import { LockBackdrop, LockBrand } from './lockMotion';

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
@keyframes privacy-face-ring-breathe {
  0% { transform: scale(0.7); opacity: 0; }
  30% { opacity: 0.85; }
  100% { transform: scale(1.55); opacity: 0; }
}
@keyframes privacy-face-ring-collapse {
  0% { transform: scale(1); opacity: 0.85; }
  100% { transform: scale(0.1); opacity: 0; }
}
.privacy-face-ring {
  position: absolute;
  inset: -8px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-accent);
  pointer-events: none;
  animation: privacy-face-ring-breathe 600ms var(--ease-out) infinite;
}
.privacy-face-ring-b {
  animation-duration: 900ms;
  animation-delay: 300ms;
}
.privacy-face-ring[data-tone='error'] {
  border-color: var(--color-error);
  animation: privacy-face-ring-collapse 260ms var(--ease-spring) forwards;
}
.privacy-face-ring[data-tone='success'] {
  animation: privacy-face-ring-collapse 240ms var(--ease-spring) forwards;
}
@media (prefers-reduced-motion: reduce) {
  .privacy-lock-shake {
    animation: none;
  }
  .privacy-face-ring {
    animation: none;
    opacity: 0;
  }
  .privacy-lock-key {
    transition: none;
  }
  .privacy-lock-key:active {
    transform: none;
  }
  .privacy-lock-dot {
    transition: none;
  }
}
`;

const SHAKE_RESET_MS = 480;

const DIGIT_ROWS: readonly (readonly string[])[] = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
];

const DOT_VARIANTS: Variants = {
  filled: { scale: [0.6, 1.06, 1] },
  empty: { scale: [1.06, 0.6, 1] },
  celebrate: (index: number) => ({
    scale: [1, 1.32, 1],
    transition: {
      delay: lockSec(index * LOCK_UNLOCK_MS.dotStagger),
      duration: lockSec(LOCK_UNLOCK_MS.dot),
      ease: LOCK_EASE,
    },
  }),
};

export interface PinDotsProps {
  count: number;
  error?: boolean;
  total?: number;
  /** Success sequence: dots light up teal one by one. */
  celebrate?: boolean;
  /** Bump this number to fire the 80ms synchronous pre-submit pulse. */
  pulseSignal?: number;
}

/** Six round progress dots; error turns the filled ones to the error hue. */
export function PinDots({
  count,
  error = false,
  total = PIN_LENGTH,
  celebrate = false,
  pulseSignal = 0,
}: PinDotsProps) {
  const { t } = useI18n();
  const reducedMotion = usePrefersReducedMotion();
  const pulseControls = useAnimationControls();

  useEffect(() => {
    if (pulseSignal <= 0 || reducedMotion) return;
    void pulseControls.start({ scale: [1, 1.05, 1] }, { duration: lockSec(LOCK_UNLOCK_MS.pulse) });
  }, [pulseSignal, reducedMotion, pulseControls]);

  return (
    <motion.div
      className="flex items-center justify-center gap-4"
      data-testid="pin-dots"
      aria-label={t('privacy.dots_aria', { count })}
      animate={pulseControls}
    >
      {Array.from({ length: total }, (_, index) => {
        const filled = index < count;
        const tone = filled
          ? error
            ? 'border-[var(--color-error)] bg-[var(--color-error)]'
            : celebrate
              ? 'border-[var(--color-accent-foreground)] bg-[var(--color-accent-foreground)]'
              : 'border-[var(--color-accent)] bg-[var(--color-accent)]'
          : 'border-[var(--color-border-default)] bg-transparent';
        return (
          <motion.span
            key={index}
            data-lock-item="pin-dot"
            initial={reducedMotion ? false : { opacity: 0, y: 4, scale: 0.6 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
              duration: lockSec(LOCK_ENTRANCE_MS.dot),
              delay: reducedMotion
                ? 0
                : lockSec(LOCK_ENTRANCE_MS.dotDelay + index * LOCK_ENTRANCE_MS.dotStagger),
              ease: LOCK_EASE,
            }}
          >
            <motion.span
              className={`privacy-lock-dot block h-3 w-3 rounded-full border transition-colors duration-200 ${tone}`}
              initial={false}
              animate={
                reducedMotion
                  ? { scale: 1 }
                  : celebrate
                    ? 'celebrate'
                    : filled
                      ? 'filled'
                      : 'empty'
              }
              variants={reducedMotion ? undefined : DOT_VARIANTS}
              custom={index}
              transition={{ duration: 0.12, ease: 'easeOut' }}
            />
          </motion.span>
        );
      })}
    </motion.div>
  );
}

export interface PinPadProps {
  onPress: (digit: string) => void;
  onBackspace: () => void;
  disabled?: boolean;
  /** Error register: pressed keys tint to the error token. */
  error?: boolean;
  /** Bottom-left slot; LockScreen puts the Face ID trigger there. */
  bottomLeft?: ReactNode;
}

/** 3x4 numeric keypad with the iOS press-scale effect on each key. */
export function PinPad({
  onPress,
  onBackspace,
  disabled = false,
  error = false,
  bottomLeft,
}: PinPadProps) {
  const { t } = useI18n();
  const keyClass = `privacy-lock-key flex h-[72px] w-[72px] select-none items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]/70 text-[26px] font-light text-[var(--color-text-primary)] transition-transform duration-100 ease-out active:scale-90 disabled:pointer-events-none disabled:opacity-40 ${
    error ? 'active:border-[var(--color-error)] active:text-[var(--color-error)]' : ''
  }`;
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

type FacePhase = 'idle' | 'scanning' | 'failed' | 'succeeded';
type UnlockPhase = 'idle' | 'celebrate';

export function LockScreen({
  pinHash,
  onUnlock,
  webAuthnAvailable = false,
  onWebAuthnUnlock,
}: LockScreenProps) {
  const { t } = useI18n();
  const reducedMotion = usePrefersReducedMotion();
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [facePhase, setFacePhase] = useState<FacePhase>('idle');
  const [unlockPhase, setUnlockPhase] = useState<UnlockPhase>('idle');
  const [pulseSeq, setPulseSeq] = useState(0);
  const shakeTimer = useRef<number | null>(null);
  const faceResetTimer = useRef<number | null>(null);
  const unlockTimer = useRef<number | null>(null);

  const celebrating = unlockPhase === 'celebrate';
  const keypadLocked =
    verifying || celebrating || facePhase === 'scanning' || facePhase === 'succeeded';

  useEffect(
    () => () => {
      for (const timer of [shakeTimer, faceResetTimer, unlockTimer]) {
        if (timer.current !== null) window.clearTimeout(timer.current);
      }
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

  const celebrateUnlock = useCallback(() => {
    if (reducedMotion) {
      onUnlock();
      return;
    }
    setUnlockPhase('celebrate');
    if (unlockTimer.current !== null) window.clearTimeout(unlockTimer.current);
    unlockTimer.current = window.setTimeout(() => onUnlock(), LOCK_UNLOCK_MS.hold);
  }, [reducedMotion, onUnlock]);

  const submit = useCallback(
    async (candidate: string) => {
      if (verifying) return;
      setVerifying(true);
      const ok = await verifyPin(candidate, pinHash);
      setVerifying(false);
      if (ok) {
        celebrateUnlock();
        return;
      }
      setPin('');
      fail(t('privacy.pin_wrong'));
    },
    [verifying, pinHash, celebrateUnlock, t, fail],
  );

  const press = useCallback(
    (digit: string) => {
      if (verifying || celebrating) return;
      setError(null);
      const next = `${pin}${digit}`;
      setPin(next);
      if (next.length === PIN_LENGTH) {
        if (!reducedMotion) setPulseSeq((seq) => seq + 1);
        void submit(next);
      }
    },
    [verifying, celebrating, pin, reducedMotion, submit],
  );

  const backspace = useCallback(() => {
    if (verifying || celebrating) return;
    setError(null);
    setPin((prev) => prev.slice(0, -1));
  }, [verifying, celebrating]);

  const faceUnlock = useCallback(async () => {
    if (!onWebAuthnUnlock || facePhase !== 'idle' || verifying || celebrating) return;
    setFacePhase('scanning');
    let ok = false;
    try {
      ok = await onWebAuthnUnlock();
    } catch {
      ok = false;
    }
    if (ok) {
      setFacePhase('succeeded');
      celebrateUnlock();
      return;
    }
    setFacePhase('failed');
    if (faceResetTimer.current !== null) window.clearTimeout(faceResetTimer.current);
    faceResetTimer.current = window.setTimeout(() => setFacePhase('idle'), LOCK_UNLOCK_MS.faceFailReset);
    fail(t('privacy.face_unavailable'));
  }, [onWebAuthnUnlock, facePhase, verifying, celebrating, celebrateUnlock, t, fail]);

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
  const faceTone =
    facePhase === 'failed' ? 'error' : facePhase === 'succeeded' ? 'success' : 'scanning';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('privacy.lock_aria')}
      data-lock-intro={reducedMotion ? 'instant' : 'play'}
      data-unlock-phase={unlockPhase}
      data-face-phase={facePhase}
      className="fixed inset-0 z-[var(--z-modal)] flex flex-col items-center justify-center overflow-hidden px-6"
    >
      <style>{PRIVACY_SHAKE_STYLE}</style>
      <LockBackdrop reducedMotion={reducedMotion} />
      <div className="relative flex w-full max-w-xs flex-col items-center">
        <LockBrand
          reducedMotion={reducedMotion}
          title={t('privacy.lock_title')}
          subtitle={t('privacy.lock_subtitle')}
        />

        <motion.div
          className={`mt-7 flex flex-col items-center ${shaking ? 'privacy-lock-shake' : ''}`}
          data-shake={shaking ? 'true' : undefined}
          data-lock-item="pin-stage"
          aria-live="polite"
          initial={false}
          animate={celebrating ? { y: -24, opacity: 0 } : { y: 0, opacity: 1 }}
          transition={
            celebrating
              ? {
                  duration: lockSec(LOCK_UNLOCK_MS.float),
                  delay: lockSec(LOCK_UNLOCK_MS.floatDelay),
                  ease: LOCK_EASE,
                }
              : { duration: 0.2 }
          }
        >
          <PinDots
            count={pin.length}
            error={Boolean(error)}
            celebrate={celebrating}
            pulseSignal={pulseSeq}
          />
          <p
            className="mt-3 h-5 text-center text-[13px] text-[var(--color-error)]"
            data-testid="pin-error"
            role="alert"
          >
            {error}
          </p>
        </motion.div>

        <motion.div
          className="mt-4"
          data-lock-item="keypad"
          initial={reducedMotion ? false : { opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={
            reducedMotion
              ? { duration: 0 }
              : {
                  type: 'spring',
                  stiffness: 380,
                  damping: 26,
                  delay: lockSec(LOCK_ENTRANCE_MS.keypadDelay),
                }
          }
        >
          <PinPad
            onPress={press}
            onBackspace={backspace}
            disabled={keypadLocked}
            error={Boolean(error)}
            bottomLeft={
              showFace ? (
                <motion.div
                  className="relative flex h-12 w-12 items-center justify-center"
                  data-lock-item="face-button"
                  initial={reducedMotion ? false : { opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{
                    duration: lockSec(LOCK_ENTRANCE_MS.face),
                    delay: reducedMotion ? 0 : lockSec(LOCK_ENTRANCE_MS.faceDelay),
                    ease: LOCK_EASE,
                  }}
                >
                  {facePhase !== 'idle' && !reducedMotion ? (
                    <>
                      <span aria-hidden="true" className="privacy-face-ring" data-tone={faceTone} />
                      <span
                        aria-hidden="true"
                        className="privacy-face-ring privacy-face-ring-b"
                        data-tone={faceTone}
                      />
                    </>
                  ) : null}
                  <button
                    type="button"
                    className={`flex h-12 w-12 items-center justify-center rounded-full border bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)] transition-colors duration-150 active:opacity-80 disabled:opacity-40 ${
                      facePhase === 'failed'
                        ? 'border-[var(--color-error)]'
                        : 'border-[var(--color-border-subtle)]'
                    }`}
                    disabled={facePhase !== 'idle' || verifying || celebrating}
                    aria-label={t('privacy.unlock_face')}
                    aria-busy={facePhase === 'scanning'}
                    data-face-state={facePhase}
                    onClick={() => void faceUnlock()}
                  >
                    <motion.span
                      className="flex"
                      initial={false}
                      animate={
                        facePhase === 'scanning' && !reducedMotion
                          ? { scale: [1, 1.06, 1] }
                          : { scale: 1 }
                      }
                      transition={
                        facePhase === 'scanning' && !reducedMotion
                          ? { duration: 1.1, repeat: Infinity, ease: 'easeInOut' }
                          : { duration: 0.15 }
                      }
                    >
                      <ScanFace className="h-5 w-5" aria-hidden="true" />
                    </motion.span>
                  </button>
                  {facePhase === 'scanning' ? (
                    <span role="status" className="sr-only">
                      {t('privacy_lock.face_scanning', { defaultValue: '正在扫描人脸' })}
                    </span>
                  ) : null}
                </motion.div>
              ) : undefined
            }
          />
        </motion.div>

        {showFace ? (
          <motion.p
            className="mt-5 text-[13px] font-medium text-[var(--color-accent-foreground)]"
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{
              duration: lockSec(LOCK_ENTRANCE_MS.hint),
              delay: reducedMotion ? 0 : lockSec(LOCK_ENTRANCE_MS.hintDelay),
            }}
          >
            {facePhase === 'scanning' || facePhase === 'succeeded'
              ? t('privacy.face_verifying')
              : t('privacy.unlock_face')}
          </motion.p>
        ) : null}

        <motion.p
          className="mt-6 text-center text-[12px] text-[var(--color-text-muted)]"
          initial={reducedMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{
            duration: lockSec(LOCK_ENTRANCE_MS.hint),
            delay: reducedMotion ? 0 : lockSec(LOCK_ENTRANCE_MS.hintDelay),
          }}
        >
          {t('privacy.auto_lock_hint')}
        </motion.p>
      </div>
    </div>
  );
}
