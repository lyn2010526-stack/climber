import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { forwardRef } from 'react';

/**
 * The eight-tone status vocabulary has exactly seven resting shapes: every tone
 * except `loading`, which is motion and so cannot be a label. Each of those
 * seven gets a variant here, so a badge can always report the state its
 * `StatusIcon` reports and no call site has to hand-pick a colour pair.
 *
 * Two states sit next to each other in the list and must stay apart.
 * `unknown` means the backend never reported a value, and takes a dashed
 * border over the muted wash. `disabled` means the value exists and the control
 * is switched off, and takes a recessed surface with no hue at all. They share
 * a grey, so the border style and the presence of a wash are what separate
 * them, and both survive a monochrome rendering.
 */
const badgeVariants = cva(
  'inline-flex items-center gap-[var(--control-gap-compact)] font-medium transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
  {
    variants: {
      variant: {
        default: 'border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]',
        secondary: 'border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]',
        primary: 'border border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]',
        success: 'border border-[var(--color-success)]/30 bg-[var(--color-success-subtle)] text-[var(--color-success)]',
        warning: 'border border-[var(--color-warning)]/30 bg-[var(--color-warning-subtle)] text-[var(--color-warning)]',
        destructive: 'border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]',
        info: 'border border-[var(--color-info)]/30 bg-[var(--color-info-subtle)] text-[var(--color-info)]',
        // Waiting for a slot: no hue of its own, one step above a disabled
        // chip, because the work is real and has not started yet.
        queued: 'border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-disabled)]',
        // Parked on a human decision. The accent is the colour the workbench
        // already uses for "the run is waiting on you".
        approval: 'border border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]',
        // "Not reported" and inactive look alike at a glance, so unknown keeps
        // its own hue pair and a dashed edge instead of borrowing the disabled
        // treatment.
        unknown: 'border border-dashed border-[var(--color-unknown)]/40 bg-[var(--color-unknown-subtle)] text-[var(--color-unknown)]',
        // The value is known and the control is off: no hue, no wash, and the
        // label one full step down the text ramp.
        disabled: 'border border-[var(--color-border-subtle)] bg-transparent text-[var(--color-text-disabled)]',
        outline: 'border border-[var(--color-border-default)] bg-transparent text-[var(--color-text-secondary)]',
      },
      size: {
        xs: 'px-[var(--space-1-5)] py-[var(--space-0-5)] text-[length:var(--text-2xs)]',
        sm: 'px-[var(--space-2)] py-[var(--space-0-5)] text-[length:var(--text-xs)]',
        md: 'px-[var(--space-2-5)] py-[var(--space-0-5)] text-[length:var(--text-xs)]',
      },
      /**
       * The pill is reserved. A status chip or a filter chip reads as a token
       * the user can pick out of a row, and a full-radius end says exactly
       * that; a prose badge keeps the tighter radius so it never looks
       * clickable. Opt in per call site rather than by variant, so the
       * exception stays visible where it is used.
       */
      shape: {
        default: 'rounded-[var(--radius-sm)]',
        pill: 'rounded-[var(--radius-pill)]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
      shape: 'default',
    },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode;
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(({ className, variant, size, shape, icon, children, ...props }, ref) => {
  return (
    <span ref={ref} className={cn(badgeVariants({ variant, size, shape }), className)} {...props}>
      {icon}
      {children}
    </span>
  );
});
Badge.displayName = 'Badge';

export { Badge, badgeVariants };
export type { BadgeProps };
