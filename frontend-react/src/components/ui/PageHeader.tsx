import React from 'react';
import { cn } from '../../lib/utils';

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
  className?: string;
}

export function PageHeader({
  title,
  description,
  icon,
  actions,
  breadcrumbs,
  className
}: PageHeaderProps) {
  return (
    <header className={cn('mb-5 md:mb-6', className)}>
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-2 text-[var(--font-size-xs)] mb-3">
          {breadcrumbs.map((crumb, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span className="text-[var(--text-muted)]">/</span>}
              <span
                className={i === breadcrumbs.length - 1 ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-muted)]'}
              >
                {crumb.label}
              </span>
            </React.Fragment>
          ))}
        </nav>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          {icon && (
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border" style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              borderColor: 'var(--color-border-subtle)',
              color: 'var(--color-text-secondary)'
            }}>
              {icon}
            </div>
          )}
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.02em] leading-tight md:text-2xl" style={{ color: 'var(--color-text-primary)' }}>
              {title}
            </h1>
            {description && (
              <p className="mt-1 max-w-2xl text-sm leading-5" style={{ color: 'var(--color-text-secondary)' }}>
                {description}
              </p>
            )}
          </div>
        </div>

        {actions && (
          <div className="flex items-center gap-2 shrink-0">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
}
