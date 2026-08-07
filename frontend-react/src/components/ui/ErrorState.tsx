import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryText?: string;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = '加载失败',
  message = '发生了意外错误，请稍后重试。',
  onRetry,
  retryText = '重试',
  className,
}) => {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-16 px-6 text-center',
      className
    )}>
      <div className="w-14 h-14 rounded-2xl bg-[var(--color-error-subtle)] flex items-center justify-center mb-4">
        <AlertCircle size={24} className="text-[var(--color-error)]" />
      </div>
      <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-1.5">{title}</h3>
      <p className="text-sm text-[var(--color-text-muted)] max-w-sm leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] rounded-xl text-sm font-medium hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)] transition-all duration-200 active:scale-[0.97]"
        >
          <RefreshCw size={14} />
          {retryText}
        </button>
      )}
    </div>
  );
};

export default ErrorState;
