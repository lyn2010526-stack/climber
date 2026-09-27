import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'linear' | 'circular';
  color?: 'primary' | 'success' | 'warning' | 'danger';
  /**
   * A run whose length is unknown. The bar then reports no value at all rather
   * than a fabricated one, because a progressbar that announces a number it
   * cannot stand behind is worse than one that admits it is busy.
   */
  indeterminate?: boolean;
  animated?: boolean;
  striped?: boolean;
  showLabel?: boolean;
  label?: string;
  className?: string;
}

const colorMap = {
  primary: 'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-error)',
};

/**
 * The track is a surface, never a tint of the fill. A progress bar sits on top
 * of whatever panel it is drawn in, so its own background has to be that
 * panel's next step up rather than a second dose of the status hue, which would
 * read as a partly filled bar at a glance.
 */
const colorTrackMap = {
  primary: 'var(--color-bg-surface-3)',
  success: 'var(--color-bg-surface-3)',
  warning: 'var(--color-bg-surface-3)',
  danger: 'var(--color-bg-surface-3)',
};

const heightMap = {
  sm: 'h-[var(--space-1)]',
  md: 'h-[var(--space-2)]',
  lg: 'h-[var(--space-3)]',
};

/**
 * Ring geometry is declared as numbers because `width`, `height`, `r` and
 * `stroke-width` are SVG attributes and only accept lengths, so there is no
 * token syntax available for them. The colours stay on tokens.
 */
const ringSizeMap = { sm: 32, md: 48, lg: 64 };
const strokeWidthMap = { sm: 3, md: 4, lg: 5 };

const LinearProgress: React.FC<Omit<ProgressProps, 'variant'>> = ({
  value,
  max = 100,
  size = 'md',
  color = 'primary',
  indeterminate = false,
  animated = false,
  striped = false,
  showLabel = false,
  label,
  className,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const opacity = striped ? 0.9 : 1;
  // An indeterminate run has no end to grow towards, so the fill holds a fixed
  // slice and its motion is the only thing that reports progress.
  const fillStyle = indeterminate
    ? { width: '35%', backgroundColor: colorMap[color], opacity }
    : { width: `${percentage}%`, backgroundColor: colorMap[color], opacity };

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="mb-[var(--space-1-5)] flex items-center justify-between">
          <span className="text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">{label}</span>
          {showLabel && !indeterminate && (
            <span className="text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-muted)]">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div
        className={cn('w-full overflow-hidden rounded-[var(--radius-pill)]', heightMap[size])}
        style={{ backgroundColor: colorTrackMap[color] }}
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : value}
        aria-valuemin={indeterminate ? undefined : 0}
        aria-valuemax={indeterminate ? undefined : max}
        aria-valuetext={indeterminate ? 'In progress' : undefined}
        aria-label={label || 'Progress'}
      >
        <div
          className={cn(
            'h-full rounded-[var(--radius-pill)] transition-[width] duration-[var(--transition-slow)] ease-out motion-reduce:transition-none',
            animated && 'motion-safe:animate-pulse',
            indeterminate && 'motion-safe:animate-pulse'
          )}
          style={fillStyle}
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
  indeterminate = false,
  showLabel = false,
  label,
  className,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const dimension = ringSizeMap[size];
  const strokeWidth = strokeWidthMap[size];
  const radius = (dimension - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // Three quarters of an arc is the honest indeterminate ring: work visibly
  // under way, with nothing claimed about how much is left.
  const strokeDashoffset = indeterminate
    ? circumference * 0.75
    : circumference - (percentage / 100) * circumference;

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg
        width={dimension}
        height={dimension}
        className="rotate-[-90deg]"
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : value}
        aria-valuemin={indeterminate ? undefined : 0}
        aria-valuemax={indeterminate ? undefined : max}
        aria-valuetext={indeterminate ? 'In progress' : undefined}
        aria-label={label || 'Progress'}
      >
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke={colorTrackMap[color]}
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
          className={cn(
            'transition-[stroke-dashoffset] duration-[var(--transition-slow)] ease-out motion-reduce:transition-none',
            indeterminate && 'motion-safe:animate-spin'
          )}
        />
      </svg>
      {showLabel && !indeterminate && (
        <span className="absolute text-[length:var(--text-xs)] font-medium tabular-nums text-[var(--color-text-primary)]">
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
