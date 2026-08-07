import React from 'react';
import { cn } from '../../lib/utils';

interface DividerProps {
  className?: string;
  orientation?: 'horizontal' | 'vertical';
  label?: string;
}

export const Divider: React.FC<DividerProps> = ({ className, orientation = 'horizontal', label }) => {
  if (label) {
    return (
      <div className={cn('flex items-center gap-4 my-4', className)}>
        <div className="flex-1 h-px bg-[var(--color-border-subtle)]" />
        <span className="text-xs text-[var(--color-text-muted)] font-medium">{label}</span>
        <div className="flex-1 h-px bg-[var(--color-border-subtle)]" />
      </div>
    );
  }

  if (orientation === 'vertical') {
    return <div className={cn('w-px h-full bg-[var(--color-border-subtle)]', className)} />;
  }

  return <div className={cn('h-px w-full bg-[var(--color-border-subtle)]', className)} />;
};

export default Divider;
