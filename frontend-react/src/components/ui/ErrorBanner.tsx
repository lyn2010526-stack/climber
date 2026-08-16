import { AlertCircle, RefreshCw } from 'lucide-react';

export interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBanner({ message, onRetry, className }: ErrorBannerProps) {
  return (
    <div className={`rounded-2xl p-4 mb-6 flex items-center gap-3 ${className ?? ''}`} style={{ backgroundColor: 'var(--color-error-subtle)', border: '1px solid var(--color-error)' }}>
      <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
      <p className="text-sm text-[var(--color-error)] flex-1">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
          aria-label="重试"
        >
          <RefreshCw size={14} />
          重试
        </button>
      )}
    </div>
  );
}
