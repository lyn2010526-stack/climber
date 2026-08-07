import React from 'react';
import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animated?: boolean;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'text',
  width,
  height,
  animated = true,
}) => {
  const variantClasses = {
    text: 'h-4 rounded-lg',
    circular: 'rounded-full',
    rectangular: 'rounded-none',
    rounded: 'rounded-xl',
  };

  return (
    <div
      className={cn(
        'bg-gradient-to-r from-[var(--color-bg-surface-2)] via-[var(--color-bg-surface-3)] to-[var(--color-bg-surface-2)] bg-[length:200%_100%]',
        variantClasses[variant],
        animated && 'animate-[shimmer_1.5s_ease-in-out_infinite]',
        className
      )}
      style={{ width, height }}
    />
  );
};

interface SkeletonGroupProps {
  count?: number;
  className?: string;
}

export const SkeletonText: React.FC<SkeletonGroupProps> = ({ count = 3, className }) => (
  <div className={cn('space-y-3', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} className={i === count - 1 ? 'w-3/4' : 'w-full'} />
    ))}
  </div>
);

export const SkeletonCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn(
    'p-5 rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]',
    'shadow-[0_1px_2px_rgba(0,0,0,0.05)]',
    className
  )}>
    <div className="flex items-center gap-4">
      <Skeleton variant="circular" width={40} height={40} />
      <div className="flex-1 space-y-2">
        <Skeleton className="w-32" />
        <Skeleton className="w-48" />
      </div>
    </div>
    <div className="mt-4">
      <SkeletonText count={2} />
    </div>
  </div>
);

export const SkeletonList: React.FC<{ count?: number; className?: string }> = ({ count = 3, className }) => (
  <div className={cn('space-y-3', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <SkeletonCard key={i} />
    ))}
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; cols?: number; className?: string }> = ({ rows = 5, cols = 4, className }) => (
  <div className={cn('space-y-2', className)}>
    <div className="flex gap-3">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-4 flex-1" />
      ))}
    </div>
    {Array.from({ length: rows }).map((_, rowIdx) => (
      <div key={rowIdx} className="flex gap-3">
        {Array.from({ length: cols }).map((_, colIdx) => (
          <Skeleton key={colIdx} className="h-3 flex-1" />
        ))}
      </div>
    ))}
  </div>
);

export default Skeleton;
