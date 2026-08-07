import { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { Check, Minus } from 'lucide-react';

export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  indeterminate?: boolean;
  className?: string;
}

export function Checkbox({ checked, onChange, label, description, disabled = false, indeterminate = false, className }: CheckboxProps) {
  const Icon = indeterminate ? Minus : Check;

  const checkboxElement = (
    <div
      className={cn(
        'w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-all duration-150 cursor-pointer',
        checked || indeterminate
          ? 'bg-[var(--color-accent)] border-[var(--color-accent)]'
          : 'bg-[var(--color-bg-surface-1)] border-[var(--color-border-default)]',
        !checked && !indeterminate && !disabled && 'hover:border-[var(--color-accent)]',
        disabled && 'opacity-40 cursor-not-allowed'
      )}
      onClick={() => !disabled && onChange(!checked)}
    >
      {(checked || indeterminate) && <Icon size={10} className="text-white" strokeWidth={3} />}
    </div>
  );

  if (!label) return checkboxElement;

  return (
    <div className={cn('flex items-start gap-2.5 py-1', className)}>
      {checkboxElement}
      <div className="flex-1 min-w-0">
        <div className={cn('text-sm text-[var(--color-text-primary)] leading-tight', disabled && 'opacity-40')}>{label}</div>
        {description && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>}
      </div>
    </div>
  );
}

export interface CheckboxGroupProps {
  options: Array<{ value: string; label: string; description?: string }>;
  value: string[];
  onChange: (value: string[]) => void;
  className?: string;
}

export function CheckboxGroup({ options, value, onChange, className }: CheckboxGroupProps) {
  const handleToggle = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter(v => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  };

  return (
    <div className={cn('space-y-1', className)}>
      {options.map(option => (
        <Checkbox
          key={option.value}
          checked={value.includes(option.value)}
          onChange={() => handleToggle(option.value)}
          label={option.label}
          description={option.description}
        />
      ))}
    </div>
  );
}

export interface RadioProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function Radio({ checked, onChange, label, description, disabled = false, className }: RadioProps) {
  const radioElement = (
    <div
      className={cn(
        'w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors cursor-pointer',
        checked ? 'border-[var(--color-accent)]' : 'border-[var(--color-border-default)]',
        !checked && !disabled && 'hover:border-[var(--color-accent)]',
        disabled && 'opacity-40 cursor-not-allowed'
      )}
      onClick={() => !disabled && onChange(!checked)}
    >
      {checked && <div className="w-2 h-2 rounded-full bg-[var(--color-accent)]" />}
    </div>
  );

  if (!label) return radioElement;

  return (
    <div className={cn('flex items-start gap-2.5 py-1', className)}>
      {radioElement}
      <div className="flex-1 min-w-0">
        <div className={cn('text-sm text-[var(--color-text-primary)] leading-tight', disabled && 'opacity-40')}>{label}</div>
        {description && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>}
      </div>
    </div>
  );
}

export interface RadioGroupProps {
  options: Array<{ value: string; label: string; description?: string }>;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function RadioGroup({ options, value, onChange, className }: RadioGroupProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {options.map(option => {
        const isSelected = value === option.value;
        return (
          <div
            key={option.value}
            className={cn(
              'flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-150',
              isSelected
                ? 'border-[var(--color-accent)] bg-[var(--color-accent-subtle)]'
                : 'border-[var(--color-border-subtle)] hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-2)]'
            )}
            onClick={() => onChange(option.value)}
          >
            <div className={cn(
              'w-4 h-4 rounded-full border-2 mt-0.5 flex items-center justify-center shrink-0 transition-colors',
              isSelected ? 'border-[var(--color-accent)]' : 'border-[var(--color-border-default)]'
            )}>
              {isSelected && <div className="w-2 h-2 rounded-full bg-[var(--color-accent)]" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-[var(--color-text-primary)]">{option.label}</div>
              {option.description && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{option.description}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
