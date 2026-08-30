import { forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const progressVariants = cva(
  'relative w-full overflow-hidden rounded-full bg-[var(--color-bg-surface-3)]',
  {
    variants: {
      size: {
        sm: 'h-1',
        md: 'h-2',
        lg: 'h-3',
        xl: 'h-4',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

const progressBarVariants = cva(
  'h-full rounded-full transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
  {
    variants: {
      variant: {
        default: 'bg-gradient-to-r from-blue-500 to-violet-500',
        success: 'bg-gradient-to-r from-emerald-500 to-teal-500',
        warning: 'bg-gradient-to-r from-amber-500 to-orange-500',
        error: 'bg-gradient-to-r from-red-500 to-rose-500',
        info: 'bg-gradient-to-r from-sky-500 to-cyan-500',
      },
      animated: {
        true: 'relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:animate-[shimmer_2s_infinite]',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      animated: false,
    },
  }
);

interface ProgressProps {
  value: number;
  max?: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  showValue?: boolean;
  label?: string;
  animated?: boolean;
  striped?: boolean;
}

const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ value, max = 100, className, size, variant, showValue, label, animated = false, striped = false }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
      <div ref={ref} className={cn('w-full', className)}>
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-1.5">
            {label && <span className="text-xs text-[var(--color-text-secondary)]">{label}</span>}
            {showValue && <span className="text-xs text-[var(--color-text-secondary)] font-medium">{Math.round(percentage)}%</span>}
          </div>
        )}
        <div className={cn(progressVariants({ size }))} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label={label || '进度'}>
          <div
            className={cn(
              progressBarVariants({ variant, animated }),
              striped && 'bg-[length:1rem_1rem] bg-[linear-gradient(45deg,rgba(255,255,255,0.1)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.1)_50%,rgba(255,255,255,0.1)_75%,transparent_75%,transparent)]',
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }
);
Progress.displayName = 'Progress';

interface CircularProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  showValue?: boolean;
}

const CircularProgress = forwardRef<SVGSVGElement, CircularProgressProps>(
  ({ value, max = 100, size = 60, strokeWidth = 4, className, variant = 'default', showValue }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    const colorMap: Record<string, string> = {
      default: 'var(--color-accent)',
      success: 'var(--color-success)',
      warning: 'var(--color-warning)',
      error: 'var(--color-error)',
      info: 'var(--color-accent-secondary)',
    };

    return (
      <div className={cn('relative inline-flex items-center justify-center', className)} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label="进度">
         <svg ref={ref} width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--color-border-strong)"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colorMap[variant]}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
          />
        </svg>
        {showValue && (
          <span className="absolute text-xs font-medium text-[var(--color-text-secondary)]">
            {Math.round(percentage)}%
          </span>
        )}
      </div>
    );
  }
);
CircularProgress.displayName = 'CircularProgress';

export { Progress, CircularProgress, progressVariants, progressBarVariants };
export type { ProgressProps, CircularProgressProps };
