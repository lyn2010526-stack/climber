import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

/**
 * A card is a border that happens to hold a surface. The border carries the
 * structure, so it is a real `--color-border-default` on every variant and it
 * is the only thing separating a card from the page behind it. The surface
 * steps up from there.
 *
 * A shadow appears only where something genuinely floats above its neighbours.
 * `--shadow-panel` is that one step; the `glass` and `gradient` names survive
 * for call sites that still pass them and resolve to the panel treatment, so
 * no frosted highlight and no gradient survives anywhere in the layer.
 */
const cardShapeVariants = cva(
  'rounded-[var(--radius-lg)] border transition-[background-color,border-color,box-shadow] duration-150 ease-out motion-reduce:transition-none',
  {
    variants: {
      variant: {
        default: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]',
        elevated: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]',
        bordered: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]',
        glass: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]',
        outline: 'border-[var(--color-border-default)] bg-transparent hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-surface-1)]',
        filled: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]',
        gradient: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]',
        interactive: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)] cursor-pointer hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-surface-2)] active:bg-[var(--color-bg-surface-3)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

/**
 * The two axes are separate CVA tables on purpose. `cardShapeVariants` owns
 * what a card *is*: a border that carries the structure, the surface it sits
 * on, and a shadow on the single rung that genuinely floats. `cardVariants` is
 * the public surface, and it answers for the interior on its own — asking it
 * for `padding` alone returns exactly the padding rung, and a bare
 * `padding: 'none'` returns an empty string.
 *
 * Folding the padding keys into the shape table cannot satisfy that: each
 * padding key would have to repeat the whole shape to stay a real card, and
 * each shape key would have to carry every padding rung to keep its default.
 * Two tables, with the public one joining them, is the only arrangement where
 * either axis answers for itself.
 */
const cardPaddingClasses = {
  none: '',
  sm: 'p-[var(--space-3)]',
  md: 'p-[var(--space-4)]',
  lg: 'p-[var(--space-6)]',
  xl: 'p-[var(--space-8)]',
} as const;

const cardPaddingVariants = cva('', {
  variants: { padding: cardPaddingClasses },
  defaultVariants: { padding: 'md' },
});

type CardPadding = keyof typeof cardPaddingClasses;
type CardShapeProps = VariantProps<typeof cardShapeVariants>;

/**
 * What a caller is allowed to ask for, and the shape of a card is still a
 * `variant`, so the existing call sites keep compiling unchanged.
 */
interface CardVariantProps extends CardShapeProps {
  padding?: CardPadding;
}

const cardVariants = (props: CardVariantProps = {}): string => {
  const { variant, padding } = props;
  if (variant === undefined) return cardPaddingVariants({ padding });
  return cn(cardShapeVariants({ variant }), cardPaddingVariants({ padding }));
};

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'color'>, CardVariantProps {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  // Both defaults are applied here rather than left to `cardVariants`: the
  // public helper answers for padding on its own, so a variant left unset has to
  // reach it as the shape it means, or the card would come out as a bare frame.
  ({ className, variant = 'default', padding = 'md', ...props }, ref) => {
    return <div ref={ref} className={cn(cardVariants({ variant, padding }), className)} {...props} />;
  }
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-[var(--space-1-5)] pb-[var(--space-4)]', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-[length:var(--text-lg)] font-semibold leading-[var(--leading-tight)] tracking-tight text-[var(--color-text-primary)]', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-[length:var(--text-sm)] leading-[var(--leading-relaxed)] text-[var(--color-text-muted)]', className)} {...props} />
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
    <div ref={ref} className={cn('flex items-center border-t border-[var(--color-border-subtle)] pt-[var(--space-4)]', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, cardVariants, cardPaddingVariants };
export type { CardProps };
