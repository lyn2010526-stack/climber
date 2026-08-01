import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0A0F] disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97] select-none',
  {
    variants: {
      variant: {
        primary: 'bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] text-white shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 hover:brightness-110',
        secondary: 'bg-white/[0.06] text-foreground hover:bg-white/[0.1] border border-white/[0.06]',
        outline: 'border border-white/[0.1] bg-transparent hover:bg-white/[0.04] hover:border-white/[0.15] text-gray-200',
        ghost: 'hover:bg-white/[0.06] text-gray-300 hover:text-white',
        subtle: 'bg-white/[0.03] text-gray-300 hover:bg-white/[0.06] hover:text-white',
        destructive: 'bg-red-500/90 text-white hover:bg-red-500 shadow-sm shadow-red-500/20',
        link: 'text-blue-400 underline-offset-4 hover:underline hover:text-blue-300',
      },
      size: {
        sm: 'h-8 px-3 text-xs rounded-xl',
        md: 'h-10 px-4 text-sm rounded-xl',
        lg: 'h-12 px-6 text-base rounded-2xl',
        icon: 'h-10 w-10 rounded-xl',
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
