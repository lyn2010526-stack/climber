import React from 'react';

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: string;
  color?: string;
  bgColor?: string;
  className?: string;
}

export function StatCard({ icon: Icon, label, value, trend, color = 'var(--color-accent)', bgColor = 'var(--color-accent-subtle)', className }: StatCardProps) {
  return (
    <div className={`bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5 transition-all duration-200 ${className ?? ''}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ backgroundColor: bgColor, border: `1px solid ${color}20` }}>
          <Icon size={20} style={{ color }} />
        </div>
        {trend && (
          <span className="flex items-center gap-1 text-xs font-medium text-[var(--color-success)]">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
            {trend}
          </span>
        )}
      </div>
      <div className="text-3xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>{value}</div>
      <div className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
    </div>
  );
}
