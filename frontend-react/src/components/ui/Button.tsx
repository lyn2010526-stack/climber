import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium select-none cursor-pointer',
  {
    variants: {
      variant: {
        primary: 'bg-[var(--color-accent)] text-white shadow-sm hover:bg-[var(--color-accent-hover)] active:bg-[var(--color-accent)] disabled:bg-[var(--color-text-disabled)] disabled:shadow-none',
        secondary: 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-3)] hover:border-[var(--color-border-strong)] hover:shadow-sm active:scale-[0.97]',
        outline: 'border border-[var(--color-border-default)] bg-transparent text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] hover:border-[var(--color-border-strong)] active:scale-[0.97]',
        ghost: 'bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] active:scale-[0.97]',
        subtle: 'bg-[var(--color-bg-surface-2)]/50 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] active:scale-[0.97]',
        destructive: 'bg-[var(--color-error)] text-white shadow-sm hover:brightness-110 active:brightness-95 disabled:bg-[var(--color-text-disabled)] disabled:shadow-none',
        success: 'bg-[var(--color-success)] text-white shadow-sm hover:brightness-110 active:brightness-95 disabled:bg-[var(--color-text-disabled)] disabled:shadow-none',
        link: 'text-[var(--color-accent)] underline-offset-4 hover:underline hover:text-[var(--color-accent-hover)] bg-transparent',
      },
      size: {
        xs: 'h-8 px-2.5 text-xs rounded-md',
        sm: 'h-9 px-3 text-xs rounded-lg',
        md: 'h-10 px-4 text-sm rounded-lg',
        lg: 'h-11 px-5 text-sm rounded-lg',
        icon: 'h-10 w-10 rounded-lg p-0',
        'icon-sm': 'h-9 w-9 rounded-lg p-0',
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
  icon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, icon, ...props }, ref) => {
    return (
      <button
        className={cn(
          buttonVariants({ variant, size }),
          'transition-[color,background-color,border-color,box-shadow,opacity] duration-150 ease-out',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg-page)]',
          'disabled:pointer-events-none disabled:opacity-50 disabled:cursor-not-allowed',
          loading && 'relative pointer-events-none',
          className
        )}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : icon}
        <span>{children}</span>
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
export type { ButtonProps };
