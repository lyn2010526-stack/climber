import React from 'react';
import { Search, Bell, Command, ChevronRight } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { cn } from '../../lib/utils';

interface TopBarProps {
  breadcrumbs?: { label: string; href?: string }[];
  onSearchClick?: () => void;
  notificationCount?: number;
  rightContent?: React.ReactNode;
  className?: string;
}

export function TopBar({
  breadcrumbs = [],
  onSearchClick,
  notificationCount,
  rightContent,
  className
}: TopBarProps) {
  return (
    <header
      className={cn(
        'h-14 flex items-center justify-between px-4 md:px-6 shrink-0 z-30',
        className
      )}
      style={{
        borderBottom: '1px solid var(--color-border-subtle)',
        backgroundColor: 'var(--color-surface-glass)',
        backdropFilter: 'blur(var(--glass-blur)) saturate(var(--glass-saturate))',
        WebkitBackdropFilter: 'blur(var(--glass-blur)) saturate(var(--glass-saturate))',
      }}
    >
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 min-w-0">
        {breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1.5 text-xs">
            {breadcrumbs.map((crumb, i) => (
              <React.Fragment key={i}>
                {i > 0 && (
                  <ChevronRight size={10} style={{ color: 'var(--color-text-muted)' }} />
                )}
                <button
                  onClick={() => crumb.href && (window.location.hash = crumb.href)}
                  className={cn(
                    'truncate transition-colors duration-200',
                    i === breadcrumbs.length - 1
                      ? 'font-semibold text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  )}
                >
                  {crumb.label}
                </button>
              </React.Fragment>
            ))}
          </nav>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Global Search Trigger */}
        <button
          onClick={onSearchClick}
          className={cn(
            'hidden md:flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-xs transition-all duration-200 border',
            'hover:border-[var(--color-border-default)]'
          )}
          style={{
            color: 'var(--color-text-muted)',
            borderColor: 'var(--color-border-subtle)',
            backgroundColor: 'var(--color-bg-surface-2)',
            width: '240px',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--color-text-secondary)';
            e.currentTarget.style.borderColor = 'var(--color-border-default)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--color-text-muted)';
            e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
          }}
        >
          <Search size={14} />
          <span className="flex-1 text-left">搜索...</span>
          <kbd className="text-[10px] px-1.5 py-0.5 rounded-md font-mono flex items-center gap-0.5" style={{
            backgroundColor: 'var(--color-bg-surface-3)',
            color: 'var(--color-text-muted)',
            border: '1px solid var(--color-border-subtle)'
          }}>
            <Command size={10} /> K
          </kbd>
        </button>

        {/* Mobile search button */}
        <button
          onClick={onSearchClick}
          className="md:hidden p-2 rounded-xl transition-all duration-200"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <Search size={18} />
        </button>

        {/* Notifications */}
        <button
          className="relative p-2 rounded-xl transition-all duration-200"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
            e.currentTarget.style.color = 'var(--color-text-secondary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-text-muted)';
          }}
        >
          <Bell size={18} />
          {notificationCount && notificationCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full" style={{
              backgroundColor: 'var(--color-accent)',
              boxShadow: '0 0 6px var(--color-accent-glow)'
            }} />
          )}
        </button>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Custom Right Content */}
        {rightContent}
      </div>
    </header>
  );
}
