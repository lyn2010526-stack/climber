import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { icons, iconSizes, type IconSizeName } from '../../lib/icons';
import { cn } from '../../lib/utils';

/**
 * Codex CLI's control language, in the same order of commitment the CLI itself
 * uses them: exactly one saturated element per view, every other action steps
 * down through surface, border and finally nothing at all.
 *
 * Two rules hold across the whole table.
 *
 * The accent owns a real press. `primary` moves accent -> accent-hover ->
 * accent-active, and those three tokens are distinct values in both themes, so
 * a press reads as motion instead of a repaint of the same fill.
 *
 * A disabled control is described by tokens rather than by a blanket opacity.
 * `--color-bg-disabled` recedes the surface and `--color-text-disabled` drops
 * the label a step down the text ramp, which keeps a disabled action
 * distinguishable from an enabled one that happens to be quiet.
 */
const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-[var(--control-gap)] whitespace-nowrap font-medium select-none',
    'transition-[color,background-color,border-color,box-shadow] duration-150 ease-out motion-reduce:transition-none',
    // The focus indicator is the shared two-layer ring: a page-coloured gap
    // then the accent, so it stays visible on both the accent fill of a primary
    // button and the page surface behind a ghost one.
    'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
    'disabled:cursor-not-allowed',
  ],
  {
    variants: {
      variant: {
        primary: [
          'bg-[var(--color-accent)] text-[var(--color-accent-text)]',
          'hover:bg-[var(--color-accent-hover)]',
          'active:bg-[var(--color-accent-active)]',
          // A receded fill and a dropped label: the button keeps its shape so
          // the row does not reflow, while nothing about it invites a press.
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)]',
        ],
        secondary: [
          'bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] border border-[var(--color-border-default)]',
          'hover:bg-[var(--color-bg-surface-2)] hover:border-[var(--color-border-strong)]',
          'active:bg-[var(--color-bg-surface-3)] active:border-[var(--color-border-strong)]',
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
        ],
        outline: [
          'border border-[var(--color-border-default)] bg-transparent text-[var(--color-text-primary)]',
          'hover:bg-[var(--color-bg-surface-1)] hover:border-[var(--color-border-strong)]',
          'active:bg-[var(--color-bg-surface-2)]',
          'disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
        ],
        ghost: [
          'bg-transparent text-[var(--color-text-secondary)]',
          'hover:bg-[var(--color-bg-surface-1)] hover:text-[var(--color-text-primary)]',
          'active:bg-[var(--color-bg-surface-2)]',
          'disabled:text-[var(--color-text-disabled)]',
        ],
        // A filled wash for a low-commitment action that still needs to read as
        // an object next to the ghost buttons around it.
        subtle: [
          'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]',
          'hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]',
          'active:bg-[var(--color-bg-surface-4)]',
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)]',
        ],
        // Status tones only for actions that themselves report a state (retry
        // after a failure, confirm a success). Error reads text-first so the
        // label never depends on hue alone. `danger` is the same treatment
        // under the name the overlay layer uses for a destructive action.
        destructive: [
          'border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]',
          'hover:bg-[var(--color-error)]/20 active:bg-[var(--color-error)]/30',
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
        ],
        danger: [
          'border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]',
          'hover:bg-[var(--color-error)]/20 active:bg-[var(--color-error)]/30',
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
        ],
        success: [
          'border border-[var(--color-success)]/30 bg-[var(--color-success-subtle)] text-[var(--color-success)]',
          'hover:bg-[var(--color-success)]/20 active:bg-[var(--color-success)]/30',
          'disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)] disabled:border-[var(--color-border-subtle)]',
        ],
        link: [
          'bg-transparent text-[var(--color-accent-foreground)] underline-offset-[var(--space-1)] hover:underline',
          'active:text-[var(--color-accent)]',
          'disabled:text-[var(--color-text-disabled)] disabled:no-underline',
        ],
      },
      size: {
        xs: 'h-[var(--control-height-xs)] px-[var(--space-2-5)] text-[length:var(--text-xs)] rounded-[var(--radius-sm)]',
        sm: 'h-[var(--control-height-sm)] px-[var(--space-3)] text-[length:var(--text-xs)] rounded-[var(--radius-md)]',
        md: 'h-[var(--control-height-md)] px-[var(--space-4)] text-[length:var(--text-sm)] rounded-[var(--radius-md)]',
        lg: 'h-[var(--control-height-lg)] px-[var(--space-5)] text-[length:var(--text-sm)] rounded-[var(--radius-md)]',
        icon: 'h-[var(--control-height-md)] w-[var(--control-height-md)] rounded-[var(--radius-md)] p-0',
        'icon-sm': 'h-[var(--control-height-sm)] w-[var(--control-height-sm)] rounded-[var(--radius-md)] p-0',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

/**
 * A control's glyph takes the rung of the same name, so `size="md"` carries a
 * 16px icon. Icon-only buttons are sized by their own box instead, so they
 * borrow the rung that matches that box.
 */
const iconSizeForControl = (size: ButtonSize): IconSizeName => {
  switch (size) {
    case 'icon':
      return 'md';
    case 'icon-sm':
      return 'sm';
    case 'xs':
    case 'sm':
    case 'md':
    case 'lg':
      return size;
    default:
      return 'md';
  }
};

type ButtonSize = NonNullable<VariantProps<typeof buttonVariants>['size']>;

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean;
  icon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, icon, type = 'button', ...props }, ref) => {
    const resolvedSize = size ?? 'md';
    // Keep the label mounted so a pending button retains its accessible name
    // and width instead of collapsing while the spinner runs.
    const glyphSize = iconSizes[iconSizeForControl(resolvedSize)];
    // A pending button is disabled by the same attribute a caller sets, so the
    // disabled tokens apply and the control cannot fire a second request.
    const isDisabled = Boolean(disabled) || Boolean(loading);

    return (
      <button
        type={type}
        className={cn(buttonVariants({ variant, size }), 'disabled:pointer-events-none', className)}
        ref={ref}
        disabled={isDisabled}
        {...props}
        aria-busy={loading || props['aria-busy']}
      >
        {loading ? (
          <icons.loading size={glyphSize} className="shrink-0 animate-spin motion-reduce:animate-none" aria-hidden="true" focusable="false" />
        ) : (
          icon
        )}
        {children != null && <span>{children}</span>}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
export type { ButtonProps };
