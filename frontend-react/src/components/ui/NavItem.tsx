import React from 'react';
import { cn } from '../../lib/utils';

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  badge?: string | number;
  onClick?: () => void;
  className?: string;
  compact?: boolean;
}

export function NavItem({ icon, label, active, badge, onClick, className, compact }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 rounded-2xl text-sm transition-all duration-200 border relative group',
        compact ? 'px-2.5 py-2' : 'px-3 py-2.5',
        className
      )}
      style={{
        color: active ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
        backgroundColor: active ? 'var(--color-accent-subtle)' : 'transparent',
        borderColor: active ? 'var(--color-border-accent)' : 'transparent',
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
          e.currentTarget.style.color = 'var(--color-text-secondary)';
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.color = 'var(--color-text-muted)';
        }
      }}
    >
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full" style={{
          backgroundColor: 'var(--color-accent)',
          boxShadow: '0 0 8px var(--color-accent-glow)'
        }} />
      )}
      <div className={cn('rounded-xl flex items-center justify-center transition-all duration-200', compact ? 'p-1' : 'p-1.5')} style={{
        backgroundColor: active ? 'rgba(94,106,210,0.15)' : 'var(--color-bg-surface-2)',
        color: active ? 'var(--color-accent)' : 'var(--color-text-muted)',
      }}>
        {icon}
      </div>
      {!compact && (
        <span className={cn('flex-1 truncate', active ? 'font-medium' : 'font-normal')}>{label}</span>
      )}
      {!compact && badge !== undefined && (
        <span className="text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
          backgroundColor: 'var(--color-bg-surface-3)',
          color: 'var(--color-text-muted)',
        }}>
          {badge}
        </span>
      )}
    </button>
  );
}
