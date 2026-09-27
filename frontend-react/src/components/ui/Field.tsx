import { createContext, useContext, useId, type ReactNode } from 'react';
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
  /**
   * Control this field labels. Optional: a field holding a single control
   * adopts it automatically, so the common case cannot ship a label that is
   * visually attached to nothing. Set it when the field holds more than one
   * control, where only one of them is the label's target.
   */
  htmlFor?: string;
}

interface FormFieldContextValue {
  /** The id the field's visible label points at, or undefined when unlabelled. */
  htmlFor: string | undefined;
  /** Id of the description the field renders, so a control can point at it. */
  descriptionId: string | undefined;
  /**
   * Id of the error-or-hint the field renders. The field is the one owner of
   * that message: a control inside it defers, so the same sentence is never
   * announced twice and never appears on screen twice.
   */
  messageId: string | undefined;
}

const FormFieldContext = createContext<FormFieldContextValue | null>(null);

/**
 * The surrounding field, or null when a control stands on its own.
 *
 * A control asks the field for the association it can give it — the id its
 * visible label points at, and the ids of the text the field itself renders —
 * and falls back to its own when there is no field. A standalone `Input` still
 * has to announce its error to a screen reader, so it keeps rendering that
 * message itself.
 *
 * The field's label target always wins over a control's own `id`, because the
 * label is what the user sees: if the two could disagree, the label would point
 * at a control that is not the one on screen.
 */
export function useField(): FormFieldContextValue | null {
  return useContext(FormFieldContext);
}

/**
 * The text ladder, in the order it is read: the label is the name of the
 * control, the description explains it, and the hint or the error closes the
 * field. The three step down the ramp one rung each, and the error takes over
 * the hint's slot rather than joining it, because two conclusions about one
 * field compete and the user can only act on one of them.
 */
export function FormField({ label, description, required, error, hint, children, className, htmlFor }: FormFieldProps) {
  const generatedId = `field-${useId()}`;
  // Without a label there is nothing for a control to point at.
  const target = label ? htmlFor ?? generatedId : undefined;
  const descriptionId = description ? `${generatedId}-description` : undefined;
  const messageId = error || hint ? `${generatedId}-message` : undefined;

  return (
    <div className={cn('w-full space-y-[var(--space-1-5)]', className)}>
      {label && (
        <Label htmlFor={target} required={required}>
          {label}
        </Label>
      )}
      {description && <p id={descriptionId} className="-mt-[var(--space-0-5)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{description}</p>}
      <FormFieldContext.Provider value={{ htmlFor: target, descriptionId, messageId }}>
        {children}
      </FormFieldContext.Provider>
      {error && <Helper id={messageId} variant="error">{error}</Helper>}
      {hint && !error && <Helper id={messageId} variant="default">{hint}</Helper>}
    </div>
  );
}
