import { useState, forwardRef, InputHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  icon?: ReactNode;
  loading?: boolean;
  error?: string;
  hint?: string;
  success?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ size = 'md', leftIcon, rightIcon, icon, loading, error, hint, success, className, type, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === 'password';
    const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

    const sizeMap = {
      sm: 'h-8 text-xs px-3 rounded-lg',
      md: 'h-10 text-sm px-3.5 rounded-xl',
      lg: 'h-11 text-sm px-4 rounded-xl',
    };

    const iconSizeMap = { sm: 12, md: 14, lg: 16 };

    return (
      <div className="w-full">
        <div className="relative flex items-center">
          {(leftIcon || icon) && (
            <span className="absolute left-3 flex items-center text-[var(--color-text-muted)]">
              {leftIcon || icon}
            </span>
          )}
          <input
            ref={ref}
            type={inputType}
            className={cn(
              'w-full border bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)]',
              'placeholder:text-[var(--color-text-muted)] transition-all duration-150',
              'hover:border-[var(--color-border-strong)]',
              'focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)] focus:bg-[var(--color-bg-surface-1)]',
              'disabled:bg-[var(--color-bg-surface-3)] disabled:text-[var(--color-text-disabled)] disabled:cursor-not-allowed disabled:opacity-60',
              sizeMap[size],
              (leftIcon || icon) && 'pl-9',
              (rightIcon || loading || isPassword || error || success) && 'pr-9',
              error && 'border-[var(--color-error)] focus:ring-[var(--color-error)]/20 focus:border-[var(--color-error)]',
              !error && success && 'border-[var(--color-success)] focus:ring-[var(--color-success)]/20 focus:border-[var(--color-success)]',
              !error && !success && 'border-[var(--color-border-default)]',
              className
            )}
            {...props}
          />
          <span className="absolute right-3 flex items-center gap-1.5">
            {loading && <Loader2 size={iconSizeMap[size]} className="text-[var(--color-text-muted)] animate-spin" />}
            {!loading && error && <AlertCircle size={iconSizeMap[size]} className="text-[var(--color-error)]" />}
            {!loading && !error && success && <CheckCircle2 size={iconSizeMap[size]} className="text-[var(--color-success)]" />}
            {isPassword && (
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">
                {showPassword ? <EyeOff size={iconSizeMap[size]} /> : <Eye size={iconSizeMap[size]} />}
              </button>
            )}
            {!loading && !error && !success && !isPassword && rightIcon}
          </span>
        </div>
        {error && <p className="mt-1.5 text-xs text-[var(--color-error)] leading-relaxed">{error}</p>}
        {hint && !error && <p className="mt-1.5 text-xs text-[var(--color-text-muted)] leading-relaxed">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
