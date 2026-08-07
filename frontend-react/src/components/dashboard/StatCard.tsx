import React from 'react';
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    trend: 'up' | 'down' | 'neutral';
  };
  icon?: LucideIcon;
  description?: string;
  sparklineData?: number[];
  className?: string;
}

const TrendIcon = ({ trend }: { trend: 'up' | 'down' | 'neutral' }) => {
  if (trend === 'up') return <TrendingUp size={12} />;
  if (trend === 'down') return <TrendingDown size={12} />;
  return <Minus size={12} />;
};

const Sparkline = ({ data, color }: { data: number[]; color: string }) => {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const width = 80;
  const height = 32;
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="shrink-0" viewBox={`0 0 ${width} ${height}`}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  icon: Icon,
  description,
  sparklineData,
  className,
}) => {
  const trendColors = {
    up: 'text-[var(--color-success)] bg-[var(--color-success-subtle)]',
    down: 'text-[var(--color-error)] bg-[var(--color-error-subtle)]',
    neutral: 'text-[var(--color-text-muted)] bg-[var(--color-bg-surface-3)]',
  };

  const sparklineColor = change?.trend === 'up'
    ? 'var(--color-success)'
    : change?.trend === 'down'
      ? 'var(--color-error)'
      : 'var(--color-accent)';

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5 transition-all duration-200',
        'hover:border-[var(--color-border-default)] hover:shadow-lg hover:shadow-black/10',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</span>
            {change && (
              <span className={cn('inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium', trendColors[change.trend])}>
                <TrendIcon trend={change.trend} />
                {Math.abs(change.value)}%
              </span>
            )}
          </div>
          {description && (
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">{description}</p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          {Icon && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-accent-subtle)] text-[var(--color-accent)] transition-colors duration-200 group-hover:bg-[var(--color-accent-glow)]">
              <Icon size={20} />
            </div>
          )}
          {sparklineData && (
            <Sparkline data={sparklineData} color={sparklineColor} />
          )}
        </div>
      </div>

      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-[var(--color-accent)]/20 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
    </div>
  );
};
