import { useState, forwardRef, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Info, CheckCircle, AlertTriangle, AlertCircle, X } from 'lucide-react';
import { cn } from '../../lib/utils';

const alertVariants = cva(
  'relative flex gap-3 rounded-xl border p-4 transition-all duration-200',
  {
    variants: {
      variant: {
        info: 'border-sky-500/20 bg-sky-500/[0.05] text-sky-300',
        success: 'border-emerald-500/20 bg-emerald-500/[0.05] text-emerald-300',
        warning: 'border-amber-500/20 bg-amber-500/[0.05] text-amber-300',
        error: 'border-red-500/20 bg-red-500/[0.05] text-red-300',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
);

interface AlertProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {
  title?: string;
  icon?: ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
}

function getIcon(variant: string | null | undefined): ReactNode {
  switch (variant) {
    case 'success':
      return <CheckCircle className="h-5 w-5 shrink-0" />;
    case 'warning':
      return <AlertTriangle className="h-5 w-5 shrink-0" />;
    case 'error':
      return <AlertCircle className="h-5 w-5 shrink-0" />;
    default:
      return <Info className="h-5 w-5 shrink-0" />;
  }
}

const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, title, icon, dismissible, onDismiss, children, ...props }, ref) => {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    const handleDismiss = () => {
      setDismissed(true);
      onDismiss?.();
    };

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        <span className="shrink-0 mt-0.5">{icon || getIcon(variant)}</span>
        <div className="flex-1 min-w-0">
          {title && <h4 className="text-sm font-medium mb-0.5">{title}</h4>}
          <div className="text-sm opacity-80 leading-relaxed">{children}</div>
        </div>
        {dismissible && (
          <button
            type="button"
            onClick={handleDismiss}
            className="shrink-0 p-1 rounded-md opacity-60 hover:opacity-100 hover:bg-white/[0.06] transition-all"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    );
  }
);
Alert.displayName = 'Alert';

export { Alert, alertVariants };
export type { AlertProps };
