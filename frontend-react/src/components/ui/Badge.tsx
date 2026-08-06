import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { forwardRef } from 'react';

const badgeVariants = cva(
  'inline-flex items-center gap-1 font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]',
        secondary: 'border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]',
        primary: 'border border-[rgba(94,106,210,0.2)] bg-[var(--color-accent-subtle)] text-[var(--color-accent)]',
        success: 'border border-[rgba(16,185,129,0.2)] bg-[var(--color-success-subtle)] text-[var(--color-success)]',
        warning: 'border border-[rgba(245,158,11,0.2)] bg-[var(--color-warning-subtle)] text-[var(--color-warning)]',
        destructive: 'border border-[rgba(239,68,68,0.2)] bg-[var(--color-error-subtle)] text-[var(--color-error)]',
        info: 'border border-[rgba(59,130,246,0.2)] bg-[var(--color-info-subtle)] text-[var(--color-info)]',
        outline: 'border border-[var(--color-border-default)] bg-transparent',
      },
      size: {
        xs: 'px-1.5 py-0.5 text-[10px] rounded-md',
        sm: 'px-2 py-0.5 text-xs rounded-lg',
        md: 'px-2.5 py-0.5 text-xs rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
    },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode;
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(({ className, variant, size, icon, children, ...props }, ref) => {
  return (
    <div ref={ref} className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {icon}
      {children}
    </div>
  );
});
Badge.displayName = 'Badge';

export { Badge, badgeVariants };
export type { BadgeProps };
