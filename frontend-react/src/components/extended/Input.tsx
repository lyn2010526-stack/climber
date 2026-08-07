/* ────────────────────────────────────────────────────────────
   ENHANCED INPUT COMPONENT
   Visual Hierarchy System - LineCodePro Standard
   ──────────────────────────────────────────────────────────── */

import React, { useState, useCallback, useId, useRef, forwardRef } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Additional CSS class names */
  className?: string;
  /** Label text */
  label?: string;
  /** Helper text below input */
  helperText?: string;
  /** Error message */
  error?: boolean | string;
  /** Success state */
  success?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Icon to display before input */
  leadingIcon?: React.ReactNode;
  /** Icon to display after input */
  trailingIcon?: React.ReactNode;
  /** Input size: sm | md | lg */
  size?: 'sm' | 'md' | 'lg';
  /** Variant: default | outlined | filled */
  variant?: 'default' | 'outlined' | 'filled';
  /** Loading state */
  loading?: boolean;
}

/** Combine CSS classes with tailwind-merge */
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

export interface InputRef {
  focus(): void;
  blur(): void;
  setSelectionRange(start: number, end: number): void;
}

/** Enhanced Input Component with full visual hierarchy support */
export const Input = forwardRef<InputRef, InputProps>(function Input(props, ref) {
  const {
    className,
    label,
    helperText,
    error,
    success,
    placeholder,
    leadingIcon,
    trailingIcon,
    size = 'md',
    variant = 'default',
    disabled,
    required,
    loading,
    id,
    value: propValue,
    onFocus,
    onBlur,
    ...restProps
  } = props;

  const generatedId = useId();
  const inputId = id || generatedId;
  const [focused, setFocused] = useState(false);
  const [internalValue, setInternalValue] = useState((propValue ?? restProps.defaultValue ?? '') as string);
  const value = (propValue ?? internalValue) as string;
  
  const inputRef = useRef<HTMLInputElement>(null);

  // Expose methods via forwardRef
  React.useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
    blur: () => inputRef.current?.blur(),
    setSelectionRange: (start, end) => inputRef.current?.setSelectionRange(start, end),
  }));

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInternalValue(e.target.value);
    restProps.onChange?.(e);
  }, [restProps.onChange]);

  const handleFocus = useCallback((e: React.FocusEvent<HTMLInputElement>) => {
    setFocused(true);
    onFocus?.(e);
  }, [onFocus]);

  const handleBlur = useCallback((e: React.FocusEvent<HTMLInputElement>) => {
    setFocused(false);
    onBlur?.(e);
  }, [onBlur]);

  const isError = error !== undefined && error !== '';
  const isStatusSet = isError || success;

  const sizeClasses = {
    sm: 'text-xs px-3 py-1.5 min-h-[28px] rounded-sm',
    md: 'text-sm px-4 py-2 min-h-[36px] rounded-md',
    lg: 'text-base px-5 py-3 min-h-[44px] rounded-lg',
  };

  const baseStyles = `
    w-full bg-surface-2 
    transition-all duration-150 ease-out-expo
    disabled:bg-surface-3 disabled:text-text-level-4 disabled:cursor-not-allowed
    hover:border-border-strong
    autofill:bg-surface-2 autofill:border-border-default autofill:transition-colors
  `;

  const variantStyles = {
    default: `
      border border-border-default
      focus:border-accent focus:ring-3 focus:ring-accent-glow
      placeholder:text-text-level-3
    `,
    outlined: `
      border-2 border-border-default
      focus:border-accent focus:ring-3 focus:ring-accent-glow
      placeholder:text-text-level-3
    `,
    filled: `
      bg-surface-3 border border-transparent
      focus:bg-surface-2 focus:border-accent focus:ring-3 focus:ring-accent-glow
      placeholder:text-text-level-3
    `,
  };

  const statusStyles = {
    error: 'border-error focus:border-error focus:ring-error-glow',
    success: 'border-success focus:border-success focus:ring-success-glow',
    default: '',
  };

  return (
    <div className={cn('flex flex-col gap-1.5 w-full', className)}>
      {/* Label */}
      {label && (
        <label 
          htmlFor={inputId}
          className="text-xs font-medium text-text-level-1"
        >
          {label}
          {required && <span className="text-error ml-0.5">*</span>}
        </label>
      )}

      {/* Input Container */}
      <div className="relative group">
        {/* Leading Icon */}
        {leadingIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-level-3 pointer-events-none">
            {leadingIcon}
          </div>
        )}

        {/* Input Field */}
        <input
          {...restProps}
          ref={inputRef}
          id={inputId}
          type={restProps.type || 'text'}
          value={value}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          disabled={disabled}
          required={required}
          placeholder={placeholder}
          aria-invalid={isError}
          aria-describedby={isError ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          className={cn(
            baseStyles,
            sizeClasses[size],
            variantStyles[variant],
            isStatusSet ? statusStyles[isError ? 'error' : 'success'] : statusStyles.default,
            focused && 'bg-surface-1',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        />

        {/* Status Icon */}
        {trailingIcon && !disabled && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-level-3 pointer-events-none">
            {trailingIcon}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}
      </div>

      {/* Helper/Error Text */}
      {(helperText || isError) && (
        <div 
          id={isError ? `${inputId}-error` : `${inputId}-helper`}
          className={cn(
            'text-xs transition-opacity duration-150',
            isError ? 'text-error' : 'text-text-level-3',
            !helperText && !isError ? 'opacity-0' : 'opacity-100'
          )}
        >
          {isError ? String(error) : helperText}
        </div>
      )}
    </div>
  );
});
