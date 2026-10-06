import { Children, cloneElement, isValidElement, useEffect, useRef, useState } from 'react';
import type { CSSProperties, ReactElement, ReactNode } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { cn } from '../../lib/utils';

export type ScrollRevealDirection = 'up' | 'down' | 'left' | 'right';

export interface ScrollRevealProps {
  children: ReactNode;
  once?: boolean;
  offset?: string;
  duration?: number;
  delay?: number;
  ease?: string;
  stagger?: number;
  distance?: number;
  direction?: ScrollRevealDirection;
  className?: string;
  style?: CSSProperties;
  testId?: string;
}

const DEFAULT_OFFSET = '0px 0px -10% 0px';
const DEFAULT_EASE = 'var(--ease-spring)';

interface RevealTiming {
  duration: number;
  delay: number;
  ease: string;
  distance: number;
  direction: ScrollRevealDirection;
}

function hiddenTransform({ direction, distance }: RevealTiming): string {
  switch (direction) {
    case 'down':
      return `translate3d(0, -${distance}px, 0)`;
    case 'left':
      return `translate3d(${distance}px, 0, 0)`;
    case 'right':
      return `translate3d(-${distance}px, 0, 0)`;
    default:
      return `translate3d(0, ${distance}px, 0)`;
  }
}

function revealStyle(revealed: boolean, timing: RevealTiming): CSSProperties {
  const transition = `opacity ${timing.duration}ms ${timing.ease} ${timing.delay}ms, transform ${timing.duration}ms ${timing.ease} ${timing.delay}ms`;
  if (revealed) {
    return { opacity: 1, transform: 'none', transition };
  }
  return { opacity: 0, transform: hiddenTransform(timing), transition };
}

export function ScrollReveal({
  children,
  once = true,
  offset = DEFAULT_OFFSET,
  duration = 480,
  delay = 0,
  ease = DEFAULT_EASE,
  stagger = 0,
  distance = 16,
  direction = 'up',
  className,
  style,
  testId,
}: ScrollRevealProps) {
  const reducedMotion = usePrefersReducedMotion();
  const observerSupported = typeof window !== 'undefined' && typeof IntersectionObserver === 'function';
  const active = !reducedMotion && observerSupported;
  const ref = useRef<HTMLDivElement | null>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            if (once) {
              observer.disconnect();
              break;
            }
          } else if (!once) {
            setRevealed(false);
          }
        }
      },
      { rootMargin: offset, threshold: 0 },
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
    };
  }, [active, once, offset]);

  if (!active) {
    return (
      <div ref={ref} data-testid={testId} className={className} style={style}>
        {children}
      </div>
    );
  }

  const timing: RevealTiming = { duration, delay, ease, distance, direction };

  if (stagger > 0) {
    let itemIndex = -1;
    const items = Children.toArray(children).map((child) => {
      if (!isValidElement(child)) return child;
      itemIndex += 1;
      const item = child as ReactElement<{ style?: CSSProperties }>;
      const itemDelay = delay + itemIndex * stagger;
      return cloneElement(item, {
        style: {
          ...item.props.style,
          ...revealStyle(revealed, timing),
          transitionDelay: `${itemDelay}ms`,
        },
      });
    });
    return (
      <div ref={ref} data-testid={testId} className={cn(className)} style={style}>
        {items}
      </div>
    );
  }

  return (
    <div
      ref={ref}
      data-testid={testId}
      className={cn(className)}
      style={{ ...style, ...revealStyle(revealed, timing) }}
    >
      {children}
    </div>
  );
}
