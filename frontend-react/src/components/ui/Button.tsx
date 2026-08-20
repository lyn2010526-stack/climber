import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg-page)] disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97] select-none',
  {
    variants: {
      variant: {
        primary: 'text-white shadow-md hover:brightness-110',
        'accent-soft': 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)] hover:brightness-110 font-semibold',
        secondary: 'text-foreground hover:bg-white/[0.08] border',
        outline: 'border bg-transparent hover:bg-white/[0.04] hover:border-white/[0.15]',
        ghost: 'hover:bg-white/[0.06] text-[var(--color-text-secondary)] hover:text-white',
        subtle: 'bg-white/[0.04] text-[var(--color-text-secondary)] hover:bg-white/[0.08] hover:text-white',
        destructive: 'bg-red-500/90 text-white hover:bg-red-500 shadow-sm',
        link: 'underline-offset-4 hover:underline',
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
    const baseStyles: React.CSSProperties = {};
    if (variant === 'primary') {
      baseStyles.backgroundColor = 'var(--color-accent)';
      baseStyles.boxShadow = '0 0 16px var(--color-accent-glow)';
    } else if (variant === 'secondary' || variant === 'outline') {
      baseStyles.borderColor = 'var(--color-border-subtle)';
    } else if (variant === 'destructive') {
      baseStyles.boxShadow = '0 0 12px rgba(239, 68, 68, 0.15)';
    }

    return (
      <button
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        disabled={disabled || loading}
        style={baseStyles}
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