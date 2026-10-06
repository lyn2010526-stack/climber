import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ClimberMark } from '../brand/ClimberMark';
import { hasSeenBootSession, markBootSessionSeen } from '../motion/bootSession';
import { announceBootPhase } from '../motion/bootHandoff';
import { BOOT_SPLASH_WINDOW } from '../motion/bootTiming';
import { useI18n } from '../../i18n';

export interface BootSplashProps {
  onDone?: () => void;
}

export function BootSplash({ onDone }: BootSplashProps) {
  const { t } = useI18n();
  const [seenBefore] = useState(hasSeenBootSession);
  const [leaving, setLeaving] = useState(false);
  const doneRef = useRef(false);
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  });

  // Claim the screen before any passive effect below it can run. The app is
  // already mounted underneath the curtain, so a layout effect is the only
  // point where the surfaces waiting on the hand-off are guaranteed to hear
  // `holding` before they decide to start their own entrance.
  useLayoutEffect(() => {
    announceBootPhase('holding');
    return () => announceBootPhase('settled');
  }, []);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const timing = reduced
      ? BOOT_SPLASH_WINDOW.reduced
      : seenBefore
        ? BOOT_SPLASH_WINDOW.quick
        : BOOT_SPLASH_WINDOW.first;
    const leaveTimer = window.setTimeout(() => {
      setLeaving(true);
      // The curtain starts to lift on this frame, which is when the app below
      // should spend its entrance rather than after the lift has finished.
      announceBootPhase('revealing');
    }, timing.enter);
    const doneTimer = window.setTimeout(() => {
      if (doneRef.current) return;
      doneRef.current = true;
      markBootSessionSeen();
      onDoneRef.current?.();
    }, timing.enter + timing.exit);
    return () => {
      window.clearTimeout(leaveTimer);
      window.clearTimeout(doneTimer);
    };
  }, [seenBefore]);

  const className = [
    'boot-splash',
    seenBefore ? 'boot-splash-quick' : 'boot-splash-first',
    leaving ? 'boot-splash-exit' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      role="status"
      aria-label={t('boot.loading', { defaultValue: '正在启动 Climber' })}
      className={className}
      data-boot-phase={leaving ? 'revealing' : 'holding'}
    >
      <span className="boot-splash-texture" aria-hidden="true" />
      <span className="boot-splash-mark" aria-hidden="true">
        <ClimberMark size={seenBefore ? 40 : 64} color="var(--color-accent-foreground)" />
      </span>
      {seenBefore ? null : (
        <>
          <span className="boot-splash-name">Climber</span>
          <span className="boot-splash-bar" aria-hidden="true" />
          <span className="boot-splash-tagline">
            {t('boot.tagline', { defaultValue: '正在准备工作区' })}
          </span>
        </>
      )}
    </div>
  );
}

export default BootSplash;
