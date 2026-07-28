import React from 'react';
import { Activity, Cpu, MemoryStick, Zap, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from '../ui/Card';
import { cn } from '../../lib/utils';
import { cva } from 'class-variance-authority';

/* Reference: Lobe UI `dashboard/StatCard/StatCard.tsx` */
const statCardVariants = cva(
  'flex flex-col gap-3 transition-all duration-200 hover:scale-[1.02]',
  {
    variants: {
      variant: {
        default: '',
        bordered: 'border border-white/10 bg-white/[0.02]',
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
    neutral: 'text-gray-400 bg-white/5',
  };

  return (
    <Card variant={variant} padding="md" className={cn(statCardVariants({ variant }), className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{title}</span>
        {icon && (
          <div className="p-2 rounded-xl bg-white/5 text-gray-400">
            {icon}
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-white tracking-tight">{value}</span>
        {change && (
          <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1', trendColors[change.trend])}>
            <TrendIcon trend={change.trend} />
            {Math.abs(change.value)}%
          </span>
        )}
      </div>
      {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
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
  const defaultStats = [
    { title: '活跃会话', value: '12', icon: <Activity className="h-5 w-5" />, change: { value: 12, trend: 'up' } as const },
    { title: 'Token 消耗', value: '45.2K', icon: <Zap className="h-5 w-5" />, change: { value: 8, trend: 'up' } as const },
    { title: '内存使用', value: '1.2GB', icon: <MemoryStick className="h-5 w-5" />, change: { value: 3, trend: 'down' } as const },
    { title: 'CPU 负载', value: '34%', icon: <Cpu className="h-5 w-5" />, change: { value: 5, trend: 'neutral' } as const },
  ];

  const displayStats = stats || defaultStats;

  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4', className)}>
      {displayStats.map((stat, index) => (
        <div key={index} className="animate-in fade-in duration-500" style={{ animationDelay: `${index * 100}ms` }}>
          <StatCard {...stat} />
        </div>
      ))}
    </div>
  );
};

export default Dashboard;
