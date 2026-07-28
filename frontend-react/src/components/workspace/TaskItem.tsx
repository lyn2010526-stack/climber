import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { Check, X, ChevronRight } from 'lucide-react';

const taskItemVariants = cva(
  'flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-3 transition-all duration-200 hover:border-border-subtle',
  {
    variants: {
      status: {
        pending: 'opacity-60',
        running: 'border-accent/50 bg-accent/5',
        completed: 'border-success/30 bg-success/5',
        failed: 'border-destructive/30 bg-destructive/5',
      },
    },
    defaultVariants: {
      status: 'pending',
    },
  }
);

interface TaskItemProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof taskItemVariants> {
  title: string;
  description?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

const TaskItem = React.forwardRef<HTMLDivElement, TaskItemProps>(
  ({ className, status, title, description, onRetry, onDismiss, ...props }, ref) => {
    const statusConfig = {
      pending: { icon: <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />, label: 'Pending' },
      running: { icon: <div className="h-4 w-4 rounded-full border-2 border-accent border-t-transparent animate-spin" />, label: 'Running' },
      completed: { icon: <Check className="h-4 w-4 text-success" />, label: 'Completed' },
      failed: { icon: <X className="h-4 w-4 text-destructive" />, label: 'Failed' },
    };

    const config = statusConfig[status || 'pending'];

    return (
      <div ref={ref} className={cn(taskItemVariants({ status }), className)} {...props}>
        <div className="mt-0.5">{config.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-foreground truncate">{title}</div>
          {description && <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{description}</div>}
        </div>
        <div className="flex items-center gap-1">
          {status === 'failed' && onRetry && (
            <button
              onClick={onRetry}
              className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Retry"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    );
  }
);
TaskItem.displayName = 'TaskItem';

export { TaskItem, taskItemVariants };
export type { TaskItemProps };
