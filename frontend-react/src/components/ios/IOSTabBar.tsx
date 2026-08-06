import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ReactNode } from 'react';

interface IOSTabItem {
  id: string;
  label: string;
  icon: ReactNode;
  badge?: number;
}

interface IOSTabBarProps {
  tabs: IOSTabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export function IOSTabBar({ tabs, activeTab, onChange, className }: IOSTabBarProps) {
  return (
    <div
      className={cn(
        'fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around px-2 pb-[env(safe-area-inset-bottom,8px)] pt-1',
        'bg-[var(--color-bg-surface-1)]/90 backdrop-blur-xl border-t border-[var(--color-border-subtle)]',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className="relative flex flex-col items-center justify-center flex-1 py-1.5 min-w-[56px] gap-0.5"
          >
            <div className="relative">
              <div
                className={cn(
                  'transition-colors duration-150',
                  isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'
                )}
              >
                {tab.icon}
              </div>
              {tab.badge && tab.badge > 0 && (
                <span className="absolute -top-1 -right-2 min-w-[16px] h-4 flex items-center justify-center px-1 rounded-full bg-[var(--color-error)] text-white text-[10px] font-semibold">
                  {tab.badge > 99 ? '99+' : tab.badge}
                </span>
              )}
            </div>
            <span
              className={cn(
                'text-[10px] font-medium transition-colors duration-150',
                isActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'
              )}
            >
              {tab.label}
            </span>
            {isActive && (
              <motion.div
                layoutId="tab-indicator"
                className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full bg-[var(--color-accent)]"
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
