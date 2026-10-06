import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useI18n } from '../../i18n';

export type PageTransitionVariant = 'overlay' | 'fade';
export type PageTransitionDirection = 'forward' | 'backward' | 'up' | 'down';

interface PageTransitionProps {
  children: React.ReactNode;
  transitionKey: string;
  variant?: PageTransitionVariant;
  direction?: PageTransitionDirection;
}

const pageVariants = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
};

const pageTransition = {
  duration: 0.22,
  ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
};

const MASK_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const MASK_COVER_S = 0.2;
const MASK_REVEAL_S = 0.24;

const OFFSCREEN: Record<PageTransitionDirection, { x: string; y: string }> = {
  forward: { x: '-101%', y: '0%' },
  backward: { x: '101%', y: '0%' },
  up: { x: '0%', y: '101%' },
  down: { x: '0%', y: '-101%' },
};

type MaskPhase = 'idle' | 'cover' | 'reveal';

function negateAxis(value: string): string {
  if (value === '0%') return value;
  return value.startsWith('-') ? value.slice(1) : `-${value}`;
}

function invertOffset(offset: { x: string; y: string }): { x: string; y: string } {
  return { x: negateAxis(offset.x), y: negateAxis(offset.y) };
}

export function PageTransition({
  children,
  transitionKey,
  variant = 'overlay',
  direction = 'forward',
}: PageTransitionProps) {
  const reducedMotion = useReducedMotion();
  const { t } = useI18n();
  const [displayKey, setDisplayKey] = useState(transitionKey);
  const [phase, setPhase] = useState<MaskPhase>('idle');
  const phaseRef = useRef<MaskPhase>('idle');
  const latestKeyRef = useRef(transitionKey);
  const frozenChildrenRef = useRef<React.ReactNode>(children);

  latestKeyRef.current = transitionKey;
  phaseRef.current = phase;
  const showingLatest = displayKey === transitionKey;
  if (showingLatest) {
    frozenChildrenRef.current = children;
  }

  useEffect(() => {
    if (variant === 'fade') return;
    if (transitionKey === displayKey) return;
    if (reducedMotion) {
      setDisplayKey(transitionKey);
      setPhase('idle');
      return;
    }
    setPhase('cover');
  }, [transitionKey, displayKey, reducedMotion, variant]);

  if (variant === 'fade') {
    if (reducedMotion) {
      return <div className="page-transition flex-1 overflow-hidden">{children}</div>;
    }
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={transitionKey}
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={pageTransition}
          className="page-transition flex-1 overflow-hidden"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    );
  }

  const home = OFFSCREEN[direction];
  const exitOffset = invertOffset(home);
  const maskTarget =
    phase === 'cover' ? { x: '0%', y: '0%' } : phase === 'reveal' ? exitOffset : home;

  const handleMaskComplete = () => {
    if (phaseRef.current === 'cover') {
      setDisplayKey(latestKeyRef.current);
      setPhase('reveal');
    } else if (phaseRef.current === 'reveal') {
      setPhase('idle');
    }
  };

  return (
    <div className="page-transition flex-1 overflow-hidden">
      {showingLatest ? children : frozenChildrenRef.current}
      <motion.div
        className="page-mask"
        data-state={phase}
        data-direction={direction}
        initial={false}
        animate={maskTarget}
        transition={
          phase === 'idle'
            ? { duration: 0 }
            : { duration: phase === 'cover' ? MASK_COVER_S : MASK_REVEAL_S, ease: MASK_EASE }
        }
        onAnimationComplete={handleMaskComplete}
        aria-hidden="true"
      />
      {phase !== 'idle' && (
        <span className="sr-only" role="status">
          {t('page_transition.status', { defaultValue: '正在切换页面' })}
        </span>
      )}
    </div>
  );
}
