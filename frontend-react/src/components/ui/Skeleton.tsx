import React from 'react';
import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animated?: boolean;
}

/**
 * A placeholder is a hole in the layout, not a decoration, so the shimmer is
 * built from the surface ramp alone.
 *
 * The design system bans every colour ramp, and a sweeping highlight would
 * break that rule to solve a problem two flat planes already solve: a lit
 * surface-2 plane pulsing in and out over a sunk surface-3 plane underneath.
 * The output alternates between those two steps and holds a constant tone,
 * because no ramp takes part in the construction at all. `overflow-hidden` on
 * the root clips the lit plane to whatever radius the variant asked for.
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'text',
  width,
  height,
  animated = true,
}) => {
  const variantClasses = {
    text: 'h-[var(--space-4)] rounded-[var(--radius-sm)]',
    circular: 'rounded-[var(--radius-pill)]',
    rectangular: 'rounded-none',
    rounded: 'rounded-[var(--radius-md)]',
  };

  return (
    <div
      aria-hidden="true"
      className={cn('relative overflow-hidden', variantClasses[variant], className)}
      style={{ width, height }}
    >
      <span className="absolute inset-0 bg-[var(--color-bg-surface-3)]" />
      {animated && <span className="absolute inset-0 animate-pulse bg-[var(--color-bg-surface-2)] motion-reduce:animate-none" />}
    </div>
  );
};

interface SkeletonGroupProps {
  count?: number;
  className?: string;
}

export const SkeletonText: React.FC<SkeletonGroupProps> = ({ count = 3, className }) => (
  <div className={cn('space-y-[var(--space-3)]', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} className={i === count - 1 ? 'w-3/4' : 'w-full'} />
    ))}
  </div>
);

export const SkeletonCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn(
    'rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-[var(--space-4)]',
    className
  )}>
    <div className="flex items-center gap-[var(--space-4)]">
      <Skeleton variant="circular" width={40} height={40} />
      <div className="flex-1 space-y-[var(--space-2)]">
        <Skeleton className="w-32" />
        <Skeleton className="w-48" />
      </div>
    </div>
    <div className="mt-[var(--space-4)]">
      <SkeletonText count={2} />
    </div>
  </div>
);

export const SkeletonList: React.FC<{ count?: number; className?: string }> = ({ count = 3, className }) => (
  <div className={cn('space-y-[var(--space-3)]', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <SkeletonCard key={i} />
    ))}
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; cols?: number; className?: string }> = ({ rows = 5, cols = 4, className }) => (
  <div className={cn('space-y-[var(--space-2)]', className)}>
    <div className="flex gap-[var(--space-3)]">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-[var(--space-4)] flex-1" />
      ))}
    </div>
    {Array.from({ length: rows }).map((_, rowIdx) => (
      <div key={rowIdx} className="flex gap-[var(--space-3)]">
        {Array.from({ length: cols }).map((_, colIdx) => (
          <Skeleton key={colIdx} className="h-[var(--space-3)] flex-1" />
        ))}
      </div>
    ))}
  </div>
);

export default Skeleton;
