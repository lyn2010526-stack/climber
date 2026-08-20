import { useState, useRef, forwardRef } from 'react';
import { cn } from '../../lib/utils';

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: 'top' | 'bottom' | 'left' | 'right';
  align?: 'start' | 'center' | 'end';
  delay?: number;
  disabled?: boolean;
  className?: string;
}

const sideStyles: Record<string, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

const alignStyles: Record<string, Record<string, string>> = {
  top: { start: 'left-0 translate-x-0', end: 'right-0 left-auto translate-x-0', center: '' },
  bottom: { start: 'left-0 translate-x-0', end: 'right-0 left-auto translate-x-0', center: '' },
  left: { start: 'top-0 translate-y-0', end: 'bottom-0 top-auto translate-y-0', center: '' },
  right: { start: 'top-0 translate-y-0', end: 'bottom-0 top-auto translate-y-0', center: '' },
};

const arrowStyles: Record<string, string> = {
  top: 'bottom-0 left-1/2 -translate-x-1/2 translate-y-full border-t-[var(--color-code-bg)] border-x-transparent border-b-transparent',
  bottom: 'top-0 left-1/2 -translate-x-1/2 -translate-y-full border-b-[var(--color-code-bg)] border-x-transparent border-t-transparent',
  left: 'right-0 top-1/2 -translate-y-1/2 translate-x-full border-l-[var(--color-code-bg)] border-y-transparent border-r-transparent',
  right: 'left-0 top-1/2 -translate-y-1/2 -translate-x-full border-r-[var(--color-code-bg)] border-y-transparent border-l-transparent',
};

const Tooltip = forwardRef<HTMLDivElement, TooltipProps>(
  ({ content, children, side = 'top', align = 'center', delay = 300, disabled, className }, ref) => {
    const [isVisible, setIsVisible] = useState(false);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const show = () => {
      if (disabled) return;
      timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
    };

    const hide = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      setIsVisible(false);
    };

    return (
      <div
        ref={ref}
        className={cn('relative inline-flex', className)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {children}
        {isVisible && (
          <div
            role="tooltip"
            className={cn(
              'absolute z-50 whitespace-nowrap rounded-lg border border-white/[0.08] bg-[var(--color-code-bg)] px-2.5 py-1.5 text-xs text-[var(--color-text-inverse)] shadow-lg shadow-black/30 animate-in fade-in zoom-in-95 duration-150',
              sideStyles[side],
              alignStyles[side]?.[align] || '',
            )}
          >
            {content}
            <span
              className={cn(
                'absolute h-0 w-0 border-4',
                arrowStyles[side],
              )}
            />
          </div>
        )}
      </div>
    );
  }
);
Tooltip.displayName = 'Tooltip';

export { Tooltip };
export type { TooltipProps };
