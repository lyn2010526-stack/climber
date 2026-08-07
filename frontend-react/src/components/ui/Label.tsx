import { LabelHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export function Label({ required, className, children, ...props }: LabelProps) {
  return (
    <label className={cn('block text-sm font-medium text-[var(--color-text-primary)]', className)} {...props}>
      {children}
      {required && <span className="text-[var(--color-error)] ml-0.5">*</span>}
    </label>
  );
}
