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

/**
 * The page title is the brightest text on the screen, so it takes
 * `--color-text-primary` and the largest heading rung. Everything under it
 * steps down one level per rung: the description lands on the secondary text
 * role one step below the title, and a breadcrumb trail drops to muted so the
 * path is always the quietest thing in the header.
 */
export function PageHeader({
  title,
  description,
  icon,
  actions,
  breadcrumbs,
  className
}: PageHeaderProps) {
  return (
    <header className={cn('mb-[var(--space-5)] md:mb-[var(--space-6)]', className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-[var(--space-3)] flex items-center gap-[var(--space-2)] text-[length:var(--text-xs)]">
          {breadcrumbs.map((crumb, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span aria-hidden="true" className="text-[var(--color-text-muted)]">/</span>}
              <span
                className={i === breadcrumbs.length - 1 ? 'font-medium text-[var(--color-text-secondary)]' : 'text-[var(--color-text-muted)]'}
              >
                {crumb.label}
              </span>
            </React.Fragment>
          ))}
        </nav>
      )}

      <div className="flex flex-col gap-[var(--space-4)] sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-[var(--space-3)]">
          {icon && (
            <div className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)] [&>svg]:size-[var(--icon-lg)]">
              {icon}
            </div>
          )}
          <div>
            <h1 className="text-[length:var(--text-xl)] font-semibold leading-[var(--leading-tight)] tracking-[-0.02em] text-[var(--color-text-primary)] md:text-[length:var(--text-2xl)]">
              {title}
            </h1>
            {description && (
              <p className="mt-[var(--space-1)] max-w-2xl text-[length:var(--text-sm)] leading-[var(--leading-normal)] text-[var(--color-text-secondary)]">
                {description}
              </p>
            )}
          </div>
        </div>

        {actions && (
          <div className="flex shrink-0 items-center gap-[var(--space-2)]">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
}
