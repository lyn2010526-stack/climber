import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const cardVariants = cva(
  'rounded-2xl border text-foreground transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]',
  {
    variants: {
      variant: {
        default: 'border-white/[0.06] bg-white/[0.02]',
        elevated: 'border-white/[0.06] bg-white/[0.03] shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:border-white/[0.1]',
        glass: 'border-white/[0.06] bg-white/[0.03] backdrop-blur-xl shadow-lg shadow-black/20',
        outline: 'border-white/[0.08] bg-transparent hover:border-white/[0.12]',
        bordered: 'border-white/10 bg-white/[0.02] hover:bg-white/[0.04]',
        gradient: 'border-white/[0.06] bg-gradient-to-br from-white/[0.04] to-white/[0.01] hover:from-white/[0.06] hover:to-white/[0.02]',
      },
      padding: {
        none: '',
        sm: 'p-3',
        md: 'p-5',
        lg: 'p-6',
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
    <h3 ref={ref} className={cn('text-lg font-semibold leading-none tracking-tight text-white', className)} {...props} />
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
    <div ref={ref} className={cn('flex items-center pt-4', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, cardVariants };
export type { CardProps };
