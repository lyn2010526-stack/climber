import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const timelineVariants = cva('relative', {
  variants: {
    variant: {
      default: '',
      dotted: '',
      solid: '',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
});

const timelineItemVariants = cva('relative flex gap-4 pb-6 last:pb-0', {
  variants: {
    align: {
      left: '',
      right: '',
      alternate: '',
    },
  },
  defaultVariants: {
    align: 'left',
  },
});

const dotVariants = cva(
  'relative z-10 flex h-3 w-3 shrink-0 items-center justify-center rounded-full ring-4 ring-[var(--color-bg-page)] mt-1',
  {
    variants: {
      status: {
        default: 'bg-white/40',
        success: 'bg-emerald-500',
        warning: 'bg-amber-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        pending: 'bg-violet-500',
      },
      size: {
        sm: 'h-2.5 w-2.5',
        md: 'h-3 w-3',
        lg: 'h-4 w-4',
      },
    },
    defaultVariants: {
      status: 'default',
      size: 'md',
    },
  }
);

const lineVariants = cva('absolute left-[5.5px] top-4 bottom-0 w-px', {
  variants: {
    variant: {
      default: 'bg-white/[0.08]',
      dotted: 'border-l border-dashed border-white/[0.12]',
      solid: 'bg-white/[0.12]',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
});

interface TimelineProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof timelineVariants> {
  children: React.ReactNode;
}

interface TimelineItemProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof timelineItemVariants> {
  children: React.ReactNode;
}

interface TimelineDotProps extends VariantProps<typeof dotVariants> {
  icon?: React.ReactNode;
  className?: string;
}

interface TimelineContentProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  timestamp?: string;
}

interface TimelineSeparatorProps extends VariantProps<typeof lineVariants> {
  className?: string;
}

const Timeline = forwardRef<HTMLDivElement, TimelineProps>(
  ({ className, variant, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn(timelineVariants({ variant }), className)} {...props}>
        {children}
      </div>
    );
  }
);
Timeline.displayName = 'Timeline';

const TimelineItem = forwardRef<HTMLDivElement, TimelineItemProps>(
  ({ className, align, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn(timelineItemVariants({ align }), className)} {...props}>
        {children}
      </div>
    );
  }
);
TimelineItem.displayName = 'TimelineItem';

const TimelineDot = forwardRef<HTMLDivElement, TimelineDotProps>(
  ({ className, status, size, icon, ...props }, ref) => {
    return (
      <div ref={ref} className={cn(dotVariants({ status, size }), className)} {...props}>
        {icon && <span className="flex h-2 w-2 items-center justify-center text-white">{icon}</span>}
      </div>
    );
  }
);
TimelineDot.displayName = 'TimelineDot';

const TimelineLine = forwardRef<HTMLDivElement, TimelineSeparatorProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div ref={ref} className={cn(lineVariants({ variant }), className)} {...props} />
    );
  }
);
TimelineLine.displayName = 'TimelineLine';

const TimelineContent = forwardRef<HTMLDivElement, TimelineContentProps>(
  ({ className, title, description, timestamp, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('flex-1 min-w-0', className)} {...props}>
        {(title || timestamp) && (
          <div className="flex items-center justify-between gap-2 mb-1">
            {title && <h4 className="text-sm font-medium text-white">{title}</h4>}
            {timestamp && <span className="text-xs text-white/40 shrink-0">{timestamp}</span>}
          </div>
        )}
        {description && <p className="text-sm text-white/60 leading-relaxed">{description}</p>}
        {children}
      </div>
    );
  }
);
TimelineContent.displayName = 'TimelineContent';

export { Timeline, TimelineItem, TimelineDot, TimelineLine, TimelineContent, timelineVariants, timelineItemVariants, dotVariants, lineVariants };
export type { TimelineProps, TimelineItemProps, TimelineDotProps, TimelineContentProps, TimelineSeparatorProps };
