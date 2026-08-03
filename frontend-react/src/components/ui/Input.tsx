import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const inputVariants = cva(
  'flex w-full rounded-lg border bg-surface-inset px-3 py-2 text-sm transition-all duration-200 placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-accent disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'border-border',
        destructive: 'border-destructive focus-visible:ring-destructive',
        success: 'border-success focus-visible:ring-success',
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

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement>, VariantProps<typeof inputVariants> {
  inputSize?: 'sm' | 'md' | 'lg' | null;
}

const Input = forwardRef<HTMLInputElement, InputProps>(({ className, variant, inputSize, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(inputVariants({ variant, inputSize, className }))}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = 'Input';

export { Input, inputVariants };
export type { InputProps };
