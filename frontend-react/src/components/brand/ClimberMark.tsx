/** Shared ascent geometry; keep public/favicon.svg in sync. */
export const CLIMBER_MARK = {
  viewBox: '0 0 24 24',
  ridge: '4.6 19.9 9.9 13.9 7.2 10.2 11.7 7.1',
  node: { cx: 17.2, cy: 5.9, r: 2.2 },
  strokeWidth: 1.75,
} as const;

export interface ClimberMarkProps {
  size?: number;
  className?: string;
  color?: string;
  strokeWidth?: number;
}

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
