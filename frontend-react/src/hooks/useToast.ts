import { useCallback, useEffect, useRef } from 'react';
import { useUIStore } from '../store/ui';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastOptions {
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

export function useToast() {
  const toasts = useUIStore((s) => s.toasts);
  const addToast = useUIStore((s) => s.addToast);
  const removeToast = useUIStore((s) => s.removeToast);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const toast = useCallback((options: ToastOptions) => {
    const id = addToast(options);
    const duration = options.duration ?? 4000;
    if (duration > 0) {
      const timer = setTimeout(() => removeToast(id), duration);
      timersRef.current.set(id, timer);
    }
    return id;
  }, [addToast, removeToast]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
      timersRef.current.clear();
    };
  }, []);

  return { toasts, toast, removeToast };
}
