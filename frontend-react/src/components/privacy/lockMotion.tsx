import { motion } from 'framer-motion';
import { ClimberMark } from '../brand/ClimberMark';
import { LOCK_EASE, LOCK_ENTRANCE_MS, lockSec } from './lockTiming';

export interface LockBackdropProps {
  reducedMotion: boolean;
}

export function LockBackdrop({ reducedMotion }: LockBackdropProps) {
  const surface = 'absolute inset-0 bg-[var(--color-bg-page)]/80 backdrop-blur-2xl';
  if (reducedMotion) {
    return <div aria-hidden="true" className={surface} />;
  }
  return (
    <>
      <motion.div
        aria-hidden="true"
        className={surface}
        data-lock-item="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: lockSec(LOCK_ENTRANCE_MS.backdrop), ease: LOCK_EASE }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-1/2 flex justify-center"
      >
        <motion.div
          className="h-px w-[min(60vw,320px)] origin-center bg-[var(--color-accent)]"
          data-lock-item="reveal-line"
          style={{ boxShadow: '0 0 12px var(--color-accent-subtle)' }}
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: [0, 0.9, 0.9, 0] }}
          transition={{
            scaleX: {
              duration: lockSec(LOCK_ENTRANCE_MS.revealLine),
              delay: lockSec(LOCK_ENTRANCE_MS.revealLineDelay),
              ease: LOCK_EASE,
            },
            opacity: {
              duration: lockSec(LOCK_ENTRANCE_MS.revealFade),
              times: [0, 0.2, 0.55, 1],
              ease: 'easeOut',
            },
          }}
        />
      </div>
    </>
  );
}

export interface LockBrandProps {
  reducedMotion: boolean;
  title: string;
  subtitle: string;
  subtitleClassName?: string;
}

export function LockBrand({ reducedMotion, title, subtitle, subtitleClassName }: LockBrandProps) {
  const instant = reducedMotion;
  return (
    <div className="flex flex-col items-center gap-2">
      <motion.span
        className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/70 shadow-[var(--shadow-panel)]"
        data-lock-item="brand"
        initial={instant ? false : { scale: 0.92, opacity: 0 }}
        animate={
          instant
            ? { scale: 1, opacity: 1 }
            : { scale: [0.92, LOCK_ENTRANCE_MS.brandOvershoot, 1], opacity: 1 }
        }
        transition={{
          duration: lockSec(LOCK_ENTRANCE_MS.brandSpring),
          times: [0, 0.62, 1],
          delay: instant ? 0 : lockSec(LOCK_ENTRANCE_MS.brandDelay),
          ease: LOCK_EASE,
        }}
      >
        <ClimberMark size={30} color="var(--color-accent-foreground)" />
      </motion.span>
      <motion.h1
        className="mt-2 text-[17px] font-semibold tracking-tight text-[var(--color-text-primary)]"
        initial={instant ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: lockSec(LOCK_ENTRANCE_MS.title),
          delay: instant ? 0 : lockSec(LOCK_ENTRANCE_MS.titleDelay),
          ease: LOCK_EASE,
        }}
      >
        {title}
      </motion.h1>
      <motion.p
        className={subtitleClassName ?? 'text-[13px] text-[var(--color-text-secondary)]'}
        initial={instant ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: lockSec(LOCK_ENTRANCE_MS.subtitle),
          delay: instant ? 0 : lockSec(LOCK_ENTRANCE_MS.subtitleDelay),
          ease: LOCK_EASE,
        }}
      >
        {subtitle}
      </motion.p>
    </div>
  );
}
