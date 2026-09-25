import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from '../ui/Card';
import { cn } from '../../lib/utils';
import { cva } from 'class-variance-authority';

/* Reference: Lobe UI `dashboard/StatCard/StatCard.tsx` */
const statCardVariants = cva(
  'flex flex-col gap-3 transition-colors duration-150',
  {
    variants: {
      variant: {
        default: '',
        bordered: 'border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)]',
        elevated: 'shadow-lg shadow-black/20',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface StatCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    trend: 'up' | 'down' | 'neutral';
  };
  icon?: React.ReactNode;
  description?: string;
  className?: string;
  variant?: 'default' | 'bordered' | 'elevated';
}

const TrendIcon = ({ trend }: { trend: 'up' | 'down' | 'neutral' }) => {
  if (trend === 'up') return <TrendingUp size={12} />;
  if (trend === 'down') return <TrendingDown size={12} />;
  return <Minus size={12} />;
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  icon,
  description,
  className,
  variant = 'default',
}) => {
  const trendColors = {
    up: 'text-emerald-400 bg-emerald-500/10',
    down: 'text-rose-400 bg-rose-500/10',
    neutral: 'text-[var(--color-text-secondary)] bg-[var(--color-bg-surface-2)]',
  };

  return (
    <Card variant={variant} padding="md" className={cn(statCardVariants({ variant }), className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">{title}</span>
        {icon && (
          <div className="p-2 rounded-xl bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]">
            {icon}
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-[var(--color-text-primary)] tracking-tight">{value}</span>
        {change && (
          <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1', trendColors[change.trend])}>
            <TrendIcon trend={change.trend} />
            {Math.abs(change.value)}%
          </span>
        )}
      </div>
      {description && <p className="text-xs text-[var(--color-text-muted)] mt-1">{description}</p>}
    </Card>
  );
};

interface DashboardProps {
  stats?: Array<{
    title: string;
    value: string | number;
    icon?: React.ReactNode;
    change?: { value: number; trend: 'up' | 'down' | 'neutral' };
    description?: string;
  }>;
  className?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({ stats, className }) => {
  if (!stats || stats.length === 0) {
    return (
      <Card className={className}>
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          {stats ? '暂无统计数据' : '统计数据未加载'}
        </p>
      </Card>
    );
  }

  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4', className)}>
      {stats.map((stat, index) => (
        <StatCard key={index} {...stat} />
      ))}
    </div>
  );
};

export default Dashboard;
