import { AlertCircle, RotateCcw, X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ErrorMessageProps {
  error: string;
  onRetry?: (() => void) | undefined;
  onDismiss?: (() => void) | undefined;
  retryCount?: number;
  maxRetries?: number;
}

export function ErrorMessage({
  error,
  onRetry,
  onDismiss,
  retryCount = 0,
  maxRetries = 3,
}: ErrorMessageProps) {
  const canRetry = retryCount < maxRetries;

  return (
    <div
      className="mx-auto max-w-md px-4 py-3 rounded-2xl border flex items-start gap-3 fade-enter"
      style={{
        backgroundColor: 'var(--color-error-subtle)',
        borderColor: 'var(--color-error)/20',
      }}
      role="alert"
    >
      <AlertCircle size={18} className="text-[var(--color-error)] shrink-0 mt-0.5" />

      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--color-error)] leading-relaxed">{error}</p>

        <div className="flex items-center gap-2 mt-2.5">
          {canRetry && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              style={{
                backgroundColor: 'var(--color-error)/20',
                color: 'var(--color-error)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-error)/30';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-error)/20';
              }}
            >
              <RotateCcw size={11} />
              重试 ({retryCount}/{maxRetries})
            </button>
          )}

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="px-3 py-1.5 rounded-lg text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            >
              忽略
            </button>
          )}
        </div>
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors shrink-0"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
