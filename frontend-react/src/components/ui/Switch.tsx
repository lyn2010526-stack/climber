import { cn } from '../../lib/utils';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

interface SizeConfig {
  track: string;
  thumb: string;
  translate: string;
  label: string;
  desc: string;
}

export function Switch({ checked, onChange, size = 'md', label, description, disabled = false, className }: SwitchProps) {
  const sizeConfig: Record<'sm' | 'md' | 'lg', SizeConfig> = {
    sm: { track: 'w-7 h-4', thumb: 'w-3 h-3', translate: 'translate-x-3', label: 'text-xs', desc: 'text-[10px]' },
    md: { track: 'w-9 h-5', thumb: 'w-4 h-4', translate: 'translate-x-4', label: 'text-sm', desc: 'text-xs' },
    lg: { track: 'w-11 h-6', thumb: 'w-5 h-5', translate: 'translate-x-5', label: 'text-sm', desc: 'text-xs' },
  };
  const config = sizeConfig[size];

  const switchElement = (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        'relative inline-flex shrink-0 cursor-pointer rounded-full border-2 border-transparent',
        'transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]/30',
        config.track,
        checked ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-surface-4)]',
        disabled && 'opacity-40 cursor-not-allowed',
        !label && className
      )}
    >
      <span className={cn(
        'pointer-events-none inline-block rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out',
        config.thumb,
        checked ? config.translate : 'translate-x-0'
      )} />
    </button>
  );

  if (!label) return switchElement;

  return (
    <div className={cn('flex items-center justify-between gap-3', className)}>
      <div className="flex-1 min-w-0">
        <div className={cn('font-medium text-[var(--color-text-primary)]', config.label)}>{label}</div>
        {description && <div className={cn('text-[var(--color-text-muted)] mt-0.5', config.desc)}>{description}</div>}
      </div>
      {switchElement}
    </div>
  );
}
