import React from 'react';
import { cn } from '../../lib/utils';

export interface ListCardProps {
  icon: React.ElementType;
  iconColor?: string;
  iconBg?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  onClick?: () => void;
  className?: string;
  badge?: string;
}

export function ListCard({
  icon: Icon,
  iconColor = 'var(--color-accent)',
  iconBg = 'var(--color-accent-subtle)',
  title,
  description,
  actions,
  onClick,
  className,
  badge,
}: ListCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-[var(--color-bg-surface-1)] border rounded-2xl p-4 flex items-center gap-4 transition-all duration-200',
        onClick ? 'cursor-pointer hover:border-[var(--color-accent)]/30' : '',
        className
      )}
      style={{ border: '1px solid var(--color-border-subtle)' }}
    >
      <div
        className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: iconBg, border: `1px solid ${iconColor}20` }}
      >
        <Icon size={20} style={{ color: iconColor }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm truncate" style={{ color: 'var(--color-text-primary)' }}>{title}</h3>
          {badge && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: `${iconColor}15`, color: iconColor }}>
              {badge}
            </span>
          )}
        </div>
        {description && <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-1 shrink-0">{actions}</div>}
    </div>
  );
}
