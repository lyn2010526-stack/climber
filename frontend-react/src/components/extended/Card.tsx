/* ────────────────────────────────────────────────────────────
   ENHANCED CARD COMPONENT
   Visual Hierarchy System - LineCodePro Standard
   ──────────────────────────────────────────────────────────── */

import React, { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Additional CSS class names */
  className?: string;
  /** Card variant: default | elevated | filled | outlined */
  variant?: 'default' | 'elevated' | 'filled' | 'outlined';
  /** Interactive card (clickable) */
  interactive?: boolean;
  /** Loading skeleton state */
  loading?: boolean;
  /** Hover lift effect */
  hoverLift?: boolean;
  /** Shadow intensity */
  shadow?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  /** Border radius */
  rounded?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  /** Content padding */
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  /** Click handler */
  onClick?: () => void;
  /** Header section */
  header?: React.ReactNode;
  /** Footer section */
  footer?: React.ReactNode;
}

/** Combine CSS classes with tailwind-merge */
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

/** Enhanced Card Component with full visual hierarchy support */
export function Card({
  children,
  className,
  variant = 'default',
  interactive = false,
  loading = false,
  hoverLift = false,
  shadow = 'sm',
  rounded = 'xl',
  padding = 'md',
  onClick,
  header,
  footer,
  ...restProps
}: CardProps) {
  
  const handleClick = useCallback(() => {
    if (!loading && interactive) {
      onClick?.();
    }
  }, [loading, interactive, onClick]);

  const baseStyles = `
    relative transition-all duration-200 ease-out-expo
    ${interactive ? 'cursor-pointer' : 'cursor-default'}
  `;

  const variantStyles = {
    default: `
      bg-surface-1 border border-border-subtle shadow-sm
      hover:border-border-default hover:shadow-md
    `,
    elevated: `
      bg-surface-2 border border-border-default shadow-md
      hover:shadow-lg hover:border-border-strong
    `,
    filled: `
      bg-surface-3 border border-subtle shadow-inner
    `,
    outlined: `
      bg-transparent border border-border-default shadow-none
      hover:bg-surface-1 hover:border-border-strong
    `,
  };

  const shadowClasses = {
    none: '',
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg',
    xl: 'shadow-xl',
  };

  const shapeClass = {
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    '2xl': 'rounded-2xl',
  };

  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
    xl: 'p-8',
  };

  const hoverClass = hoverLift && interactive
    ? 'hover:-translate-y-1 hover:shadow-lg'
    : '';

  // Loading Skeleton Mode
  if (loading) {
    return (
      <div
        className={cn(
          'animate-pulse bg-surface-2 border border-border-subtle',
          shapeClass[rounded],
          className
        )}
        style={{ minHeight: '120px' }}
      >
        <div className="flex items-center gap-3 p-4 mb-4">
          <div className="w-12 h-12 rounded-full bg-surface-3" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-2/3 bg-surface-3 rounded" />
            <div className="h-3 w-1/2 bg-surface-3 rounded" />
          </div>
        </div>
        <div className="px-4 pb-4 space-y-2">
          <div className="h-3 w-full bg-surface-3 rounded" />
          <div className="h-3 w-5/6 bg-surface-3 rounded" />
          <div className="h-3 w-4/6 bg-surface-3 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        shadowClasses[shadow],
        shapeClass[rounded],
        paddingClasses[padding],
        hoverClass,
        className
      )}
      onClick={handleClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={(e) => {
        if (interactive && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-pressed={interactive}
      {...restProps}
    >
      {/* Header */}
      {header && (
        <div className="mb-4 pb-4 border-b border-border-subtle last:pb-0 last:border-0">
          {header}
        </div>
      )}

      {/* Content */}
      <div className={cn(interactive && 'pointer-events-none')}>
        {children}
      </div>

      {/* Footer */}
      {footer && (
        <div className="mt-4 pt-4 border-t border-border-subtle">
          {footer}
        </div>
      )}
    </div>
  );
}
