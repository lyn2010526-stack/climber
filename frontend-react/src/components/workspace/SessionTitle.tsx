import { useEffect, useRef, useState } from 'react';

/** Sideways travel speed; the duration follows from the measured overflow. */
const TITLE_SPEED_PX_PER_SECOND = 30;
/** Time the title sits still before it starts, so a glance costs nothing. */
const TITLE_START_DELAY_MS = 600;
/** Time it rests at the end before travelling back. */
const TITLE_HOLD_MS = 2000;
/** How long the trailing fade takes to arrive, as a share of the travel. */
const TITLE_REVEAL_RATIO = 0.35;
/** Below this width the sidebar is too narrow for a marquee to read. */
const TITLE_MIN_VIEWPORT_PX = 160;

interface SessionTitleProps {
  title: string;
  /** Whether the row is hovered or the title itself is focused. */
  active: boolean;
  className?: string;
}

/** Legacy engines expose only `addListener` on MediaQueryList. */
function observeMediaQuery(query: MediaQueryList, onChange: () => void): () => void {
  if (typeof query.addEventListener === 'function') {
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }
  query.addListener(onChange);
  return () => query.removeListener(onChange);
}

/**
 * A session title that travels sideways when the sidebar is too narrow to show
 * it whole.
 *
 * The overflow is measured rather than assumed: the viewport and the text are
 * both measured, because a title that fits reports no overflow even in a narrow
 * sidebar, and one that does not has to be told. Three conditions end the
 * animation — the row is not hovered, the viewport is too small to read a
 * moving title, and the reader asked for reduced motion — and none of them is
 * checked before the measurement, so a title that fits starts nothing.
 */
export function SessionTitle({ title, active, className = '' }: SessionTitleProps) {
  const [isOverflowing, setIsOverflowing] = useState(false);
  const viewportRef = useRef<HTMLSpanElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const viewport = viewportRef.current;
    const text = textRef.current;
    if (!viewport || !text) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let animation: Animation | undefined;
    let frame = 0;

    const start = () => {
      animation?.cancel();
      cancelAnimationFrame(frame);
      delete viewport.dataset.titleRevealed;
      const overflow = text.getBoundingClientRect().width - viewport.getBoundingClientRect().width;
      setIsOverflowing(overflow > 0);
      const tooNarrow = viewport.getBoundingClientRect().width < TITLE_MIN_VIEWPORT_PX;
      if (!active || tooNarrow || reducedMotion.matches || overflow <= 0) return;
      // Web Animations is the only engine that can animate a transform here, and
      // it is absent in the test environment where every measurement is zero.
      if (typeof text.animate !== 'function') return;

      const direction = getComputedStyle(viewport).direction === 'rtl' ? 1 : -1;
      const travelDuration = (overflow / TITLE_SPEED_PX_PER_SECOND) * 1000;
      const duration = travelDuration + TITLE_HOLD_MS;
      const end = `translateX(${direction * overflow}px)`;

      animation = text.animate(
        [
          { transform: 'translateX(0)' },
          { transform: end, offset: travelDuration / duration },
          { transform: end },
        ],
        { duration, delay: TITLE_START_DELAY_MS, iterations: Infinity, easing: 'linear' },
      );

      // The fade retreats as the ending arrives, so the last characters read
      // clearly without the text overscrolling past the available width.
      const revealFrom = Math.max(0, travelDuration * (1 - TITLE_REVEAL_RATIO));
      const tick = () => {
        const currentTime = typeof animation?.currentTime === 'number' ? animation.currentTime : 0;
        const elapsed = currentTime - TITLE_START_DELAY_MS;
        viewport.dataset.titleRevealed = String(elapsed > 0 && elapsed % duration >= revealFrom);
        frame = requestAnimationFrame(tick);
      };
      tick();
    };

    const observer = new ResizeObserver(start);
    observer.observe(viewport);
    observer.observe(text);
    const unobserveMediaQuery = observeMediaQuery(reducedMotion, start);
    start();

    return () => {
      observer.disconnect();
      unobserveMediaQuery();
      animation?.cancel();
      cancelAnimationFrame(frame);
      delete viewport.dataset.titleRevealed;
    };
  }, [active, title]);

  return (
    <span
      ref={viewportRef}
      title={title}
      className={`min-w-0 flex-1 overflow-hidden whitespace-nowrap [--session-title-fade-width:20px] [--session-title-reveal-duration:600ms] [mask-position:left] [mask-repeat:no-repeat] [mask-size:100%_100%] [text-align:start] [transition-duration:0ms] [transition-property:mask-size] [transition-timing-function:linear] [&:dir(rtl)]:[mask-position:right] ${
        isOverflowing
          ? '[mask-image:linear-gradient(to_right,currentColor_calc(100%_-_var(--session-title-fade-width)),transparent)] [&:dir(rtl)]:[mask-image:linear-gradient(to_left,currentColor_calc(100%_-_var(--session-title-fade-width)),transparent)]'
          : ''
      } data-[title-revealed=true]:[mask-size:calc(100%_+_var(--session-title-fade-width))_100%] data-[title-revealed=true]:[transition-duration:var(--session-title-reveal-duration)] ${className}`}
    >
      <span ref={textRef} className="inline-block">
        {title}
      </span>
    </span>
  );
}
