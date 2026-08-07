import React from 'react';
import { cn } from '../../lib/utils';
import { Loader2 } from 'lucide-react';

export interface LoadingOverlayProps {
  message?: string;
  spinner?: React.ReactNode;
  blur?: boolean;
  transparent?: boolean;
  className?: string;
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  message = 'Loading...',
  spinner,
  blur = true,
  transparent = false,
  className,
}) => {
  return (
    <div
      className={cn(
        'absolute inset-0 z-[var(--z-overlay)] flex flex-col items-center justify-center gap-[var(--space-3)]',
        blur && 'backdrop-blur-sm',
        transparent ? 'bg-[var(--surface-bg)]/50' : 'bg-[var(--surface-bg)]/80',
        'animate-[fadeIn_200ms_ease-out]',
        className
      )}
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      {spinner || (
        <div className="relative">
          <div className="w-10 h-10 rounded-full border-[3px] animate-spin" style={{
            borderColor: 'var(--border-subtle)',
            borderTopColor: 'var(--accent)',
          }} />
        </div>
      )}
      {message && (
        <span className="text-[var(--font-size-sm)] text-[var(--text-muted)] font-medium">{message}</span>
      )}
    </div>
  );
};

interface InlineSpinnerProps {
  size?: number;
  className?: string;
  message?: string;
}

const InlineSpinner: React.FC<InlineSpinnerProps> = ({ size = 16, className, message }) => (
  <span className={cn('inline-flex items-center gap-[var(--space-2)]', className)} role="status" aria-label={message || 'Loading'}>
    <Loader2 size={size} className="animate-spin text-[var(--accent)]" />
    {message && <span className="text-[var(--font-size-sm)] text-[var(--text-muted)]">{message}</span>}
  </span>
);

export { LoadingOverlay, InlineSpinner };
