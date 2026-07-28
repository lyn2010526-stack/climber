import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { Loader2 } from 'lucide-react';

const spinnerVariants = cva('animate-spin', {
  variants: {
    size: {
      sm: 'h-4 w-4',
      md: 'h-6 w-6',
      lg: 'h-8 w-8',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

interface SpinnerProps extends VariantProps<typeof spinnerVariants> {
  className?: string;
  label?: string;
}

const Spinner = ({ size, className, label }: SpinnerProps) => {
  return (
    <div className="inline-flex items-center gap-2">
      <Loader2 className={cn(spinnerVariants({ size }), className)} />
      {label && <span className="text-sm text-muted-foreground">{label}</span>}
    </div>
  );
};

export { Spinner, spinnerVariants };
export type { SpinnerProps };
