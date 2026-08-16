import { useState, useEffect } from 'react';
import { Brain, ChevronRight, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

/* Reference: Dify `markdown-blocks/thinking-details.tsx` */
interface ThinkingDetailsProps {
  isComplete?: boolean;
  elapsedTime?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function ThinkingDetails({
  isComplete = false,
  elapsedTime,
  defaultOpen = false,
  children,
  className,
}: ThinkingDetailsProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [displayTime, setDisplayTime] = useState(0);

  useEffect(() => {
    if (!isComplete && elapsedTime !== undefined) {
      const timer = setInterval(() => {
        setDisplayTime((t) => t + 0.1);
      }, 100);
      return () => clearInterval(timer);
    }
  }, [isComplete, elapsedTime]);

  const timeLabel = isComplete
    ? `思考完成 · ${((elapsedTime || 0).toFixed(1))}s`
    : `正在思考 · ${displayTime.toFixed(1)}s`;

  return (
    <div
      className={cn('my-2 rounded-lg border overflow-hidden transition-all duration-300', className)}
      style={{ borderColor: 'var(--color-border-subtle)', backgroundColor: 'var(--color-bg-surface-2)' }}
    >
      <details
        open={isOpen}
        onToggle={(e) => {
          setIsOpen((e.target as HTMLDetailsElement).open);
        }}
      >
        <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-xs font-medium text-[var(--color-text-secondary)] select-none hover:bg-[var(--color-bg-surface-3)] transition-all duration-200 group">
          <div className="flex items-center justify-center w-5 h-5 rounded-md" style={{ backgroundColor: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
            <Brain size={12} />
          </div>
          <div className="flex items-center justify-center w-5 h-5 rounded-md">
            <ChevronRight className="size-3 transition-transform duration-300 group-open:rotate-90" />
          </div>
          <span className="flex items-center gap-1.5">
            {!isComplete && <Loader2 size={12} className="animate-spin text-[var(--color-accent)]" />}
            {timeLabel}
          </span>
        </summary>
        <div className="px-4 py-3" style={{ borderTop: '1px solid var(--color-border-subtle)', backgroundColor: 'var(--color-bg-surface-1)' }}>
          <div className="text-sm text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap font-mono text-xs">
            {children}
          </div>
        </div>
      </details>
    </div>
  );
}

export default ThinkingDetails;
