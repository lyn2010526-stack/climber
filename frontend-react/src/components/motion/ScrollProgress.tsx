import { useEffect, useState } from 'react';
import type { CSSProperties, RefObject } from 'react';
import { measureScrollProgress, resolveScrollSegment } from './scrollProgressMath';
import { cn } from '../../lib/utils';

export interface ScrollProgressProps {
  containerRef?: RefObject<HTMLElement | null>;
  variant?: 'bar' | 'segments';
  segments?: number;
  className?: string;
  style?: CSSProperties;
  testId?: string;
  ariaLabel: string;
}

export function ScrollProgress({
  containerRef,
  variant = 'bar',
  segments = 5,
  className,
  style,
  testId,
  ariaLabel,
}: ScrollProgressProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const container = containerRef?.current ?? null;
    const scrollTarget: EventTarget = container ?? window;
    let frame: number | null = null;
    const measure = () => {
      frame = null;
      setProgress(measureScrollProgress(container ?? window));
    };
    const schedule = () => {
      if (frame !== null) return;
      frame = requestAnimationFrame(measure);
    };
    schedule();
    scrollTarget.addEventListener('scroll', schedule, { passive: true });
    let observer: ResizeObserver | undefined;
    if (container && typeof ResizeObserver === 'function') {
      observer = new ResizeObserver(schedule);
      observer.observe(container);
    }
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      scrollTarget.removeEventListener('scroll', schedule);
      observer?.disconnect();
    };
  }, [containerRef]);

  const percent = Math.round(progress * 100);

  if (variant === 'segments') {
    const activeIndex = resolveScrollSegment(progress, segments);
    return (
      <div
        role="progressbar"
        aria-label={ariaLabel}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        data-testid={testId}
        className={cn('flex items-center gap-[var(--space-1)]', className)}
        style={style}
      >
        {Array.from({ length: Math.max(1, Math.floor(segments)) }, (_, index) => (
          <span
            key={index}
            aria-hidden="true"
            data-state={index < activeIndex ? 'passed' : index === activeIndex ? 'active' : 'idle'}
            className={cn(
              'h-[3px] flex-1 rounded-full transition-colors',
              index < activeIndex && 'bg-[var(--color-accent-muted)]',
              index === activeIndex && 'bg-[var(--color-accent)]',
              index > activeIndex && 'bg-[var(--color-bg-surface-3)]',
            )}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      data-testid={testId}
      className={cn('h-[2px] w-full overflow-hidden bg-[var(--color-bg-surface-2)]', className)}
      style={style}
    >
      <span
        aria-hidden="true"
        className="block h-full w-full origin-left bg-[var(--color-accent)]"
        style={{ transform: `scaleX(${progress})` }}
      />
    </div>
  );
}
