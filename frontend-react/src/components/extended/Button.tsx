/* ────────────────────────────────────────────────────────────
   ENHANCED BUTTON COMPONENT
   Visual Hierarchy System - LineCodePro Standard
   ──────────────────────────────────────────────────────────── */

import React, { useCallback } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Additional CSS class names */
  className?: string;
  /** Button variant: primary | secondary | ghost | destructive | text */
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive' | 'text';
  /** Button size: sm | md | lg */
  size?: 'sm' | 'md' | 'lg';
  /** Full width button */
  fullWidth?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Icon before text */
  leadingIcon?: React.ReactNode;
  /** Icon after text */
  trailingIcon?: React.ReactNode;
  /** Disable ripple effect */
  disableRipple?: boolean;
}

/** Combine CSS classes with tailwind-merge */
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

/** Enhanced Button Component with full visual hierarchy support */
export function Button({
  children,
  className,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  loading = false,
  leadingIcon,
  trailingIcon,
  disableRipple = false,
  disabled,
  onClick,
  ...restProps
}: ButtonProps) {
  
  const handleClick = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled && !loading) {
      onClick?.(e);
    }
  }, [disabled, loading, onClick]);

  const baseStyles = `
    inline-flex items-center justify-center gap-2
    font-medium transition-all duration-150 ease-out-expo
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface-page
    active:scale-[0.98]
    disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100
    select-none touch-manipulation
  `;

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs rounded-sm min-h-[28px]',
    md: 'px-4 py-2 text-sm rounded-md min-h-[36px]',
    lg: 'px-6 py-3 text-base rounded-lg min-h-[44px]',
  };

  const fullWidthClass = fullWidth ? 'w-full' : '';

  const variantStyles = {
    primary: `
      bg-accent hover:bg-accent-hover text-white border-transparent
      hover:shadow-glow-md hover:-translate-y-0.5
      active:translate-y-0 active:shadow-glow-sm
    `,
    secondary: `
      bg-surface-2 border border-border-default text-text-level-1
      hover:bg-surface-3 hover:border-border-strong
      active:translate-y-0.5
    `,
    ghost: `
      bg-transparent text-text-level-2 border-transparent
      hover:bg-surface-2 hover:text-text-level-1
      active:translate-y-0.5
    `,
    destructive: `
      bg-error hover:bg-error-hover text-white border-transparent
      hover:shadow-glow-error active:translate-y-0.5
    `,
    text: `
      bg-transparent text-accent border-transparent
      hover:bg-accent-subtle hover:text-accent-hover
      active:translate-y-0.5
    `,
  };

  const iconSize = size === 'sm' ? 14 : size === 'lg' ? 20 : 16;

  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={handleClick}
      className={cn(
        baseStyles,
        sizeClasses[size],
        fullWidthClass,
        variantStyles[variant],
        className
      )}
      {...restProps}
    >
      {/* Leading Icon */}
      {leadingIcon && (
        <span className="flex-shrink-0">
          {React.cloneElement(leadingIcon as React.ReactElement, {
            size: iconSize,
            className: undefined,
          } as Record<string, unknown>)}
        </span>
      )}

      {/* Loading Spinner */}
      {loading && (
        <span className="flex-shrink-0 flex items-center justify-center">
          <svg 
            className="animate-spin h-4 w-4" 
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle 
              className="opacity-25" 
              cx="12" 
              cy="12" 
              r="10" 
              stroke="currentColor" 
              strokeWidth="2"
            />
            <path 
              className="opacity-75" 
              fill="currentColor" 
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}

      {/* Button Text */}
      {!loading && children && (
        <span className="whitespace-nowrap">{children}</span>
      )}

      {/* Trailing Icon */}
      {trailingIcon && !loading && (
        <span className="flex-shrink-0">
          {React.cloneElement(trailingIcon as React.ReactElement, {
            size: iconSize,
            className: undefined,
          } as Record<string, unknown>)}
        </span>
      )}
    </button>
  );
}
