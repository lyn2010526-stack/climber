import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: number | string;
  height?: number | string;
  lines?: number;
  animated?: boolean;
}

const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = 'text', width, height, lines = 1, animated = true, ...props }, ref) => {
    const variantStyles = {
      text: 'h-4 rounded-md',
      circular: 'rounded-full',
      rectangular: 'rounded-none',
      rounded: 'rounded-xl',
    };

    const style: React.CSSProperties = {
      width: width || '100%',
      height: height || undefined,
    };

    if (lines > 1) {
      return (
        <div ref={ref} className={cn('space-y-2.5', className)} {...props}>
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className={cn(
                'bg-[var(--color-bg-surface-3)]',
                variantStyles[variant],
                animated && 'animate-pulse',
              )}
              style={{
                ...style,
                width: i === lines - 1 ? '75%' : style.width,
              }}
            />
          ))}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          'bg-[var(--color-bg-surface-3)]',
          variantStyles[variant],
          animated && 'animate-pulse',
          className,
        )}
        style={style}
        {...props}
      />
    );
  }
);
Skeleton.displayName = 'Skeleton';

interface SkeletonGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  loading?: boolean;
}

const SkeletonGroup = forwardRef<HTMLDivElement, SkeletonGroupProps>(
  ({ children, loading = true, className, ...props }, ref) => {
    if (!loading) return <>{children}</>;

    return (
      <div ref={ref} className={cn('pointer-events-none', className)} {...props}>
        {children}
      </div>
    );
  }
);
SkeletonGroup.displayName = 'SkeletonGroup';

export { Skeleton, SkeletonGroup };
export type { SkeletonProps, SkeletonGroupProps };
