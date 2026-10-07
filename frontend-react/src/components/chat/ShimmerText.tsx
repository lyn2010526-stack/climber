import { cn } from '../../lib/utils';

/** Animated text highlight that becomes static when reduced motion is enabled. */
export interface ShimmerTextProps {
  text: string;
  className?: string;
}

export function ShimmerText({ text, className }: ShimmerTextProps) {
  if (text.length === 0) return null;
  return (
    <span className={cn('workbench-shimmer-text', className)}>{text}</span>
  );
}
