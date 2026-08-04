import React, { createContext, useContext, forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const TabsContext = createContext<{
  value: string;
  onChange: (value: string) => void;
}>({ value: '', onChange: () => {} });

const tabsListVariants = cva(
  'inline-flex items-center gap-1 rounded-xl p-1',
  {
    variants: {
      variant: {
        default: 'bg-white/[0.04] border border-white/[0.06]',
        underline: 'border-b border-white/[0.08] rounded-none p-0 gap-0',
        pills: 'bg-transparent gap-2',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      fullWidth: false,
    },
  }
);

const tabVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'text-white/50 hover:text-white hover:bg-white/[0.06] data-[state=active]:text-white data-[state=active]:bg-white/[0.08]',
        underline: 'text-white/50 hover:text-white border-b-2 border-transparent rounded-none px-4 py-2 data-[state=active]:text-blue-400 data-[state=active]:border-blue-400',
        pills: 'text-white/50 hover:text-white hover:bg-white/[0.06] data-[state=active]:text-white data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500/80 data-[state=active]:to-violet-500/80 data-[state=active]:shadow-md data-[state=active]:shadow-blue-500/20',
      },
      fullWidth: {
        true: 'flex-1',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      fullWidth: false,
    },
  }
);

interface TabsProps {
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

interface TabsListProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof tabsListVariants> {
  children: React.ReactNode;
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof tabVariants> {
  value: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

const Tabs = forwardRef<HTMLDivElement, TabsProps>(
  ({ className, value, onChange, children, ...props }, ref) => {
    return (
      <TabsContext.Provider value={{ value, onChange }}>
        <div ref={ref} className={cn('w-full', className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    );
  }
);
Tabs.displayName = 'Tabs';

const TabsList = forwardRef<HTMLDivElement, TabsListProps>(
  ({ className, variant, fullWidth, children, ...props }, ref) => {
    const childArray = Array.isArray(children) ? children : [children];
    return (
      <div
        ref={ref}
        role="tablist"
        className={cn(tabsListVariants({ variant, fullWidth }), className)}
        {...props}
      >
        {childArray.map((child, index) => {
          if (React.isValidElement<TabsTriggerProps>(child)) {
            return React.cloneElement(child as React.ReactElement<TabsTriggerProps>, {
              key: child.props.value || index,
              variant: child.props.variant || variant,
              fullWidth: child.props.fullWidth || fullWidth,
            });
          }
          return child;
        })}
      </div>
    );
  }
);
TabsList.displayName = 'TabsList';

const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, variant, fullWidth, icon, badge, disabled, children, ...props }, ref) => {
    const { value: selectedValue, onChange } = useContext(TabsContext);
    const isActive = selectedValue === value;

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        aria-controls={`content-${value}`}
        disabled={disabled}
        onClick={() => onChange(value)}
        data-state={isActive ? 'active' : 'inactive'}
        className={cn(tabVariants({ variant, fullWidth }), className)}
        {...props}
      >
        {icon && <span className="shrink-0">{icon}</span>}
        {children}
        {badge !== undefined && (
          <span className="inline-flex items-center justify-center rounded-full bg-white/[0.1] px-1.5 py-0.5 text-[10px] font-medium text-white/60">
            {badge}
          </span>
        )}
      </button>
    );
  }
);
TabsTrigger.displayName = 'TabsTrigger';

const TabsContent = forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, children, ...props }, ref) => {
    const { value: selectedValue } = useContext(TabsContext);

    if (selectedValue !== value) return null;

    return (
      <div
        ref={ref}
        role="tabpanel"
        id={`content-${value}`}
        className={cn('mt-4 animate-in fade-in duration-200', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
TabsContent.displayName = 'TabsContent';

export { Tabs, TabsList, TabsTrigger, TabsContent, tabsListVariants, tabVariants };
export type { TabsProps, TabsListProps, TabsTriggerProps, TabsContentProps };
