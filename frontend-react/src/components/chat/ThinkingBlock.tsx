import { useState, useEffect } from 'react';
import { ChevronRight, Brain, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ThinkingBlockProps {
  content?: string;
  isComplete?: boolean;
  elapsedTime?: number;
  defaultOpen?: boolean;
  className?: string;
}

export function ThinkingBlock({
  content,
  isComplete = false,
  elapsedTime,
  defaultOpen = false,
  className,
}: ThinkingBlockProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen || !isComplete);
  const [displayTime, setDisplayTime] = useState(0);

  useEffect(() => {
    if (!isComplete) {
      const timer = setInterval(() => {
        setDisplayTime((t) => t + 0.1);
      }, 100);
      return () => clearInterval(timer);
    }
  }, [isComplete]);

  const timeLabel = isComplete
    ? `Thought (${((elapsedTime || 0) / 1000).toFixed(1)}s)`
    : `Thinking (${displayTime.toFixed(1)}s)`;

  return (
    <div
      className={cn(
        'rounded-2xl border overflow-hidden transition-all duration-300',
        className,
      )}
      style={{
        borderColor: 'var(--color-border-subtle)',
        backgroundColor: 'var(--color-bg-surface-1)',
        maxWidth: '85%',
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-[var(--color-bg-surface-2)]/50"
      >
        <div
          className="flex items-center justify-center w-6 h-6 rounded-lg"
          style={{ backgroundColor: 'var(--color-accent-subtle)' }}
        >
          {!isComplete ? (
            <Loader2 size={13} className="text-[var(--color-accent)] animate-spin" />
          ) : (
            <Brain size={13} className="text-[var(--color-accent)]" />
          )}
        </div>

        <ChevronRight
          size={14}
          className={cn(
            'text-[var(--color-text-muted)] transition-transform duration-300',
            isOpen && 'rotate-90',
          )}
        />

        <span className="text-xs font-medium text-[var(--color-text-secondary)]">
          {timeLabel}
        </span>
      </button>

      {isOpen && content && (
        <div
          className="px-4 pb-4 fade-enter"
          style={{ borderTop: '1px solid var(--color-border-subtle)' }}
        >
          <div className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap font-mono pl-8 pt-3">
            {content}
          </div>
        </div>
      )}
    </div>
  );
}
