import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const cardVariants = cva(
  'rounded-xl border transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]',
  {
    variants: {
      variant: {
        default: '',
        elevated: 'hover:shadow-lg',
        glass: 'backdrop-blur-xl',
        outline: 'bg-transparent',
        bordered: '',
        gradient: 'bg-gradient-to-br from-white/[0.04] to-white/[0.01]',
      },
      padding: {
        none: '',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-5',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
    },
  }
);

const variantStyles: Record<string, React.CSSProperties> = {
  default: { backgroundColor: 'var(--color-bg-surface-1)', borderColor: 'var(--color-border-subtle)' },
  elevated: { backgroundColor: 'var(--color-bg-surface-2)', borderColor: 'var(--color-border-subtle)' },
  glass: { backgroundColor: 'var(--color-glass-bg)', borderColor: 'var(--color-glass-border)' },
  outline: { backgroundColor: 'transparent', borderColor: 'var(--color-border-default)' },
  bordered: { backgroundColor: 'var(--color-bg-surface-1)', borderColor: 'var(--color-border-strong)' },
  gradient: { backgroundColor: 'var(--color-bg-surface-1)', borderColor: 'var(--color-border-subtle)' },
};

interface CardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, style, ...props }, ref) => {
    return <div ref={ref} className={cn(cardVariants({ variant, padding }), className)} style={{ ...variantStyles[variant || 'default'], ...style }} {...props} />;
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
    <h3 ref={ref} className={cn('text-base font-semibold leading-none tracking-tight', className)} style={{ color: 'var(--color-text-primary)' }} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm leading-relaxed', className)} style={{ color: 'var(--color-text-muted)' }} {...props} />
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
    <div ref={ref} className={cn('flex items-center pt-4', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, cardVariants };
export type { CardProps };