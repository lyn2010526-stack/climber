import React from 'react';
import { cn } from '../../lib/utils';

interface TabsProps {
  tabs: { id: string; label: string; icon?: React.ReactNode; count?: number }[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
  return (
    <div className={cn('flex items-center gap-1 p-1 rounded-xl', className)} style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200',
            activeTab === tab.id
              ? 'bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] shadow-sm'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
          )}
        >
          {tab.icon}
          {tab.label}
          {tab.count !== undefined && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

export function Toggle({ checked, onChange, label, description, disabled, size = 'md' }: ToggleProps) {
  const sizes = {
    sm: { track: 'w-8 h-4', thumb: 'w-3 h-3', translate: 'translate-x-4' },
    md: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5' },
  };
  const s = sizes[size];

  return (
    <label className={cn('flex items-center justify-between gap-3 cursor-pointer', disabled && 'opacity-50 cursor-not-allowed')}>
      {(label || description) && (
        <div className="flex-1 min-w-0">
          {label && <div className="text-sm font-medium text-[var(--color-text-primary)]">{label}</div>}
          {description && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>}
        </div>
      )}
      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex shrink-0 rounded-full transition-colors duration-200',
          s.track,
          checked ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-surface-3)]'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 rounded-full bg-white shadow-sm transition-transform duration-200',
            s.thumb,
            checked && s.translate
          )}
        />
      </button>
    </label>
  );
}

interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  description?: string;
  unit?: string;
  className?: string;
}

export function Slider({ value, onChange, min = 0, max = 100, step = 1, label, description, unit, className }: SliderProps) {
  const percentage = ((value - min) / (max - min)) * 100;
  const showHeader = label || description || unit

  return (
    <div className={cn('space-y-2', className)}>
      {showHeader && (
        <div className="flex items-center justify-between">
          {label && <span className="text-sm font-medium text-[var(--color-text-primary)]">{label}</span>}
          <span className="text-sm font-mono text-[var(--color-accent)]">
            {value}{unit}
          </span>
        </div>
      )}
      {description && !label && <p className="text-xs text-[var(--color-text-muted)]">{description}</p>}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, var(--color-accent) 0%, var(--color-accent) ${percentage}%, var(--color-bg-surface-3) ${percentage}%, var(--color-bg-surface-3) 100%)`,
        }}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
      />
    </div>
  );
}
