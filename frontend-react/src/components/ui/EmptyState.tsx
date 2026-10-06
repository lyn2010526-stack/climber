import React from 'react';
import { cn } from '../../lib/utils';
import { icons, iconSizes, type StatusTone } from '../../lib/icons';
import { StatusIcon } from './StatusIcon';

/** The named empty-state options a caller can pass as `icon`. A caller that
 *  needs artwork no option covers passes the node itself. */
export type EmptyStateIconName =
  | 'inbox'
  | 'search'
  | 'file'
  | 'settings'
  | 'locked'
  | 'alert'
  | 'warning'
  | 'unreported'
  | 'queued'
  | 'approval';

export interface EmptyStateProps {
  illustration?: React.ReactNode;
  icon?: EmptyStateIconName | React.ReactNode;
  title: string;
  /**
   * What is missing, named concretely: which collection came back empty, which
   * filter excluded everything, which step has to happen before the panel can
   * fill. Marketing copy belongs in the page, not here.
   */
  description?: string;
  /**
   * The way out. Callers pass a `Button` from this layer, so the action reads
   * as part of the control set instead of a one-off button in the gap.
   */
  action?: React.ReactNode;
  className?: string;
}

/**
 * Artwork options. `inbox`, `search` and `file` describe the shape of the
 * missing thing and stay on the muted rung; they are decoration, not state.
 * `settings` and `locked` extend the same muted vocabulary to the two shared
 * meanings an empty settings or privacy surface draws.
 */
const ARTWORK = {
  inbox: icons.emptyInbox,
  search: icons.emptySearch,
  file: icons.emptyFile,
  settings: icons.settings,
  locked: icons.privacyLock,
} as const satisfies Record<string, typeof icons.emptyInbox>;

/**
 * State options. These report what the panel is waiting on, so each one routes
 * through `StatusIcon` and takes its tone from the same table every other
 * control uses: `alert` is an error, `warning` and `unreported` keep their
 * existing tones, and `queued` and `approval` cover the two states an agent
 * workbench reaches that are not outcomes — a run accepted and waiting for a
 * slot, and a tool call parked on a decision.
 */
const STATE_ICON: Record<'alert' | 'warning' | 'unreported' | 'queued' | 'approval', StatusTone> = {
  alert: 'error',
  warning: 'warning',
  unreported: 'unknown',
  queued: 'queued',
  approval: 'approval',
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
    if (typeof icon !== 'string') return icon;
    if (icon in STATE_ICON) {
      return <StatusIcon tone={STATE_ICON[icon as keyof typeof STATE_ICON]} size="lg" />;
    }
    const Artwork = ARTWORK[icon as keyof typeof ARTWORK];
    if (!Artwork) return null;
    return (
      <Artwork size={iconSizes.lg} className="text-[var(--color-text-muted)]" aria-hidden="true" focusable="false" />
    );
  };

  return (
    <div className={cn('flex min-h-64 flex-col items-center justify-center px-[var(--space-6)] py-[var(--space-12)] text-center', className)}>
      <div className="mb-[var(--space-4)]">
        {renderIcon()}
      </div>
      {/* The title is the only bright line; the description drops one rung so
          the two never read as the same weight of statement. */}
      <h3 className="mb-[var(--space-1)] text-[var(--text-base)] font-semibold text-[var(--color-text-primary)]">
        {title}
      </h3>
      {description && (
        <p className="mb-[var(--space-5)] max-w-sm text-[var(--text-sm)] leading-[var(--leading-normal)] text-[var(--color-text-muted)]">
          {description}
        </p>
      )}
      {action && (
        <div className="flex items-center gap-[var(--space-2)]">
          {action}
        </div>
      )}
    </div>
  );
};

export { EmptyState };
