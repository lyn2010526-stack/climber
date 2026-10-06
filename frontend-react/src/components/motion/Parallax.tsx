import { useEffect, useRef } from 'react';
import type { CSSProperties, ReactNode, RefObject } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { cn } from '../../lib/utils';

export interface ParallaxProps {
  children?: ReactNode;
  speed?: number;
  maxShift?: number;
  containerRef?: RefObject<HTMLElement | null>;
  className?: string;
  style?: CSSProperties;
  testId?: string;
  ariaHidden?: boolean;
}

function clampAbs(value: number, limit: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(limit, Math.max(-limit, value));
}

export function Parallax({
  children,
  speed = 0.2,
  maxShift = 40,
  containerRef,
  className,
  style,
  testId,
  ariaHidden,
}: ParallaxProps) {
  const reducedMotion = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (reducedMotion || speed === 0) return;
    const node = ref.current;
    if (!node) return;
    const container = containerRef?.current ?? null;
    const scrollTarget: EventTarget = container ?? window;
    let frame: number | null = null;
    const apply = () => {
      frame = null;
      const rect = node.getBoundingClientRect();
      const bounds = container
        ? container.getBoundingClientRect()
        : { top: 0, height: window.innerHeight || 0 };
      const viewportCenter = bounds.top + bounds.height / 2;
      const drift = clampAbs((rect.top + rect.height / 2 - viewportCenter) * speed, maxShift);
      node.style.transform = `translate3d(0, ${drift.toFixed(2)}px, 0)`;
    };
    const schedule = () => {
      if (frame !== null) return;
      frame = requestAnimationFrame(apply);
    };
    schedule();
    scrollTarget.addEventListener('scroll', schedule, { passive: true });
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      scrollTarget.removeEventListener('scroll', schedule);
      node.style.transform = '';
    };
  }, [reducedMotion, speed, maxShift, containerRef]);

  return (
    <div
      ref={ref}
      data-testid={testId}
      aria-hidden={ariaHidden || undefined}
      className={cn(className)}
      style={style}
    >
      {children}
    </div>
  );
}
