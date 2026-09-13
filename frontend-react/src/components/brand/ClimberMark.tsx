export interface ClimberMarkProps {
  size?: number;
  className?: string;
  color?: string;
}

export function ClimberMark({ size = 16, className, color = 'currentColor' }: ClimberMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <polyline points="4 20 10 15 7 9 13.5 5" />
      <rect x="14.75" y="2" width="6" height="6" rx="1.25" />
    </svg>
  );
}
