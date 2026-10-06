import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

export type ContentView = 'rendered' | 'raw';

export interface RawRenderedToggleProps {
  /** The friendly, already-rendered pane. */
  rendered: ReactNode;
  /** The payload shown as text/JSON in the raw pane. Objects are pretty-printed. */
  raw?: string | object | null;
  /** Controlled view. Omit to let the component own the toggle. */
  view?: ContentView;
  onViewChange?: (view: ContentView) => void;
  defaultView?: ContentView;
  className?: string;
}

/** Pretty-print an object, and pass strings through untouched. */
export function formatRaw(raw: string | object | null | undefined): string {
  if (raw == null) return '';
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch {
        return raw;
      }
    }
    return raw;
  }
  try {
    return JSON.stringify(raw, null, 2);
  } catch {
    return String(raw);
  }
}

export function RawRenderedToggle({
  rendered,
  raw,
  view,
  onViewChange,
  defaultView = 'rendered',
  className,
}: RawRenderedToggleProps) {
  const { t } = useI18n();
  const baseId = useId();
  const [internalView, setInternalView] = useState<ContentView>(defaultView);
  const active = view ?? internalView;

  const select = (next: ContentView) => {
    setInternalView(next);
    onViewChange?.(next);
  };

  const options: { id: ContentView; label: string }[] = [
    { id: 'rendered', label: t('content_view.rendered', { defaultValue: 'Rendered' }) },
    { id: 'raw', label: t('content_view.raw', { defaultValue: 'Raw' }) },
  ];

  return (
    <div className={cn('flex min-w-0 flex-col gap-[var(--space-2)]', className)}>
      <div
        role="tablist"
        aria-label={t('content_view.label', { defaultValue: 'Content view' })}
        className="inline-flex shrink-0 items-center gap-[var(--space-1)] self-start rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-[var(--space-1)]"
      >
        {options.map(option => {
          const isActive = active === option.id;
          return (
            <button
              key={option.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${option.id}`}
              aria-selected={isActive}
              aria-controls={`${baseId}-panel-${option.id}`}
              data-view={option.id}
              data-state={isActive ? 'active' : 'inactive'}
              tabIndex={isActive ? 0 : -1}
              onClick={() => select(option.id)}
              className={cn(
                'inline-flex items-center rounded-[var(--radius-sm)] px-[var(--space-3)] py-[var(--space-1)] text-[length:var(--text-xs)] font-medium transition-colors focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
                isActive
                  ? 'bg-[var(--color-accent-subtle)] font-semibold text-[var(--color-accent-foreground)]'
                  : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]',
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${baseId}-panel-${active}`}
        aria-labelledby={`${baseId}-tab-${active}`}
        tabIndex={0}
        data-view={active}
        className="min-w-0 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
      >
        {active === 'rendered'
          ? rendered
          : (
            <pre
              data-testid="raw-payload"
              aria-label={t('content_view.raw', { defaultValue: 'Raw' })}
              className="max-h-96 max-w-full overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-code-bg)] p-[var(--space-2-5)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]"
            >
              {formatRaw(raw)}
            </pre>
          )}
      </div>
    </div>
  );
}

export default RawRenderedToggle;
