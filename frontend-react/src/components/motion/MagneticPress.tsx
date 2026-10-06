import { useCallback, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

/** How far the control leans, as a fraction of its own half-box. */
const PULL_RATIO = 0.16;
/** Absolute ceiling on the lean, so a wide CTA cannot travel further than a narrow one. */
const MAX_PULL_PX = 5;
/** The press sinks the whole control; the fill compresses separately underneath it. */
const PRESS_PX = 1;
/** One settle for the pull, the return and the press alike. */
const SETTLE_MS = 150;
const SETTLE_CURVE = 'cubic-bezier(0.16, 1, 0.3, 1)';

export interface MagneticPressProps {
  children: ReactNode;
  className?: string;
  /** A locked control stays still: nothing about it should invite a press. */
  disabled?: boolean;
}

const clampUnit = (value: number) => Math.max(-1, Math.min(1, value));

/**
 * The CTA micro-interaction: a control that leans toward the pointer and sinks
 * a pixel on the press.
 *
 * Both halves are transform-only and both settle in the same 150ms, so the pull
 * and the return read as one physical object instead of two effects. The pull is
 * clamped in pixels rather than as a percentage of the box, because a wide CTA
 * must not drift further than a narrow one — the gesture is a lean, not a slide.
 *
 * It wraps the control instead of restyling it: `Button` already owns its press
 * compression through `.press-scale`, and keeping the two transforms on separate
 * elements lets them compose instead of overwriting each other. The wrapper is a
 * plain span rather than a motion component so it cannot pick up the variant
 * propagation of the staggered container it is mounted inside.
 */
export function MagneticPress({ children, className, disabled = false }: MagneticPressProps) {
  const reducedMotion = usePrefersReducedMotion();
  const [pull, setPull] = useState({ x: 0, y: 0 });
  const [pressed, setPressed] = useState(false);
  const active = !reducedMotion && !disabled;

  const handlePointerMove = useCallback((event: ReactPointerEvent<HTMLSpanElement>) => {
    // A touch drag is a scroll gesture: leaning toward a finger would fight the
    // surface the finger is already moving.
    if (event.pointerType !== 'mouse') return;
    const box = event.currentTarget.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return;
    const halfWidth = box.width / 2;
    const halfHeight = box.height / 2;
    const limitX = Math.min(MAX_PULL_PX, halfWidth * PULL_RATIO);
    const limitY = Math.min(MAX_PULL_PX, halfHeight * PULL_RATIO);
    // Rounded to whole pixels so a slow drag cannot re-render on every event.
    const next = {
      x: Math.round(clampUnit((event.clientX - (box.left + halfWidth)) / halfWidth) * limitX),
      y: Math.round(clampUnit((event.clientY - (box.top + halfHeight)) / halfHeight) * limitY),
    };
    setPull((current) => (current.x === next.x && current.y === next.y ? current : next));
  }, []);

  const release = useCallback(() => {
    setPull({ x: 0, y: 0 });
    setPressed(false);
  }, []);

  const lift = pressed ? PRESS_PX : 0;
  const x = active ? pull.x : 0;
  const y = active ? pull.y + lift : 0;

  return (
    <span
      className={className ? `inline-flex ${className}` : 'inline-flex'}
      data-magnetic={active ? 'on' : 'off'}
      data-pressed={pressed ? 'true' : 'false'}
      data-pull={`${x},${y}`}
      style={{
        transform: `translate3d(${x}px, ${y}px, 0)`,
        transition: active ? `transform ${SETTLE_MS}ms ${SETTLE_CURVE}` : undefined,
      }}
      onPointerMove={active ? handlePointerMove : undefined}
      onPointerDown={active ? () => setPressed(true) : undefined}
      onPointerUp={active ? () => setPressed(false) : undefined}
      onPointerLeave={active ? release : undefined}
      onPointerCancel={active ? release : undefined}
    >
      {children}
    </span>
  );
}

export default MagneticPress;
