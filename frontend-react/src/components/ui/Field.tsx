import { ReactNode } from 'react';
import { Label } from './Label';
import { Helper } from './Helper';
import { cn } from '../../lib/utils';

export interface FormFieldProps {
  label?: string;
  description?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
  htmlFor?: string;
}

export function FormField({ label, description, required, error, hint, children, className, htmlFor }: FormFieldProps) {
  return (
    <div className={cn('w-full space-y-1.5', className)}>
      {label && (
        <Label htmlFor={htmlFor} required={required}>
          {label}
        </Label>
      )}
      {description && <p className="text-xs text-[var(--color-text-muted)] -mt-0.5">{description}</p>}
      {children}
      {error && <Helper variant="error">{error}</Helper>}
      {hint && !error && <Helper variant="default">{hint}</Helper>}
    </div>
  );
}
