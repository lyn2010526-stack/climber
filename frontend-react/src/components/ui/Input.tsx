import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const inputVariants = cva(
  'flex w-full rounded-lg border px-3 py-2 text-sm transition-all duration-200 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        default: '',
        destructive: '',
        success: '',
      },
      inputSize: {
        sm: 'h-8 px-2.5 text-xs',
        md: 'h-10 px-3 text-sm',
        lg: 'h-12 px-4 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      inputSize: 'md',
    },
  }
);

const variantStyles: Record<string, React.CSSProperties> = {
  default: {
    backgroundColor: 'var(--color-bg-surface-2)',
    borderColor: 'var(--color-border-subtle)',
    color: 'var(--color-text-primary)',
  },
  destructive: {
    backgroundColor: 'var(--color-error-subtle)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    color: 'var(--color-error)',
  },
  success: {
    backgroundColor: 'var(--color-success-subtle)',
    borderColor: 'rgba(34, 197, 94, 0.3)',
    color: 'var(--color-success)',
  },
};

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement>, VariantProps<typeof inputVariants> {
  inputSize?: 'sm' | 'md' | 'lg' | null;
}

const Input = forwardRef<HTMLInputElement, InputProps>(({ className, variant, inputSize, style, ...props }, ref) => {
  return (
    <input
      className={cn(inputVariants({ variant, inputSize, className }))}
      ref={ref}
      style={{ ...variantStyles[variant || 'default'], ...style }}
      {...props}
    />
  );
});
Input.displayName = 'Input';

export { Input, inputVariants };
export type { InputProps };