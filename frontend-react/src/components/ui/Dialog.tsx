import { useEffect, forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

const dialogOverlayVariants = cva(
  'fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300',
  {
    variants: {
      blur: {
        true: 'backdrop-blur-sm bg-black/60',
        false: 'bg-black/60',
      },
    },
    defaultVariants: {
      blur: true,
    },
  }
);

const dialogContentVariants = cva(
  'relative w-full rounded-2xl border shadow-2xl shadow-black/50 transition-all duration-300 animate-in fade-in zoom-in-95 slide-in-from-bottom-2',
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
        default: 'border-white/[0.08] bg-[#1a1a2e]',
        glass: 'border-white/[0.06] bg-white/[0.04] backdrop-blur-xl',
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

const Dialog = forwardRef<HTMLDivElement, DialogProps>(
  ({ open, onClose, children, className, size, variant, closeOnOverlayClick = true, closeOnEscape = true, showCloseButton = true, blur = true }, ref) => {
    useEffect(() => {
      if (!open) return;

      function handleEscape(e: KeyboardEvent) {
        if (e.key === 'Escape' && closeOnEscape) {
          onClose();
        }
      }

      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
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
          className={cn(dialogContentVariants({ size, variant }), className)}
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
        >
          {showCloseButton && (
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 z-10 p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/[0.06] transition-colors"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          {children}
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
          className="absolute right-4 top-4 p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/[0.06] transition-colors"
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
  ({ className, ...props }, ref) => (
    <h2
      ref={ref}
      className={cn('text-lg font-semibold text-white leading-none tracking-tight', className)}
      {...props}
    />
  )
);
DialogTitle.displayName = 'DialogTitle';

const DialogDescription = forwardRef<HTMLParagraphElement, DialogDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-white/50 leading-relaxed', className)}
      {...props}
    />
  )
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
