import { cn } from '../../lib/utils';

export interface RadioProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function Radio({ checked, onChange, label, description, disabled = false, className }: RadioProps) {
  return (
    <label className={cn('flex items-start gap-3 cursor-pointer', disabled && 'opacity-50 cursor-not-allowed', className)}>
      <div className="relative flex items-center justify-center shrink-0 mt-0.5">
        <input
          type="radio"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
        />
        <div className={cn(
          'w-4 h-4 rounded-full border-2 transition-colors',
          checked ? 'border-[var(--color-accent)] bg-[var(--color-accent)]' : 'border-[var(--color-border-default)] bg-transparent'
        )}>
          {checked && <div className="w-1.5 h-1.5 rounded-full bg-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />}
        </div>
      </div>
      {(label || description) && (
        <div className="flex-1 min-w-0">
          {label && <div className="text-sm font-medium text-[var(--color-text-primary)]">{label}</div>}
          {description && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>}
        </div>
      )}
    </label>
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
      {options.map((option) => (
        <Radio
          key={option.value}
          checked={value === option.value}
          onChange={() => onChange(option.value)}
          label={option.label}
          description={option.description}
        />
      ))}
    </div>
  );
}
