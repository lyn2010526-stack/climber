import React, { useState, createContext, useContext, useCallback, useMemo, type KeyboardEvent } from 'react';
import { cn } from '../../lib/utils';

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (value: string) => void;
  baseId: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface TabsProps {
  defaultValue: string;
  children: React.ReactNode;
  className?: string;
  onChange?: (value: string) => void;
}

export const Tabs: React.FC<TabsProps> = ({ defaultValue, children, className, onChange }) => {
  const [activeTab, setActiveTab] = useState(defaultValue);
  const baseId = React.useId();

  const handleSetActive = useCallback((value: string) => {
    setActiveTab(value);
    onChange?.(value);
  }, [onChange]);

  const context = useMemo(() => ({ activeTab, setActiveTab: handleSetActive, baseId }), [activeTab, handleSetActive, baseId]);

  return (
      <TabsContext.Provider value={context}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  );
};

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export const TabsList: React.FC<TabsListProps> = ({ children, className }) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsList must be used within Tabs');
  const { activeTab } = context;

  /**
   * Roving arrow-key navigation per the WAI-ARIA tabs pattern: Left/Right for
   * horizontal strips, Up/Down for vertical, Home/End to jump to the ends.
   * Only the selected tab is in the tab sequence, which is what lets keyboard
   * users reach the panel content without tabbing through every tab first.
   */
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const nextKeys = ['ArrowRight', 'ArrowDown'];
    const prevKeys = ['ArrowLeft', 'ArrowUp'];
    if (![...nextKeys, ...prevKeys, 'Home', 'End'].includes(event.key)) return;

    const tabs = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])')
    );
    if (tabs.length === 0) return;
    const index = tabs.findIndex(tab => tab.dataset.value === activeTab);
    if (index === -1) return;

    event.preventDefault();
    let nextIndex = index;
    if (nextKeys.includes(event.key)) nextIndex = (index + 1) % tabs.length;
    else if (prevKeys.includes(event.key)) nextIndex = (index - 1 + tabs.length) % tabs.length;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = tabs.length - 1;

    const next = tabs[nextIndex];
    if (!next) return;
    context.setActiveTab(next.dataset.value!);
    next.focus();
  };

  return (
    <div
      role="tablist"
      aria-label="Tabs"
      onKeyDown={handleKeyDown}
      className={cn(
        // The strip itself recedes to the surface the page already provides and
        // keeps a real border, so the selected tab is the only thing inside it
        // that carries colour.
        'inline-flex max-w-full items-center gap-[var(--space-1)] overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-[var(--space-1)]',
        className
      )}
    >
      {children}
    </div>
  );
};

interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ value, children, className, icon, disabled }) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');

  const { activeTab, setActiveTab, baseId } = context;
  // One value decides the aria state, the roving tabindex, the data attribute
  // and the paint. Deriving the visual from the same comparison that sets
  // `aria-selected` is what keeps the announced state and the drawn state from
  // drifting apart.
  const isActive = activeTab === value;
  const triggerId = `${baseId}-tab-${value}`;
  const panelId = `${baseId}-panel-${value}`;

  return (
    <button type="button"
      role="tab"
      id={triggerId}
      aria-controls={panelId}
      aria-selected={isActive}
      data-value={value}
      data-state={isActive ? 'active' : 'inactive'}
      tabIndex={isActive ? 0 : -1}
      disabled={disabled}
      onClick={() => setActiveTab(value)}
      className={cn(
        'inline-flex shrink-0 items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] px-[var(--space-3)] py-[var(--space-1-5)] text-[length:var(--text-sm)] font-medium',
        'transition-colors duration-150 motion-reduce:transition-none',
        'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
        'disabled:cursor-not-allowed',
        // Selected: the accent's own subtle wash with the accent foreground, so
        // the highlight follows the theme and survives a monochrome rendering
        // through the weight change as well.
        isActive
          ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)] font-semibold'
          : 'text-[var(--color-text-muted)] enabled:hover:bg-[var(--color-bg-surface-2)] enabled:hover:text-[var(--color-text-secondary)] enabled:active:bg-[var(--color-bg-surface-3)]',
        // Disabled last and across every channel it can own, so it wins over
        // both branches: a locked tab must not keep the selected paint just
        // because it happens to be the current one.
        disabled && 'bg-[var(--color-bg-disabled)] font-medium text-[var(--color-text-disabled)]',
        className
      )}
    >
      {icon}
      {children}
    </button>
  );
};

interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className }) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');

  const { baseId } = context;
  if (context.activeTab !== value) return null;

  return (
    <div
      role="tabpanel"
      id={`${baseId}-panel-${value}`}
      aria-labelledby={`${baseId}-tab-${value}`}
      tabIndex={0}
      className={cn('mt-[var(--space-4)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]', className)}
    >
      {children}
    </div>
  );
};

export default Tabs;
