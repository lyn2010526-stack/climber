import { forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const switchVariants = cva(
  'relative inline-flex shrink-0 cursor-pointer items-center rounded-full transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg-page)] disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      size: {
        sm: 'h-4 w-7',
        md: 'h-5 w-9',
        lg: 'h-6 w-11',
      },
      variant: {
        default: 'bg-white/[0.1] data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-blue-500 data-[state=checked]:to-violet-500',
        success: 'bg-white/[0.1] data-[state=checked]:bg-emerald-500',
        warning: 'bg-white/[0.1] data-[state=checked]:bg-amber-500',
      },
    },
    defaultVariants: {
      size: 'md',
      variant: 'default',
    },
  }
);

const thumbVariants = cva(
  'pointer-events-none block rounded-full bg-white shadow-lg shadow-black/30 transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]',
  {
    variants: {
      size: {
        sm: 'h-3 w-3 data-[state=checked]:translate-x-3 data-[state=unchecked]:translate-x-0.5',
        md: 'h-4 w-4 data-[state=checked]:translate-x-[18px] data-[state=unchecked]:translate-x-[2px]',
        lg: 'h-5 w-5 data-[state=checked]:translate-x-[22px] data-[state=unchecked]:translate-x-[2px]',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

interface SwitchProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning';
  label?: string;
  description?: string;
  name?: string;
  id?: string;
}

const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, onChange, disabled, className, size, variant, label, description, name, id }, ref) => {
    const switchId = id || name || `switch-${Math.random().toString(36).substring(2, 8)}`;

    return (
      <div className="flex items-center gap-3">
        <button
          ref={ref}
          type="button"
          id={switchId}
          role="switch"
          aria-checked={checked}
          aria-label={label}
          disabled={disabled}
          data-state={checked ? 'checked' : 'unchecked'}
          onClick={() => !disabled && onChange?.(!checked)}
          className={cn(switchVariants({ size, variant }), className)}
        >
          <span className={cn(thumbVariants({ size }))} data-state={checked ? 'checked' : 'unchecked'} />
        </button>
        {(label || description) && (
          <label htmlFor={switchId} className="cursor-pointer select-none">
            {label && <span className="text-sm text-[var(--color-text-primary)]">{label}</span>}
            {description && <span className="block text-xs text-[var(--color-text-muted)]">{description}</span>}
          </label>
        )}
      </div>
    );
  }
);
Switch.displayName = 'Switch';

export { Switch, switchVariants, thumbVariants };
export type { SwitchProps };
