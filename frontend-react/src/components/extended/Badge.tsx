/* ────────────────────────────────────────────────────────────
   ENHANCED BADGE COMPONENT
   Visual Hierarchy System - LineCodePro Standard
   ──────────────────────────────────────────────────────────── */

import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Additional CSS class names */
  className?: string;
  /** Badge variant: default | success | warning | error | primary | secondary | outline */
  variant?: 'default' | 'success' | 'warning' | 'error' | 'primary' | 'secondary' | 'outline' | 'ghost' | 'info';
  /** Badge size: sm | md | lg */
  size?: 'sm' | 'md' | 'lg';
  /** Show rounded pill shape */
  pill?: boolean;
  /** Icon before text */
  leadingIcon?: React.ReactNode;
  /** Count badge (number) */
  count?: number;
  /** Whether badge is empty */
  isEmpty?: boolean;
}

/** Combine CSS classes with tailwind-merge */
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

/** Enhanced Badge Component with full visual hierarchy support */
export function Badge({
  children,
  className,
  variant = 'default',
  size = 'md',
  pill = false,
  leadingIcon,
  count,
  isEmpty,
  ...restProps
}: BadgeProps) {
  
  if (isEmpty && !children && count === undefined) {
    return null;
  }

  const displayCount = count !== undefined ? count : undefined;
  const hasChildren = children && children !== '';

  const baseStyles = `
    inline-flex items-center justify-center gap-1.5
    font-semibold transition-all duration-150 ease-out-expo
    whitespace-nowrap select-none
  `;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] leading-tight rounded-full',
    md: 'px-2.5 py-0.5 text-xs font-medium rounded-full',
    lg: 'px-3 py-1 text-sm font-medium rounded-lg',
  };

  const shapeClass = pill ? 'rounded-full' : 'rounded-md';

  const variantStyles = {
    default: `
      bg-surface-3 border border-border-subtle text-text-level-2
    `,
    success: `
      bg-success-subtle border border-success-strong text-success
      shadow-glow-sm
    `,
    warning: `
      bg-warning-subtle border border-warning-strong text-warning
      shadow-glow-sm
    `,
    error: `
      bg-error-subtle border border-error-strong text-error
      shadow-glow-sm
    `,
    primary: `
      bg-accent-subtle border border-accent-strong text-accent
      shadow-glow-sm
    `,
    secondary: `
      bg-surface-2 border border-border-default text-text-level-2
    `,
    outline: `
      bg-transparent border border-border-default text-text-level-2
    `,
    ghost: `
      bg-transparent text-text-level-2 hover:bg-surface-2
    `,
    info: `
      bg-info-subtle border border-info-strong text-info
      shadow-glow-sm
    `,
  };

  const containerPadding = {
    sm: leadingIcon ? 'gap-1 px-1.5 py-0.5' : '',
    md: leadingIcon ? 'gap-1 px-2 py-0.5' : '',
    lg: leadingIcon ? 'gap-1.5 px-3 py-1' : '',
  };

  const iconSize = size === 'sm' ? 10 : size === 'lg' ? 16 : 12;

  return (
    <span
      className={cn(
        baseStyles,
        sizeClasses[size],
        shapeClass,
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

      {/* Content */}
      {(hasChildren || displayCount !== undefined) && (
        <span>{displayCount ?? children}</span>
      )}
    </span>
  );
}
