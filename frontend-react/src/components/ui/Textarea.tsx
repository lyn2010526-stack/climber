import { useRef, useEffect, forwardRef, TextareaHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';
import { AlertCircle } from 'lucide-react';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
  hint?: string;
  autoSize?: boolean;
  minRows?: number;
  maxRows?: number;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ error, hint, autoSize = false, minRows = 3, maxRows = 10, className, onChange, ...props }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement>(null);

    const textareaRef = (node: HTMLTextAreaElement | null) => {
      (internalRef as React.MutableRefObject<HTMLTextAreaElement | null>).current = node;
      if (typeof ref === 'function') ref(node);
      else if (ref) (ref as React.MutableRefObject<HTMLTextAreaElement | null>).current = node;
    };

    useEffect(() => {
      if (!autoSize) return;
      const el = internalRef.current;
      if (!el) return;
      el.style.height = 'auto';
      const lineHeight = parseInt(getComputedStyle(el).lineHeight) || 20;
      const minHeight = lineHeight * minRows;
      const maxHeight = lineHeight * maxRows;
      const newHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
      el.style.height = `${newHeight}px`;
      el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
    });

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      if (autoSize) {
        const el = e.target;
        el.style.height = 'auto';
        const lineHeight = parseInt(getComputedStyle(el).lineHeight) || 20;
        const minHeight = lineHeight * minRows;
        const maxHeight = lineHeight * maxRows;
        const newHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
        el.style.height = `${newHeight}px`;
        el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
      }
      onChange?.(e);
    };

    return (
      <div className="w-full">
        <textarea
          ref={textareaRef}
          className={cn(
            'w-full rounded-lg border bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] text-sm',
            'placeholder:text-[var(--color-text-muted)] transition-all duration-150 resize-none',
            'px-3 py-2.5',
            'hover:border-[var(--color-border-default)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]',
            error && 'border-[var(--color-error)] focus:ring-[var(--color-error)]/20 focus:border-[var(--color-error)]',
            !error && 'border-[var(--color-border-default)]',
            className
          )}
          rows={minRows}
          onChange={handleChange}
          {...props}
        />
        {error && <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1"><AlertCircle size={10} />{error}</p>}
        {hint && !error && <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">{hint}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
