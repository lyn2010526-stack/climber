import { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface HelperProps {
  children: ReactNode;
  /**
   * A hint is the quietest thing in a field: it sits under the control, in the
   * muted text role, and disappears from the reading order of a decision. The
   * outcome variants exist so a field that reports a result reports it in its
   * own status hue, and `disabled` lets a retired field say so without
   * borrowing the error hue.
   */
  variant?: 'default' | 'error' | 'success' | 'warning' | 'disabled';
  /** Id the surrounding `FormField` points its control at. */
  id?: string;
  className?: string;
}

const variantStyles = {
  default: 'text-[var(--color-text-muted)]',
  error: 'text-[var(--color-error)]',
  success: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
  disabled: 'text-[var(--color-text-disabled)]',
};

export function Helper({ children, variant = 'default', id, className }: HelperProps) {
  return <p id={id} className={cn('mt-[var(--space-1)] text-[length:var(--text-xs)]', variantStyles[variant], className)}>{children}</p>;
}
