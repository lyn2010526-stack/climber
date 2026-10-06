import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useI18n } from '../../i18n';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { PIN_LENGTH } from '../../hooks/useAppLock';
import { PinDots, PinPad, PRIVACY_SHAKE_STYLE } from './LockScreen';
import { LOCK_EASE, LOCK_ENTRANCE_MS, lockSec } from './lockTiming';
import { LockBackdrop, LockBrand } from './lockMotion';

/**
 * First-run passcode enrollment: enter the six digits twice, mismatches shake
 * and restart, and the whole step can be skipped (the privacy lock then stays
 * off until the user opts in from settings).
 */
export interface PinSetupProps {
  /** Called once both entries match. Resolve `false` to surface a failure. */
  onConfirm: (pin: string) => boolean | Promise<boolean>;
  /** Optional opt-out; when absent the skip action is hidden. */
  onSkip?: () => void;
}

const SHAKE_RESET_MS = 480;
const STEP_EXIT_MS = 100;
const STEP_ENTER_MS = 120;

/**
 * Enter/exit timings for the animated step swap. Held as a hoisted constant so
 * the per-value `exit` override survives structural assignability to
 * framer-motion's `Transition` (excess properties are only rejected on inline
 * literals); the runtime transition resolution is unchanged either way.
 */
const STEP_TRANSITION = {
  duration: lockSec(STEP_ENTER_MS),
  ease: LOCK_EASE,
  exit: { duration: lockSec(STEP_EXIT_MS), ease: LOCK_EASE },
};

export function PinSetup({ onConfirm, onSkip }: PinSetupProps) {
  const { t } = useI18n();
  const reducedMotion = usePrefersReducedMotion();
  const [firstPin, setFirstPin] = useState<string | null>(null);
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const shakeTimer = useRef<number | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (shakeTimer.current !== null) window.clearTimeout(shakeTimer.current);
    };
  }, []);

  const fail = useCallback((message: string) => {
    setError(message);
    setShaking(true);
    if (shakeTimer.current !== null) window.clearTimeout(shakeTimer.current);
    shakeTimer.current = window.setTimeout(() => {
      if (mounted.current) setShaking(false);
    }, SHAKE_RESET_MS);
  }, []);

  const advance = useCallback(
    async (candidate: string) => {
      if (firstPin === null) {
        setFirstPin(candidate);
        setPin('');
        setError(null);
        return;
      }
      if (candidate !== firstPin) {
        setFirstPin(null);
        setPin('');
        fail(t('privacy.pin_mismatch'));
        return;
      }
      setSubmitting(true);
      let ok: boolean;
      try {
        ok = await onConfirm(candidate);
      } catch {
        ok = false;
      }
      if (mounted.current) setSubmitting(false);
      if (ok === false) {
        setFirstPin(null);
        setPin('');
        if (mounted.current) fail(t('privacy.pin_failed'));
      }
    },
    [firstPin, onConfirm, t, fail],
  );

  const press = useCallback(
    (digit: string) => {
      if (submitting || pin.length >= PIN_LENGTH) return;
      setError(null);
      const next = `${pin}${digit}`;
      setPin(next);
      if (next.length === PIN_LENGTH) void advance(next);
    },
    [submitting, pin, advance],
  );

  const backspace = useCallback(() => {
    if (submitting) return;
    setError(null);
    setPin((prev) => prev.slice(0, -1));
  }, [submitting]);

  const step = firstPin === null ? 'set' : 'confirm';
  const stepText = firstPin === null ? t('privacy.pin_step_set') : t('privacy.pin_step_confirm');

  const stage = (
    <>
      <PinDots count={pin.length} error={Boolean(error)} />
      <p
        className="mt-3 h-5 text-center text-[13px] text-[var(--color-error)]"
        data-testid="pin-error"
        role="alert"
      >
        {error}
      </p>
      <p className="mt-1 text-[14px] font-medium text-[var(--color-text-primary)]" role="status">
        {stepText}
      </p>
    </>
  );

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex flex-col items-center justify-center overflow-hidden px-6"
      data-lock-intro={reducedMotion ? 'instant' : 'play'}
    >
      <style>{PRIVACY_SHAKE_STYLE}</style>
      <LockBackdrop reducedMotion={reducedMotion} />
      <div className="relative flex w-full max-w-xs flex-col items-center">
        <LockBrand
          reducedMotion={reducedMotion}
          title={t('privacy.setup_title')}
          subtitle={t('privacy.setup_subtitle')}
          subtitleClassName="text-center text-[13px] leading-relaxed text-[var(--color-text-secondary)]"
        />

        <div
          className={`mt-7 flex flex-col items-center ${shaking ? 'privacy-lock-shake' : ''}`}
          data-shake={shaking ? 'true' : undefined}
          aria-live="polite"
        >
          {reducedMotion ? (
            <div className="flex flex-col items-center" data-lock-step={step}>
              {stage}
            </div>
          ) : (
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={step}
                className="flex flex-col items-center"
                data-lock-step={step}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={STEP_TRANSITION}
              >
                {stage}
              </motion.div>
            </AnimatePresence>
          )}
        </div>

        <motion.div
          className="mt-4"
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
            disabled={submitting}
            error={Boolean(error)}
          />
        </motion.div>

        {onSkip ? (
          <motion.button
            type="button"
            className="mt-7 inline-flex min-h-[44px] items-center rounded-[var(--radius-pill)] px-5 text-[14px] font-medium text-[var(--color-text-muted)] transition-colors duration-150 hover:text-[var(--color-text-secondary)] active:opacity-80"
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{
              duration: lockSec(LOCK_ENTRANCE_MS.hint),
              delay: reducedMotion ? 0 : lockSec(LOCK_ENTRANCE_MS.faceDelay),
            }}
            onClick={onSkip}
          >
            {t('privacy.skip_setup')}
          </motion.button>
        ) : null}
      </div>
    </div>
  );
}
