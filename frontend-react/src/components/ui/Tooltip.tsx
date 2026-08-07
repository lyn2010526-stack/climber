import React, { useState, useRef, useCallback, useId } from 'react';
import { cn } from '../../lib/utils';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  delayLeave?: number;
  disabled?: boolean;
  className?: string;
  maxWidth?: number;
}

const positionClasses: Record<string, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-[var(--space-2)]',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-[var(--space-2)]',
  left: 'right-full top-1/2 -translate-y-1/2 mr-[var(--space-2)]',
  right: 'left-full top-1/2 -translate-y-1/2 ml-[var(--space-2)]',
};

const arrowClasses: Record<string, string> = {
  top: 'top-full left-1/2 -translate-x-1/2 border-t-[var(--surface-elevated)] border-x-transparent border-b-transparent',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-[var(--surface-elevated)] border-x-transparent border-t-transparent',
  left: 'left-full top-1/2 -translate-y-1/2 border-l-[var(--surface-elevated)] border-y-transparent border-r-transparent',
  right: 'right-full top-1/2 -translate-y-1/2 border-r-[var(--surface-elevated)] border-y-transparent border-l-transparent',
};

const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = 'top',
  delay = 200,
  delayLeave = 100,
  disabled = false,
  className,
  maxWidth = 250,
}) => {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const generatedId = useId();

  const handleEnter = useCallback(() => {
    if (disabled) return;
    timeoutRef.current = setTimeout(() => setShow(true), delay);
  }, [delay, disabled]);

  const handleLeave = useCallback(() => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(false), delayLeave);
  }, [delayLeave]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') setShow(false);
  }, []);

  if (disabled) return <>{children}</>;

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onFocus={handleEnter}
      onBlur={handleLeave}
      onKeyDown={handleKeyDown}
    >
      {children}
      {show && (
        <div
          role="tooltip"
          id={generatedId}
          className={cn(
            'absolute z-[var(--z-tooltip)] px-[var(--space-2-5)] py-[var(--space-1-5)] text-[var(--font-size-xs)] font-medium text-[var(--text-inverse)] bg-[var(--surface-elevated)] rounded-[var(--radius-lg)] shadow-[var(--shadow-lg)] whitespace-normal pointer-events-none',
            'animate-[fadeIn_150ms_ease-out]',
            positionClasses[position],
            className
          )}
          style={{ maxWidth: `${maxWidth}px` }}
        >
          {content}
          <span
            className={cn('absolute w-0 h-0 border-4', arrowClasses[position])}
            aria-hidden="true"
          />
        </div>
      )}
    </div>
  );
};

export { Tooltip };
