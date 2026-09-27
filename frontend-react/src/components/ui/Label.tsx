import { LabelHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
  /**
   * A label has to be readable, and it has to step below the value it names.
   * `--color-text-secondary` is the rung that does both: darker than the
   * control's own text, lighter than a heading.
   */
  tone?: 'default' | 'muted' | 'disabled';
}

const toneStyles = {
  default: 'text-[var(--color-text-secondary)]',
  muted: 'text-[var(--color-text-muted)]',
  disabled: 'text-[var(--color-text-disabled)]',
};

export function Label({ required, tone = 'default', className, children, ...props }: LabelProps) {
  return (
    <label className={cn('block font-medium text-[length:var(--text-sm)]', toneStyles[tone], className)} {...props}>
      {children}
      {required && <span aria-hidden="true" className="ml-[var(--space-0-5)] text-[var(--color-error)]">*</span>}
    </label>
  );
}
