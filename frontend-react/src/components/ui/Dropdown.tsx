import React, { useState, useRef, useEffect, useId, useCallback, isValidElement } from 'react';
import { cn } from '../../lib/utils';
import { icons, iconSizes } from '../../lib/icons';

export interface DropdownProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: 'left' | 'right' | 'center';
  side?: 'bottom' | 'top' | 'left' | 'right';
  className?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  closeOnSelect?: boolean;
  triggerLabel?: string;
}

/**
 * The menu is a surface-1 panel on a border-default edge, lifted by the one
 * shadow rung that means "floating above the page". It never takes a tint: the
 * only saturated thing inside a menu is the selected row. A submenu reuses this
 * recipe verbatim and only re-anchors it, so nesting cannot grow a second
 * panel look.
 */
const menuPanel =
  'absolute z-[var(--z-dropdown)] min-w-[180px] rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-1)] shadow-[var(--shadow-lg)] dropdown-panel-in';

/**
 * Everything a menu row is, minus its colour: the geometry, the short
 * transition and the shared focus ring. A leaf row, a submenu trigger and a
 * disabled row all sit on this base, so a row cannot quietly become a different
 * size or lose its focus indicator. Colour is supplied per row, which is where
 * selection and danger diverge.
 */
const menuRow =
  'flex w-full items-center gap-[var(--control-gap)] rounded-[var(--radius-md)] px-[var(--space-3)] py-[var(--space-2)] text-left text-[var(--text-sm)] transition-colors duration-150 motion-reduce:transition-none focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]';

const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  children,
  align = 'left',
  side = 'bottom',
  className,
  open: controlledOpen,
  onOpenChange,
  closeOnSelect = true,
  triggerLabel,
}) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
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
        triggerRef.current?.focus();
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

  const toggle = () => setIsOpen(!isOpen);

  useEffect(() => {
    if (!isOpen) return;
    ref.current?.querySelector<HTMLElement>('[role="menuitem"]:not([data-disabled])')?.focus();
  }, [isOpen]);

  /**
   * Trigger semantics attach to the caller's own element. Wrapping it in a
   * focusable `role="button"` div produced nested interactive content, so
   * screen readers announced a button inside a button and the inner control
   * stayed a second tab stop.
   */
  const triggerNode = isValidElement<Record<string, unknown>>(trigger)
    ? React.cloneElement(trigger, {
        ref: (node: HTMLElement | null) => {
          triggerRef.current = node;
        },
        'aria-haspopup': 'menu' as const,
        'aria-expanded': isOpen,
        'aria-controls': generatedId,
        onClick: (event: React.MouseEvent) => {
          (trigger.props as { onClick?: (e: React.MouseEvent) => void }).onClick?.(event);
          toggle();
        },
        onKeyDown: (event: React.KeyboardEvent) => {
          (trigger.props as { onKeyDown?: (e: React.KeyboardEvent) => void }).onKeyDown?.(event);
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle();
          }
        },
      })
    : (
      <button
        type="button"
        ref={node => { triggerRef.current = node; }}
        data-dropdown-trigger
        aria-label={triggerLabel}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={generatedId}
        onClick={toggle}
        onKeyDown={event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle();
          }
        }}
        className="inline-flex items-center"
      >
        {trigger}
      </button>
    );

  return (
    <div ref={ref} className={cn('relative inline-block', className)}>
      {triggerNode}
      {isOpen && (
        <div
          id={generatedId}
          role="menu"
          aria-orientation="vertical"
          className={cn(
            menuPanel,
            'motion-reduce:animate-none',
            alignmentClasses[align],
            sideClasses[side]
          )}
          onClick={(e) => {
            const item = (e.target as HTMLElement).closest('[role="menuitem"]');
            if (closeOnSelect && item && !item.hasAttribute('data-disabled') && !item.hasAttribute('aria-haspopup')) setIsOpen(false);
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
              e.preventDefault();
              const items = Array.from(ref.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([data-disabled])') || []);
              if (items.length === 0) return;
              const currentIndex = items.indexOf(document.activeElement as HTMLElement);
              const nextIndex = e.key === 'ArrowDown'
                ? (currentIndex + 1) % items.length
                : (currentIndex - 1 + items.length) % items.length;
              items[nextIndex]?.focus();
            } else if (e.key === 'Home' || e.key === 'End') {
              e.preventDefault();
              const items = Array.from(ref.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([data-disabled])') || []);
              if (items.length === 0) return;
              (e.key === 'Home' ? items[0] : items[items.length - 1])?.focus();
            }
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export interface DropdownItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  shortcut?: string;
  /**
   * Marks the row the menu currently stands on. Selection is the one place a
   * menu is allowed to spend the accent, and it is announced as the current
   * item rather than as a check, because a menu that mixes checkable rows with
   * plain ones cannot switch every row to a checkbox role.
   */
  selected?: boolean;
}

const DropdownItem = React.forwardRef<HTMLButtonElement, DropdownItemProps>(
  ({ icon, danger, disabled, shortcut, selected, children, className, onClick, ...props }, ref) => (
    <button type="button"
      ref={ref}
      role="menuitem"
      data-disabled={disabled || undefined}
      data-selected={selected || undefined}
      aria-current={selected ? 'true' : undefined}
      disabled={disabled}
      onClick={event => {
        if (disabled) return;
        onClick?.(event);
      }}
      className={cn(
        menuRow,
        // Precedence runs disabled, then selected, then danger, then the plain
        // row, so exactly one colour pair is ever on the element. Two pairs at
        // once would leave the winner up to stylesheet order.
        disabled
          ? 'cursor-not-allowed text-[var(--color-text-disabled)]'
          : selected
            ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)] enabled:hover:text-[var(--color-accent-hover)]'
            : danger
              ? 'text-[var(--color-error)] enabled:hover:bg-[var(--color-error-subtle)]'
              : 'text-[var(--color-text-secondary)] enabled:hover:bg-[var(--color-bg-surface-2)] enabled:hover:text-[var(--color-text-primary)]',
        className
      )}
      {...props}
    >
      {icon && <span className="shrink-0 w-[var(--icon-sm)] h-[var(--icon-sm)]" aria-hidden="true">{icon}</span>}
      <span className="flex-1 truncate">{children}</span>
      {shortcut && (
        <kbd className="rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-1)] py-[var(--space-0-5)] text-[var(--text-2xs)] text-[var(--color-text-muted)] font-mono">
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
  className?: string;
}

const DropdownSubMenu: React.FC<DropdownSubMenuProps> = ({ trigger, children, icon, className }) => {
  const [open, setOpen] = useState(false);
  const generatedId = useId();

  return (
    <div
      className={cn('relative', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onKeyDown={event => {
        if (event.key === 'Escape' && open) {
          event.stopPropagation();
          setOpen(false);
        }
      }}
    >
      <button type="button"
        role="menuitem"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? generatedId : undefined}
        onClick={() => setOpen(value => !value)}
        className={cn(
          menuRow,
          // A submenu trigger behaves like a plain row: it has no selection of
          // its own, so it keeps the secondary rung and the surface-2 hover.
          'text-[var(--color-text-secondary)] enabled:hover:bg-[var(--color-bg-surface-2)] enabled:hover:text-[var(--color-text-primary)]',
        )}
      >
        {icon && <span className="shrink-0 w-[var(--icon-sm)] h-[var(--icon-sm)]" aria-hidden="true">{icon}</span>}
        <span className="flex-1 truncate">{trigger}</span>
        {/* The chevron is the affordance that says a submenu opens sideways, so
            it stays on the muted rung and only follows the row on hover. */}
        <icons.submenu size={iconSizes.xs} className="shrink-0 text-[var(--color-text-muted)]" aria-hidden="true" focusable="false" />
      </button>
      {open && (
        <div
          id={generatedId}
          className={cn(menuPanel, 'left-full top-0 min-w-[160px]')}
          role="menu"
        >
          {children}
        </div>
      )}
    </div>
  );
};

const DropdownDivider: React.FC = () => (
  <div className="my-[var(--space-1)] h-px bg-[var(--color-border-subtle)]" role="separator" />
);

/** A group title. It names a section, so it takes the muted rung and never a
 *  hover or focus state of its own. */
const DropdownHeader: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="px-[var(--space-3)] py-[var(--space-1-5)] text-[var(--text-2xs)] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
    {children}
  </div>
);

export { Dropdown, DropdownItem, DropdownSubMenu, DropdownDivider, DropdownHeader };
