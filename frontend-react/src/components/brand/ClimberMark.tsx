/**
 * Single source of truth for the Climber mark geometry.
 *
 * Everything that has to draw the mark (the React component, `favicon.svg` and
 * the PWA icon set) is generated from these numbers, so the favicon and the
 * in-app logo stay one drawing instead of two that drift apart.
 *
 * Grid and optical decisions, on a 24-unit viewBox:
 * - The ridge is a single four-point polyline, so there is exactly one contour
 *   to read: down-left foot, two rungs, a shoulder, and a rise to the summit.
 *   Ink spans x 3.73-20.28 and y 2.83-20.78, which leaves 3.7 units of side
 *   padding and roughly 2.8/3.2 top/bottom padding, so the mark sits centred
 *   instead of hugging a corner.
 * - The summit is a stroked circle of the same weight as the ridge. Sharing the
 *   weight keeps the two forms one mark, and a circle has no corner to go soft
 *   at 14px the way a rounded rect does.
 * - The 1.68-unit gap between the last ridge vertex and the circle edge is
 *   deliberate. It stays a visible hairline at 14px (0.98px at 16px) and reads
 *   as "route aimed at summit" rather than "line touching a blob" at 20px+.
 * - Round caps and round joins keep every vertex the same visual thickness; a
 *   miter join would spike the two acute descents when a caller raises the
 *   stroke weight.
 */
export const CLIMBER_MARK = {
  viewBox: '0 0 24 24',
  /** Ascent polyline: foot, rung, shoulder, rise. */
  ridge: '4.6 19.9 9.9 13.9 7.2 10.2 11.7 7.1',
  /** Summit node, aimed at by the ridge. */
  node: { cx: 17.2, cy: 5.9, r: 2.2 },
  /**
   * Optical weight for the 24-unit grid. A full 2px stroke closes the summit
   * gap and turns the two rungs into one mass at the 15px mobile rung and the
   * 16px desktop shell, so the default runs lighter and callers raise it.
   */
  strokeWidth: 1.75,
} as const;

export interface ClimberMarkProps {
  size?: number;
  className?: string;
  /**
   * Defaults to `currentColor` so the mark inherits the surrounding text
   * colour. Pass a token reference such as `var(--color-accent)` to tint it;
   * colour literals in this file would break the style gate.
   */
  color?: string;
  strokeWidth?: number;
}

/**
 * Product mark: a climbing route that gains height, plus the summit node it is
 * aimed at. Two shapes only, because the mark is drawn at 15px in the mobile
 * context bar and 16px in the desktop shell.
 *
 * Stroked with `currentColor` on a 24-unit grid with round caps and joins, so
 * it needs no fill, no gradient, no per-theme variant and no hardcoded colour.
 */
export function ClimberMark({
  size = 16,
  className,
  color = 'currentColor',
  strokeWidth = CLIMBER_MARK.strokeWidth,
}: ClimberMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox={CLIMBER_MARK.viewBox}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <polyline points={CLIMBER_MARK.ridge} />
      <circle cx={CLIMBER_MARK.node.cx} cy={CLIMBER_MARK.node.cy} r={CLIMBER_MARK.node.r} />
    </svg>
  );
}
