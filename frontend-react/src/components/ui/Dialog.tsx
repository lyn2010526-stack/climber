import { createContext, forwardRef, useContext, useEffect, useId, useRef } from 'react';
import { cva } from 'class-variance-authority';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

const dialogOverlayVariants = cva(
  'fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-200',
  {
    variants: {
      blur: {
        true: 'backdrop-blur-[2px] bg-black/45',
        false: 'bg-black/45',
      },
    },
    defaultVariants: {
      blur: true,
    },
  }
);

const dialogContentVariants = cva(
  'relative w-full rounded-xl border shadow-[var(--shadow-lg)] transition-all duration-200 animate-in fade-in zoom-in-95 slide-in-from-bottom-2',
  {
    variants: {
      size: {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-lg',
        xl: 'max-w-xl',
        full: 'max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]',
      },
      variant: {
        default: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)]',
        glass: 'border-[var(--color-glass-border)] bg-[var(--color-glass-bg)] backdrop-blur-xl',
      },
    },
    defaultVariants: {
      size: 'md',
      variant: 'default',
    },
  }
);

interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  variant?: 'default' | 'glass';
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
  blur?: boolean;
}

interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  showClose?: boolean;
  onClose?: () => void;
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

interface DialogDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

interface DialogContextValue {
  titleId: string;
  descriptionId: string;
}

const DialogContext = createContext<DialogContextValue | null>(null);

const focusableSelector = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const Dialog = forwardRef<HTMLDivElement, DialogProps>(
  ({ open, onClose, children, className, size, variant, closeOnOverlayClick = true, closeOnEscape = true, showCloseButton = true, blur = true }, ref) => {
    const contentRef = useRef<HTMLDivElement>(null);
    const restoreFocusRef = useRef<HTMLElement | null>(null);
    const titleId = useId();
    const descriptionId = useId();

    useEffect(() => {
      if (!open) return;

      restoreFocusRef.current = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

      function handleKeyDown(e: KeyboardEvent) {
        if (e.key === 'Escape' && closeOnEscape) {
          onClose();
          return;
        }
        if (e.key !== 'Tab' || !contentRef.current) return;

        const focusableElements = Array.from(
          contentRef.current.querySelectorAll<HTMLElement>(focusableSelector)
        );
        if (focusableElements.length === 0) {
          e.preventDefault();
          contentRef.current.focus();
          return;
        }

        const firstElement = focusableElements[0]!;
        const lastElement = focusableElements[focusableElements.length - 1]!;
        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }

      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
      const focusableElement = contentRef.current?.querySelector<HTMLElement>(focusableSelector);
      (focusableElement ?? contentRef.current)?.focus();

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = '';
        restoreFocusRef.current?.focus();
      };
    }, [open, closeOnEscape, onClose]);

    if (!open) return null;

    return (
      <div
        ref={ref}
        className={cn(dialogOverlayVariants({ blur }))}
        onClick={closeOnOverlayClick ? onClose : undefined}
      >
        <div
          ref={contentRef}
          className={cn(dialogContentVariants({ size, variant }), className)}
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          tabIndex={-1}
        >
          <DialogContext.Provider value={{ titleId, descriptionId }}>
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className="absolute right-4 top-4 z-10 p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
                aria-label="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            )}
            {children}
          </DialogContext.Provider>
        </div>
      </div>
    );
  }
);
Dialog.displayName = 'Dialog';

const DialogHeader = forwardRef<HTMLDivElement, DialogHeaderProps>(
  ({ className, showClose, onClose, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col gap-1.5 p-6 pb-2', className)}
      {...props}
    >
      {showClose && onClose && (
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
          aria-label="关闭"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      {props.children}
    </div>
  )
);
DialogHeader.displayName = 'DialogHeader';

const DialogTitle = forwardRef<HTMLHeadingElement, DialogTitleProps>(
  ({ className, id, ...props }, ref) => {
    const context = useContext(DialogContext);
    return (
      <h2
        ref={ref}
        id={id ?? context?.titleId}
        className={cn('text-lg font-semibold text-[var(--color-text-primary)] leading-none tracking-tight', className)}
        {...props}
      />
    );
  }
);
DialogTitle.displayName = 'DialogTitle';

const DialogDescription = forwardRef<HTMLParagraphElement, DialogDescriptionProps>(
  ({ className, id, ...props }, ref) => {
    const context = useContext(DialogContext);
    return (
      <p
        ref={ref}
        id={id ?? context?.descriptionId}
        className={cn('text-sm text-[var(--color-text-secondary)] leading-relaxed', className)}
        {...props}
      />
    );
  }
);
DialogDescription.displayName = 'DialogDescription';

const DialogBody = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('px-6 py-4', className)}
      {...props}
    />
  )
);
DialogBody.displayName = 'DialogBody';

const DialogFooter = forwardRef<HTMLDivElement, DialogFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center justify-end gap-3 p-6 pt-2', className)}
      {...props}
    />
  )
);
DialogFooter.displayName = 'DialogFooter';

export { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogBody, DialogFooter, dialogOverlayVariants, dialogContentVariants };
export type { DialogProps, DialogHeaderProps, DialogTitleProps, DialogDescriptionProps, DialogFooterProps };
