import { useState, useEffect } from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
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
    ? `Thought(${((elapsedTime || 0).toFixed(1))}s)`
    : `Thinking(${displayTime.toFixed(1)}s)`;

  return (
    <div
      className={cn('my-3 rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden transition-all duration-300', className)}
    >
      <details
        {...{ open: isOpen || isComplete }}
        onToggle={(e) => {
          if (!isComplete) {
            setIsOpen((e.target as HTMLDetailsElement).open);
          }
        }}
      >
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-xs font-medium text-gray-400 select-none hover:bg-white/5 transition-all duration-200 group">
          <div className="flex items-center justify-center w-5 h-5 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors duration-200">
            <ChevronRight className="size-3 transition-transform duration-300 group-open:rotate-90" />
          </div>
          <span className="flex items-center gap-1.5">
            {!isComplete && <Loader2 size={12} className="animate-spin text-blue-400" />}
            {timeLabel}
          </span>
        </summary>
        <div className="border-t border-white/5 bg-white/[0.01] px-4 py-3">
          <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap font-mono text-xs">
            {children}
          </div>
        </div>
      </details>
    </div>
  );
}

export default ThinkingDetails;
