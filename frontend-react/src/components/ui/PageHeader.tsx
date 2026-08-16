import React from 'react';

export interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: React.ElementType;
  iconColor?: string;
  action?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, icon: Icon, iconColor = 'var(--color-accent)', action, className }: PageHeaderProps) {
  return (
    <div className={`flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8 ${className ?? ''}`}>
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="p-2.5 rounded-xl border" style={{ backgroundColor: `${iconColor}15`, border: `1px solid ${iconColor}30` }}>
            <Icon size={20} style={{ color: iconColor }} />
          </div>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>{title}</h1>
          {description && <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>{description}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
