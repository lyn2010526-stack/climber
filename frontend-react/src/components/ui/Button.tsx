import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-colors duration-150 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-45 active:translate-y-px select-none',
  {
    variants: {
      variant: {
        primary: 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]',
        'accent-soft': 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)] hover:bg-[color-mix(in_srgb,var(--color-accent)_14%,transparent)] font-semibold',
        secondary: 'border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]',
        outline: 'border border-[var(--color-border-default)] bg-transparent text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] hover:border-[var(--color-border-strong)]',
        ghost: 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
        subtle: 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]',
        destructive: 'bg-[var(--color-error)] text-white hover:brightness-95',
        link: 'text-[var(--color-accent)] underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-xs rounded-lg',
        md: 'h-10 px-4 text-sm rounded-lg',
        lg: 'h-12 px-6 text-base rounded-xl',
        icon: 'h-10 w-10 rounded-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, ...props }, ref) => {
    return (
      <button
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
export type { ButtonProps };
