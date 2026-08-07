import React, { useEffect, useRef, useCallback, useId } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../lib/utils';
import { X } from 'lucide-react';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  className?: string;
  closeOnOverlay?: boolean;
  closeOnEsc?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'fullscreen';
  centered?: boolean;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  footer?: React.ReactNode;
  showClose?: boolean;
}

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
  fullscreen: 'max-w-full m-0 min-h-screen rounded-none',
};

const Modal = React.forwardRef<HTMLDivElement, ModalProps>(({
  open,
  onClose,
  children,
  className,
  closeOnOverlay = true,
  closeOnEsc = true,
  size = 'md',
  centered = true,
  title,
  description,
  icon,
  footer,
  showClose = true,
}, ref) => {
  void ref;
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const generatedId = useId();
  const titleId = `${generatedId}-title`;
  const descId = `${generatedId}-desc`;

  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      setTimeout(() => contentRef.current?.focus(), 0);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      previousFocusRef.current?.focus();
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && closeOnEsc) {
      onClose();
    }
    if (e.key === 'Tab' && contentRef.current) {
      const focusable = contentRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }, [closeOnEsc, onClose]);

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  return createPortal(
    <div
      ref={overlayRef}
      className={cn(
        'fixed inset-0 z-[var(--z-modal)] flex p-4',
        centered ? 'items-center justify-center' : 'items-start justify-center pt-16'
      )}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      aria-describedby={description ? descId : undefined}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-[fadeIn_200ms_ease-out]"
        onClick={(e) => { if (closeOnOverlay && e.target === overlayRef.current) onClose(); }}
        aria-hidden="true"
      />
      <div
        ref={contentRef}
        tabIndex={-1}
        className={cn(
          'relative w-full bg-[var(--color-bg-surface-1)] border border-[var(--color-border-default)]',
          'rounded-2xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.25)] max-h-[90vh] overflow-hidden flex flex-col',
          'animate-[scaleIn_200ms_cubic-bezier(0.16,1,0.3,1)]',
          sizeClasses[size],
          className
        )}
      >
        {showClose && (
          <button
            onClick={onClose}
            className="absolute top-3 right-3 z-10 p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
            aria-label="Close dialog"
          >
            <X size={16} />
          </button>
        )}
        {(title || description || icon) && (
          <div className="px-6 pt-6 pb-4 border-b border-[var(--color-border-subtle)]">
            {icon && <div className="flex justify-center mb-3">{icon}</div>}
            {title && (
              <h2 id={titleId} className="text-lg font-semibold text-[var(--color-text-primary)] text-center">
                {title}
              </h2>
            )}
            {description && (
              <p id={descId} className="mt-1 text-sm text-[var(--color-text-muted)] text-center">
                {description}
              </p>
            )}
          </div>
        )}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {children}
        </div>
        {footer && (
          <div className="px-6 py-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
});
Modal.displayName = 'Modal';

export interface ConfirmDialogProps extends Omit<ModalProps, 'children' | 'footer'> {
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  loading?: boolean;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'info',
  loading = false,
  onClose,
  ...props
}) => {
  const confirmVariant = variant === 'danger' ? 'danger' : variant === 'warning' ? 'warning' : 'primary';

  return (
    <Modal
      {...props}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            disabled={loading}
            className="h-10 px-4 text-sm font-medium rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              'h-10 px-4 text-sm font-medium rounded-xl text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
              confirmVariant === 'danger' && 'bg-[#EF4444] hover:bg-[#DC2626]',
              confirmVariant === 'warning' && 'bg-[#F59E0B] hover:bg-[#D97706]',
              confirmVariant === 'primary' && 'bg-[#5E6AD2] hover:bg-[#6E7AE3]'
            )}
          >
            {loading ? 'Loading...' : confirmText}
          </button>
        </div>
      }
    />
  );
};

const ModalHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('px-6 pt-6 pb-4 border-b border-[var(--color-border-subtle)]', className)} {...props} />
  )
);
ModalHeader.displayName = 'ModalHeader';

const ModalBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex-1 overflow-y-auto px-6 pb-6', className)} {...props} />
  )
);
ModalBody.displayName = 'ModalBody';

const ModalFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('px-6 py-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] flex items-center justify-end gap-2', className)} {...props} />
  )
);
ModalFooter.displayName = 'ModalFooter';

export { Modal, ConfirmDialog, ModalHeader, ModalBody, ModalFooter };
