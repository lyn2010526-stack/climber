import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const cardVariants = cva(
  'rounded-xl border transition-[background-color,border-color,box-shadow] duration-150 ease-out',
  {
    variants: {
      variant: {
        default: 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]',
        elevated: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[0_4px_6px_rgba(0,0,0,0.07)] hover:shadow-[0_10px_15px_rgba(0,0,0,0.1)] hover:-translate-y-0.5',
        bordered: 'border border-white/10 bg-white/[0.02]',
        glass: 'border-[var(--color-glass-border)] bg-[var(--color-glass-bg)] backdrop-blur-xl shadow-[0_4px_6px_rgba(0,0,0,0.07)]',
        outline: 'border-[var(--color-border-default)] bg-transparent hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-surface-2)]/50',
        filled: 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] shadow-[inset_0_2px_4px_rgba(0,0,0,0.05)]',
        gradient: 'border-[var(--color-border-subtle)] bg-gradient-to-br from-[var(--color-bg-surface-1)] to-[var(--color-bg-surface-2)] shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:shadow-[0_4px_6px_rgba(0,0,0,0.07)]',
        interactive: 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)] cursor-pointer hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-2)] active:bg-[var(--color-bg-surface-3)]',
      },
      padding: {
        none: '',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-6',
        xl: 'p-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
    },
  }
);

interface CardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => {
    return <div ref={ref} className={cn(cardVariants({ variant, padding }), className)} {...props} />;
  }
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-1.5 pb-4', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-lg font-semibold leading-none tracking-tight text-[var(--color-text-primary)]', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-[var(--color-text-muted)] leading-relaxed', className)} {...props} />
  )
);
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center pt-4 border-t border-[var(--color-border-subtle)]', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, cardVariants };
export type { CardProps };
