import { useId, useState, forwardRef, InputHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { useField } from './Field';
import { iconSizes, icons, type StatusTone } from '../../lib/icons';
import { StatusIcon } from './StatusIcon';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  icon?: ReactNode;
  loading?: boolean;
  error?: string;
  hint?: string;
  success?: boolean;
  /** Accessible names for the password reveal toggle; both default to English. */
  showPasswordLabel?: string;
  hidePasswordLabel?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ size = 'md', leftIcon, rightIcon, icon, loading, error, hint, success, className, type, id, disabled, showPasswordLabel = 'Show password', hidePasswordLabel = 'Hide password', ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const generatedId = useId();
    // A surrounding FormField supplies the id its visible <label> points at, so
    // the two stay associated without every call site repeating itself. It also
    // owns the description and the error-or-hint, so this control points at that
    // text instead of rendering a second copy of it.
    const field = useField();
    const inputId = field?.htmlFor ?? id ?? generatedId;
    // Standing alone, the control is the one that renders the message, so it has
    // to both draw and announce it. Inside a field the field already draws it, so
    // the control only points at the one node the field gave it.
    const ownsMessage = !field?.messageId;
    const messageId = ownsMessage && (error || hint) ? `${inputId}-message` : undefined;
    const describedBy = [
      props['aria-describedby'],
      field?.descriptionId,
      // The field's message is only announced when this control has something to
      // say, or a field that renders an error for a different control would be
      // read out as this one's description.
      (error || hint) ? (messageId ?? field?.messageId) : undefined,
    ].filter(Boolean).join(' ') || undefined;
    const isPassword = type === 'password';
    const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

    const sizeMap = {
      sm: 'h-[var(--control-height-xs)] px-[var(--space-3)] text-[length:var(--text-xs)] rounded-[var(--radius-md)]',
      md: 'h-[var(--control-height-md)] px-[var(--space-4)] text-[length:var(--text-sm)] rounded-[var(--radius-md)]',
      lg: 'h-[var(--control-height-lg)] px-[var(--space-4)] text-[length:var(--text-sm)] rounded-[var(--radius-md)]',
    };

    const iconSizeMap = { sm: 'xs', md: 'sm', lg: 'md' } as const;
    // One status at a time, and the busy state outranks the outcome: a field
    // that is still validating has no result to report yet. The tone is handed
    // to `StatusIcon` rather than drawn here, so the glyph and its colour stay
    // owned by the one place that maps a tone to a shape.
    const statusTone: StatusTone | null = loading ? 'loading' : error ? 'error' : success ? 'success' : null;
    const hasStatusIcon = statusTone !== null;
    const hasLeadingGlyph = Boolean(leftIcon || icon);

    // An invalid field keeps the error hue through all three pointer states
    // and walks the border opacity up from resting to hover, so a rejected field
    // looks the same before and after the pointer reaches it.
    const stateClasses = error
      ? [
          'border-[var(--color-error)]/60 bg-[var(--color-error-subtle)]',
          'enabled:hover:border-[var(--color-error)]',
          'focus-visible:border-[var(--color-error)]',
        ]
      : success
        ? [
            'border-[var(--color-success)]/60 bg-[var(--color-bg-surface-2)]',
            'enabled:hover:border-[var(--color-success)]',
            'focus-visible:border-[var(--color-success)]',
          ]
        : [
            'border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]',
            'enabled:hover:border-[var(--color-border-strong)] enabled:hover:bg-[var(--color-bg-surface-3)]',
            'focus-visible:border-[var(--color-border-accent)] focus-visible:bg-[var(--color-bg-surface-1)]',
          ];

    return (
      <div className="w-full">
        <div className="relative flex items-center">
          {hasLeadingGlyph && (
            <span className="absolute left-[var(--space-3)] flex items-center text-[var(--color-text-muted)]">
              {leftIcon || icon}
            </span>
          )}
          <input
            ref={ref}
            type={inputType}
            className={cn(
              'w-full border text-[var(--color-text-primary)]',
              'placeholder:text-[var(--color-text-muted)]',
              'transition-[color,background-color,border-color,box-shadow] duration-150 motion-reduce:transition-none',
              // The shared two-layer focus ring, so the indicator reads on the
              // error wash as readily as on the resting surface.
              'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
              'disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
              sizeMap[size],
              stateClasses,
              hasLeadingGlyph && 'pl-[var(--space-8)]',
              (rightIcon || hasStatusIcon || isPassword) && 'pr-[var(--space-8)]',
              isPassword && (hasStatusIcon ? 'pr-[var(--space-16)]' : 'pr-[var(--space-12)]'),
              className
            )}
            {...props}
            id={inputId}
            disabled={disabled}
            aria-busy={loading || props['aria-busy']}
            aria-invalid={error ? true : props['aria-invalid']}
            aria-describedby={describedBy}
          />
          <span className="pointer-events-none absolute right-[var(--space-3)] flex items-center gap-[var(--control-gap-compact)]">
            <StatusIcon tone={statusTone} size={iconSizeMap[size]} />
            {isPassword && (
              <button type="button" disabled={disabled} aria-label={showPassword ? hidePasswordLabel : showPasswordLabel} aria-pressed={showPassword} aria-controls={inputId} onClick={() => setShowPassword(value => !value)} className="pointer-events-auto inline-flex size-[var(--icon-xl)] items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors motion-reduce:transition-none enabled:hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-not-allowed disabled:text-[var(--color-text-disabled)]">
                {showPassword ? <icons.hidePassword size={iconSizes[iconSizeMap[size]]} aria-hidden="true" focusable="false" /> : <icons.showPassword size={iconSizes[iconSizeMap[size]]} aria-hidden="true" focusable="false" />}
              </button>
            )}
            {!hasStatusIcon && !isPassword && <span className="pointer-events-auto">{rightIcon}</span>}
          </span>
        </div>
        {messageId && error && <p id={messageId} className="mt-[var(--space-1-5)] text-[length:var(--text-xs)] leading-[var(--leading-relaxed)] text-[var(--color-error)]">{error}</p>}
        {messageId && hint && !error && <p id={messageId} className="mt-[var(--space-1-5)] text-[length:var(--text-xs)] leading-[var(--leading-relaxed)] text-[var(--color-text-muted)]">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
