// @ts-nocheck
import React, { useState, useEffect } from 'react';
import {
  AlertCircle, AlertTriangle, Info, X, RefreshCw, ChevronDown,
  ChevronRight, Wifi, WifiOff, ShieldAlert,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

/* ─── Toast Notification ─── */
interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  description?: string;
  duration?: number;
  onClose: () => void;
  action?: { label: string; onClick: () => void };
}

const TOAST_ICONS = {
  success: Info,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const TOAST_COLORS = {
  success: { bg: 'var(--color-success-subtle)', border: 'var(--color-success)/20', text: 'var(--color-success)' },
  error: { bg: 'var(--color-error-subtle)', border: 'var(--color-error)/20', text: 'var(--color-error)' },
  warning: { bg: 'var(--color-warning-subtle)', border: 'var(--color-warning)/20', text: 'var(--color-warning)' },
  info: { bg: 'var(--color-info-subtle)', border: 'var(--color-info)/20', text: 'var(--color-info)' },
};

export function Toast({ type, title, description, duration = 5000, onClose, action }: ToastProps) {
  const [progress, setProgress] = useState(100);
  const Icon = TOAST_ICONS[type];
  const colors = TOAST_COLORS[type];

  useEffect(() => {
    if (duration <= 0) return;
    const interval = 50;
    const step = (interval / duration) * 100;
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= 0) {
          clearInterval(timer);
          onClose();
          return 0;
        }
        return prev - step;
      });
    }, interval);
    return () => clearInterval(timer);
  }, [duration, onClose]);

  return (
    <div
      className="flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-xl fade-enter max-w-sm relative overflow-hidden"
      style={{ backgroundColor: colors.bg, borderColor: colors.border }}
      role="alert"
      aria-live="polite"
    >
      <Icon size={16} className="shrink-0 mt-0.5" style={{ color: colors.text }} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-[var(--color-text-primary)]">{title}</p>
        {description && <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{description}</p>}
        {action && (
          <button onClick={action.onClick} className="text-[10px] font-medium mt-1.5 underline underline-offset-2" style={{ color: colors.text }}>
            {action.label}
          </button>
        )}
      </div>
      <button onClick={onClose} className="p-1 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors shrink-0" aria-label="关闭通知">
        <X size={12} />
      </button>
      <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-xl overflow-hidden" style={{ backgroundColor: 'var(--color-border-subtle)' }}>
        <div className="h-full transition-all duration-50" style={{ width: `${progress}%`, backgroundColor: colors.text }} />
      </div>
    </div>
  );
}

/* ─── Toast Container ─── */
export function ToastContainer({ toasts, onRemove }: { toasts: Array<{ id: string; type: 'success' | 'error' | 'warning' | 'info'; title: string; description?: string }>; onRemove: (id: string) => void }) {
  return (
    <div className="fixed top-4 right-4 z-[var(--z-overlay)] flex flex-col gap-2">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          type={toast.type}
          title={toast.title}
          description={toast.description ?? ''}
          onClose={() => onRemove(toast.id)}
        />
      ))}
    </div>
  );
}

/* ─── Error Boundary ─── */
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex items-center justify-center h-full p-8">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-[var(--color-error-subtle)] flex items-center justify-center mx-auto mb-4">
              <ShieldAlert size={28} className="text-[var(--color-error)]" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">出错了</h3>
            <p className="text-sm text-[var(--color-text-muted)] mb-4">
              {this.state.error?.message || '发生未知错误'}
            </p>
            <div className="flex items-center justify-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => this.setState({ hasError: false, error: null })}>
                <RefreshCw size={14} />
                重试
              </Button>
              <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/* ─── Network Status Banner ─── */
export function NetworkStatusBanner() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowBanner(true);
      setTimeout(() => setShowBanner(false), 3000);
    };
    const handleOffline = () => {
      setIsOnline(false);
      setShowBanner(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (!showBanner && isOnline) return null;

  return (
    <div
      className={cn(
        'fixed top-0 left-0 right-0 z-[var(--z-overlay)] flex items-center justify-center gap-2 py-2 text-xs font-medium transition-all duration-300',
        isOnline ? 'bg-[var(--color-success)] text-white' : 'bg-[var(--color-error)] text-white'
      )}
      role="status"
    >
      {isOnline ? (
        <>
          <Wifi size={14} />
          网络已恢复
        </>
      ) : (
        <>
          <WifiOff size={14} />
          网络连接已断开
        </>
      )}
    </div>
  );
}

/* ─── Inline Error with Retry ─── */
interface InlineErrorProps {
  error: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  retryCount?: number;
  maxRetries?: number;
}

export function InlineError({ error, onRetry, onDismiss, retryCount = 0, maxRetries = 3 }: InlineErrorProps) {
  const canRetry = onRetry && retryCount < maxRetries;

  return (
    <div
      className="flex items-start gap-3 p-4 rounded-xl border fade-enter"
      style={{ backgroundColor: 'var(--color-error-subtle)', borderColor: 'var(--color-error)/20' }}
      role="alert"
    >
      <AlertCircle size={16} className="text-[var(--color-error)] shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[var(--color-error)] leading-relaxed">{error}</p>
        {canRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 mt-2 px-3 py-1.5 rounded-lg text-[10px] font-medium bg-[var(--color-error)]/20 text-[var(--color-error)] hover:bg-[var(--color-error)]/30 transition-colors"
          >
            <RefreshCw size={10} />
            重试 ({retryCount}/{maxRetries})
          </button>
        )}
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="p-1 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors shrink-0">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

/* ─── Loading Skeleton ─── */
export function MessageSkeleton() {
  return (
    <div className="flex gap-3 max-w-[85%] message-enter">
      <div className="w-8 h-8 rounded-xl bg-[var(--color-bg-surface-2)] animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-3/4 rounded-full skeleton-shimmer" />
        <div className="h-3 w-1/2 rounded-full skeleton-shimmer" style={{ animationDelay: '100ms' }} />
        <div className="h-3 w-2/3 rounded-full skeleton-shimmer" style={{ animationDelay: '200ms' }} />
      </div>
    </div>
  );
}

/* ─── Degraded Mode Banner ─── */
export function DegradedModeBanner({ features }: { features: string[] }) {
  const [expanded, setExpanded] = useState(false);

  if (features.length === 0) return null;

  return (
    <div className="px-4 py-2 border-b border-[var(--color-warning)]/20 bg-[var(--color-warning-subtle)]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 text-xs text-[var(--color-warning)]"
        aria-expanded={expanded}
      >
        <AlertTriangle size={12} />
        <span className="flex-1 text-left">部分功能暂不可用</span>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {expanded && (
        <ul className="mt-2 ml-5 space-y-1 slide-down">
          {features.map((f) => (
            <li key={f} className="text-[10px] text-[var(--color-text-muted)]">• {f}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
