import { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface HelperProps {
  children: ReactNode;
  variant?: 'default' | 'error' | 'success' | 'warning';
  className?: string;
}

const variantStyles = {
  default: 'text-[var(--color-text-muted)]',
  error: 'text-[var(--color-error)]',
  success: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
};

export function Helper({ children, variant = 'default', className }: HelperProps) {
  return <p className={cn('text-xs mt-1', variantStyles[variant], className)}>{children}</p>;
}
