import { useCallback, useEffect, useRef, useState } from 'react';
import { ClimberMark } from '../brand/ClimberMark';
import { useI18n } from '../../i18n';
import { PIN_LENGTH } from '../../hooks/useAppLock';
import { PinDots, PinPad, PRIVACY_SHAKE_STYLE } from './LockScreen';

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

export function PinSetup({ onConfirm, onSkip }: PinSetupProps) {
  const { t } = useI18n();
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

  const stepText = firstPin === null ? t('privacy.pin_step_set') : t('privacy.pin_step_confirm');

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex flex-col items-center justify-center overflow-hidden px-6">
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
            {t('privacy.setup_title')}
          </h1>
          <p className="text-center text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
            {t('privacy.setup_subtitle')}
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

        <p className="mt-1 text-[14px] font-medium text-[var(--color-text-primary)]" role="status">
          {stepText}
        </p>

        <div className="mt-4">
          <PinPad onPress={press} onBackspace={backspace} disabled={submitting} />
        </div>

        {onSkip ? (
          <button
            type="button"
            className="mt-7 inline-flex min-h-[44px] items-center rounded-[var(--radius-pill)] px-5 text-[14px] font-medium text-[var(--color-text-muted)] transition-colors duration-150 hover:text-[var(--color-text-secondary)] active:opacity-80"
            onClick={onSkip}
          >
            {t('privacy.skip_setup')}
          </button>
        ) : null}
      </div>
    </div>
  );
}
