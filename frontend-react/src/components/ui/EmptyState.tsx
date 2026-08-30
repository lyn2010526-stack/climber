import React from 'react';

export interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={`text-center py-16 ${className ?? ''}`}>
      <div className="w-16 h-16 rounded-3xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-4">
        <Icon size={28} className="text-[var(--color-text-muted)]" />
      </div>
      <p className="text-[var(--color-text-primary)] font-medium text-sm">{title}</p>
      {description && <p className="text-[var(--color-text-muted)] text-xs mt-1">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-5 py-2.5 bg-[var(--color-accent)] text-white rounded-2xl text-sm font-semibold hover:bg-[var(--color-accent-hover)] transition-all duration-200 active:scale-[0.97]"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
