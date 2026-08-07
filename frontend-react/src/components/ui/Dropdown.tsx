import React, { useState, useRef, useEffect, useId, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { ChevronRight } from 'lucide-react';

export interface DropdownProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: 'left' | 'right' | 'center';
  side?: 'bottom' | 'top' | 'left' | 'right';
  className?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  closeOnSelect?: boolean;
}

const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  children,
  align = 'left',
  side = 'bottom',
  className,
  open: controlledOpen,
  onOpenChange,
  closeOnSelect = true,
}) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const generatedId = useId();

  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen;

  const setIsOpen = useCallback((open: boolean) => {
    if (controlledOpen === undefined) setInternalOpen(open);
    onOpenChange?.(open);
  }, [controlledOpen, onOpenChange]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen, setIsOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        ref.current?.querySelector<HTMLElement>('[data-dropdown-trigger]')?.focus();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, setIsOpen]);

  const alignmentClasses = {
    left: 'left-0',
    right: 'right-0',
    center: 'left-1/2 -translate-x-1/2',
  };

  const sideClasses = {
    bottom: 'top-full mt-[var(--space-1)]',
    top: 'bottom-full mb-[var(--space-1)]',
    left: 'right-full mr-[var(--space-1)]',
    right: 'left-full ml-[var(--space-1)]',
  };

  return (
    <div ref={ref} className={cn('relative inline-block', className)}>
      <div
        data-dropdown-trigger
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsOpen(!isOpen); } }}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={generatedId}
      >
        {trigger}
      </div>
      {isOpen && (
        <div
          id={generatedId}
          role="menu"
          aria-orientation="vertical"
          className={cn(
            'absolute z-[var(--z-dropdown)] min-w-[180px] py-[var(--space-1)] rounded-[var(--radius-xl)] border border-[var(--border-subtle)] bg-[var(--surface-elevated)] shadow-[var(--shadow-xl)] backdrop-blur-xl',
            'animate-[scaleIn_150ms_cubic-bezier(0.16,1,0.3,1)]',
            alignmentClasses[align],
            sideClasses[side]
          )}
          onClick={() => closeOnSelect && setIsOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
              e.preventDefault();
              const items = Array.from(ref.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([data-disabled])') || []);
              const currentIndex = items.indexOf(document.activeElement as HTMLElement);
              const nextIndex = e.key === 'ArrowDown'
                ? (currentIndex + 1) % items.length
                : (currentIndex - 1 + items.length) % items.length;
              items[nextIndex]?.focus();
            }
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export interface DropdownItemProps extends React.HTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  shortcut?: string;
}

const DropdownItem = React.forwardRef<HTMLButtonElement, DropdownItemProps>(
  ({ icon, danger, disabled, shortcut, children, className, ...props }, ref) => (
    <button
      ref={ref}
      role="menuitem"
      data-disabled={disabled || undefined}
      disabled={disabled}
      className={cn(
        'w-full flex items-center gap-[var(--space-2-5)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--font-size-sm)] transition-colors duration-[var(--transition-fast)] text-left rounded-[var(--radius-md)] mx-[var(--space-1)]',
        danger
          ? 'text-[var(--color-danger)] hover:bg-[var(--color-danger-subtle)]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--surface-bg-hover)] hover:text-[var(--text-primary)]',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
      {...props}
    >
      {icon && <span className="shrink-0 w-[var(--icon-sm)] h-[var(--icon-sm)]" aria-hidden="true">{icon}</span>}
      <span className="flex-1 truncate">{children}</span>
      {shortcut && (
        <kbd className="text-[10px] text-[var(--text-muted)] bg-[var(--surface-bg-subtle)] px-[var(--space-1)] py-[var(--space-0-5)] rounded-[var(--radius-sm)] font-mono">
          {shortcut}
        </kbd>
      )}
    </button>
  )
);
DropdownItem.displayName = 'DropdownItem';

interface DropdownSubMenuProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  icon?: React.ReactNode;
}

const DropdownSubMenu: React.FC<DropdownSubMenuProps> = ({ trigger, children, icon }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        role="menuitem"
        aria-haspopup="menu"
        aria-expanded={open}
        className="w-full flex items-center gap-[var(--space-2-5)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--font-size-sm)] text-[var(--text-secondary)] hover:bg-[var(--surface-bg-hover)] hover:text-[var(--text-primary)] transition-colors rounded-[var(--radius-md)] mx-[var(--space-1)] text-left"
      >
        {icon && <span className="shrink-0 w-[var(--icon-sm)] h-[var(--icon-sm)]" aria-hidden="true">{icon}</span>}
        <span className="flex-1 truncate">{trigger}</span>
        <ChevronRight className="w-[var(--icon-xs)] h-[var(--icon-xs)] text-[var(--text-muted)] shrink-0" />
      </button>
      {open && (
        <div
          className="absolute left-full top-0 min-w-[160px] py-[var(--space-1)] rounded-[var(--radius-xl)] border border-[var(--border-subtle)] bg-[var(--surface-elevated)] shadow-[var(--shadow-xl)]"
          role="menu"
        >
          {children}
        </div>
      )}
    </div>
  );
};

const DropdownDivider: React.FC = () => (
  <div className="my-[var(--space-1)] h-px bg-[var(--border-subtle)]" role="separator" />
);

const DropdownHeader: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="px-[var(--space-3)] py-[var(--space-1-5)] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
    {children}
  </div>
);

export { Dropdown, DropdownItem, DropdownSubMenu, DropdownDivider, DropdownHeader };
