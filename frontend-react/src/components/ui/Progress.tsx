import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'linear' | 'circular';
  color?: 'primary' | 'success' | 'warning' | 'danger';
  animated?: boolean;
  striped?: boolean;
  showLabel?: boolean;
  label?: string;
  className?: string;
}

const colorMap = {
  primary: 'var(--accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
};

const colorBgMap = {
  primary: 'var(--accent-subtle)',
  success: 'var(--color-success-subtle)',
  warning: 'var(--color-warning-subtle)',
  danger: 'var(--color-danger-subtle)',
};

const LinearProgress: React.FC<Omit<ProgressProps, 'variant'>> = ({
  value,
  max = 100,
  size = 'md',
  color = 'primary',
  animated = false,
  striped = false,
  showLabel = false,
  label,
  className,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const heightClasses = { sm: 'h-1', md: 'h-2', lg: 'h-3' };

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex items-center justify-between mb-[var(--space-1-5)]">
          <span className="text-[var(--font-size-xs)] text-[var(--text-secondary)]">{label}</span>
          {showLabel && <span className="text-[var(--font-size-xs)] text-[var(--text-muted)] tabular-nums">{Math.round(percentage)}%</span>}
        </div>
      )}
      <div
        className={cn('w-full rounded-full overflow-hidden', heightClasses[size])}
        style={{ backgroundColor: colorBgMap[color] }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || 'Progress'}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-[var(--transition-slow)] ease-out',
            striped && 'bg-[length:1rem_1rem]',
            animated && 'animate-[progressStripes_1s_linear_infinite]'
          )}
          style={{
            width: `${percentage}%`,
            backgroundColor: colorMap[color],
            ...(striped ? {
              backgroundImage: `linear-gradient(45deg, rgba(255,255,255,0.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.15) 75%, transparent 75%, transparent)`,
              backgroundSize: '1rem 1rem',
            } : {}),
          }}
        />
      </div>
    </div>
  );
};

const CircularProgress: React.FC<Omit<ProgressProps, 'variant'>> = ({
  value,
  max = 100,
  size = 'md',
  color = 'primary',
  showLabel = false,
  label,
  className,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const sizeMap = { sm: 32, md: 48, lg: 64 };
  const strokeWidthMap = { sm: 3, md: 4, lg: 5 };
  const dimension = sizeMap[size];
  const strokeWidth = strokeWidthMap[size];
  const radius = (dimension - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={cn('inline-flex items-center justify-center relative', className)}>
      <svg
        width={dimension}
        height={dimension}
        className="rotate-[-90deg]"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || 'Progress'}
      >
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke={colorBgMap[color]}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke={colorMap[color]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-[var(--transition-slow)] ease-out"
        />
      </svg>
      {showLabel && (
        <span className="absolute text-[var(--font-size-xs)] font-medium text-[var(--text-primary)] tabular-nums">
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  );
};

const Progress: React.FC<ProgressProps> = ({ variant = 'linear', ...props }) => {
  if (variant === 'circular') return <CircularProgress {...props} />;
  return <LinearProgress {...props} />;
};

export { Progress, LinearProgress, CircularProgress };
