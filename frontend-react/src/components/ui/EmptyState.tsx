import React from 'react';
import { cn } from '../../lib/utils';
import { Inbox, Search, FileX, AlertCircle } from 'lucide-react';

export interface EmptyStateProps {
  illustration?: React.ReactNode;
  icon?: 'inbox' | 'search' | 'file' | 'alert' | React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

const iconMap = {
  inbox: Inbox,
  search: Search,
  file: FileX,
  alert: AlertCircle,
};

const EmptyState: React.FC<EmptyStateProps> = ({
  illustration,
  icon = 'inbox',
  title,
  description,
  action,
  className,
}) => {
  const renderIcon = () => {
    if (illustration) return illustration;
    if (typeof icon === 'string') {
      const IconComponent = iconMap[icon as keyof typeof iconMap];
      if (IconComponent) {
        return (
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">
            <IconComponent className="h-5 w-5 text-[var(--color-text-muted)]" />
          </div>
        );
      }
      return null;
    }
    return <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">{icon}</div>;
  };

  return (
    <div className={cn('flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center', className)}>
      <div className="mb-4">
        {renderIcon()}
      </div>
      <h3 className="mb-1 text-base font-semibold text-[var(--color-text-primary)]">
        {title}
      </h3>
      {description && (
        <p className="mb-5 max-w-sm text-sm leading-6 text-[var(--color-text-muted)]">
          {description}
        </p>
      )}
      {action && (
        <div className="flex items-center gap-2">
          {action}
        </div>
      )}
    </div>
  );
};

export { EmptyState };
