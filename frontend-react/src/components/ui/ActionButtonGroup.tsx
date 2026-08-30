import React from 'react';

export interface ActionButtonGroupProps {
  buttons: Array<{
    label: string;
    icon?: React.ElementType;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'danger';
    disabled?: boolean;
  }>;
  className?: string;
}

export function ActionButtonGroup({ buttons, className }: ActionButtonGroupProps) {
  return (
    <div className={`flex flex-wrap gap-2 ${className ?? ''}`}>
      {buttons.map((btn, i) => {
        const VariantIcon = btn.icon;
        const variantClass = btn.variant === 'danger'
          ? 'text-[var(--color-error)] hover:bg-[var(--color-error)]/10'
          : btn.variant === 'secondary'
            ? 'border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]'
            : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] shadow-lg shadow-[var(--color-accent)]/20';
        return (
          <button
            key={i}
            onClick={btn.onClick}
            disabled={btn.disabled}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97] disabled:opacity-50 ${variantClass}`}
          >
            {VariantIcon && <VariantIcon size={14} />}
            {btn.label}
          </button>
        );
      })}
    </div>
  );
}
