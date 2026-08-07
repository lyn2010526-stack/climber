import React, { useCallback, useEffect, useState } from 'react';
import { cn } from '../../lib/utils';
import { X, AlertCircle, CheckCircle2, Info, AlertTriangle, Loader2, XCircle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastProps {
  toast: ToastMessage;
  onClose: (id: string) => void;
}

const typeIcons = {
  success: <CheckCircle2 className="w-5 h-5" />,
  error: <XCircle className="w-5 h-5" />,
  warning: <AlertTriangle className="w-5 h-5" />,
  info: <Info className="w-5 h-5" />,
  loading: <Loader2 className="w-5 h-5 animate-spin" />,
};

const typeStyles = {
  success: {
    bg: 'bg-[var(--color-success-subtle)]',
    border: 'border-[rgba(16,185,129,0.2)]',
    iconBg: 'bg-[var(--color-success)]',
    text: 'text-[var(--color-success)]',
  },
  error: {
    bg: 'bg-[var(--color-error-subtle)]',
    border: 'border-[rgba(239,68,68,0.2)]',
    iconBg: 'bg-[var(--color-error)]',
    text: 'text-[var(--color-error)]',
  },
  warning: {
    bg: 'bg-[var(--color-warning-subtle)]',
    border: 'border-[rgba(245,158,11,0.2)]',
    iconBg: 'bg-[var(--color-warning)]',
    text: 'text-[var(--color-warning)]',
  },
  info: {
    bg: 'bg-[var(--color-accent-subtle)]',
    border: 'border-[rgba(94,106,210,0.2)]',
    iconBg: 'bg-[var(--color-accent)]',
    text: 'text-[var(--color-accent)]',
  },
  loading: {
    bg: 'bg-[var(--color-bg-surface-2)]',
    border: 'border-[var(--color-border-default)]',
    iconBg: 'bg-[var(--color-bg-surface-3)]',
    text: 'text-[var(--color-text-primary)]',
  },
};

function Toast({ toast, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [isClosing, setIsClosing] = useState(false);

  const colors = typeStyles[toast.type];

  useEffect(() => {
    if (toast.type === 'loading') return;
    const timer = setTimeout(() => {
      handleClose();
    }, toast.duration ?? 5000);
    return () => clearTimeout(timer);
  }, [toast.duration, toast.type]);

  const handleClose = useCallback(() => {
    setIsClosing(true);
    setTimeout(() => {
      setIsVisible(false);
      onClose(toast.id);
    }, 200);
  }, [toast.id, onClose]);

  if (!isVisible) return null;

  return (
    <div
      className={cn(
        'group relative flex items-start gap-3 p-4 min-w-[360px] max-w-md rounded-2xl',
        'bg-[var(--color-bg-surface-1)] border shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1)]',
        'backdrop-blur-xl',
        'animate-[fadeIn_200ms_ease-out]',
        isClosing && 'opacity-0 translate-x-4 transition-all duration-200',
        colors.bg,
        colors.border
      )}
      role="alert"
    >
      <div className={cn('absolute left-0 top-3 bottom-3 w-1 rounded-r-full', colors.iconBg)} />

      <div className={cn(
        'flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center',
        colors.iconBg
      )}>
        <div className="text-white">
          {typeIcons[toast.type]}
        </div>
      </div>

      <div className="flex-1 min-w-0 pt-0.5">
        {toast.title && (
          <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">
            {toast.title}
          </h4>
        )}
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {toast.message}
        </p>
      </div>

      {toast.action && (
        <button
          onClick={toast.action.onClick}
          className={cn(
            'px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap',
            'transition-all duration-150',
            colors.text
          )}
        >
          {toast.action.label}
        </button>
      )}

      <button
        onClick={handleClose}
        className={cn(
          'flex-shrink-0 ml-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100',
          'transition-all duration-150',
          'hover:bg-[var(--color-bg-surface-2)]',
          colors.text
        )}
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onRemove: (id: string) => void;
}

function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed z-[var(--z-toast)] top-4 right-4 flex flex-col gap-3 items-end pointer-events-none"
      style={{ zIndex: 9999 }}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast toast={toast} onClose={onRemove} />
        </div>
      ))}
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((options: Omit<ToastMessage, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: ToastMessage = { id, ...options };
    setToasts(prev => [...prev, newToast]);
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    addToast,
    removeToast,
    dismissAll,
    success: (message: string, options?: { title?: string; duration?: number }) =>
      addToast({ type: 'success', message, ...options }),
    error: (message: string, options?: { title?: string; duration?: number }) =>
      addToast({ type: 'error', message, ...options }),
    warning: (message: string, options?: { title?: string; duration?: number }) =>
      addToast({ type: 'warning', message, ...options }),
    info: (message: string, options?: { title?: string; duration?: number }) =>
      addToast({ type: 'info', message, ...options }),
    loading: (message: string, options?: { title?: string; duration?: number }) =>
      addToast({ type: 'loading', message, ...options }),
  };
}

interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </>
  );
}

export { Toast, ToastContainer };
export type { ToastMessage, ToastType };
