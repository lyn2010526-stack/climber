import { useEffect, useMemo, useRef } from 'react';
import { Archive, CheckSquare, Trash2, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { Button } from '../ui/Button';
import { useSessionBatchSelection } from './sessionBatchSelection';
import type { SessionBatchItem } from './sessionBatchSelection';

/**
 * A batch-selection surface for the session sidebar.
 *
 * When more than a couple of sessions need the same action, acting one row at a
 * time stops scaling; Codex answers this with a fuzzy multi-select picker and
 * cc-haha's desktop shell with a dedicated selection bar over the browser list.
 * This toolbar is the frontend-only half of that: it renders the selectable
 * list, keeps a single batch, and hands the ticked ids to the caller. It owns
 * no store — the parent decides what archive and delete mean.
 */

export interface SessionBatchToolbarProps {
  items: SessionBatchItem[];
  onArchive?: (ids: string[]) => void;
  onDelete?: (ids: string[]) => void;
  /** Leave batch mode (e.g. clear the caller's flag). */
  onExit?: () => void;
  /** A batch action is in flight; all controls lock. */
  busy?: boolean;
  className?: string;
}

export function SessionBatchToolbar({
  items,
  onArchive,
  onDelete,
  onExit,
  busy = false,
  className,
}: SessionBatchToolbarProps) {
  const { t } = useI18n();
  const ids = useMemo(() => items.map((item) => item.id), [items]);
  const selection = useSessionBatchSelection(ids);
  const selectAllRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = selection.someSelected;
  }, [selection.someSelected]);

  if (items.length === 0) {
    return (
      <div
        data-testid="session-batch-toolbar"
        data-state="empty"
        role="status"
        className={cn(
          'rounded-[var(--radius-md)] border border-dashed border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-[var(--space-3)] py-[var(--space-3)] text-center text-[length:var(--text-xs)] text-[var(--color-text-muted)]',
          className,
        )}
      >
        {t('sessions.batch_empty', { defaultValue: '没有可批量操作的会话' })}
      </div>
    );
  }

  const countLabel = t('sessions.batch_count', {
    count: selection.count,
    defaultValue: '已选 {{count}} 项',
  });

  const run = (action?: (selectedIds: string[]) => void) => {
    if (!action || selection.count === 0 || busy) return;
    action(selection.selectedIds);
    selection.clear();
  };

  return (
    <section
      data-testid="session-batch-toolbar"
      data-state="ready"
      aria-label={t('sessions.batch_mode', { defaultValue: '批量选择会话' })}
      className={cn(
        'overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]',
        className,
      )}
    >
      <header className="flex flex-wrap items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)]">
        <label className="flex min-w-0 items-center gap-[var(--space-2)]">
          <input
            ref={selectAllRef}
            type="checkbox"
            checked={selection.allSelected}
            onChange={(event) => selection.toggleAll(event.target.checked)}
            disabled={busy}
            aria-label={t('sessions.batch_select_all', { defaultValue: '全选' })}
            className="size-4 shrink-0 accent-[var(--color-accent)]"
          />
          <CheckSquare size={14} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
        </label>

        <span role="status" className="min-w-0 flex-1 text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
          {countLabel}
        </span>

        <span className="flex shrink-0 items-center gap-[var(--space-1)]">
          {onArchive && (
            <Button
              type="button"
              size="xs"
              variant="outline"
              disabled={busy || selection.count === 0}
              onClick={() => run(onArchive)}
              className="motion-reduce:transition-none"
            >
              <Archive size={12} aria-hidden="true" />
              {t('sessions.batch_archive', { defaultValue: '归档所选' })}
            </Button>
          )}
          {onDelete && (
            <Button
              type="button"
              size="xs"
              variant="destructive"
              disabled={busy || selection.count === 0}
              onClick={() => run(onDelete)}
              className="motion-reduce:transition-none"
            >
              <Trash2 size={12} aria-hidden="true" />
              {t('sessions.batch_delete', { defaultValue: '删除所选' })}
            </Button>
          )}
          {onExit && (
            <Button
              type="button"
              size="xs"
              variant="ghost"
              disabled={busy}
              aria-label={t('sessions.batch_exit', { defaultValue: '退出批量模式' })}
              onClick={onExit}
              className="motion-reduce:transition-none"
            >
              <X size={12} aria-hidden="true" />
            </Button>
          )}
        </span>
      </header>

      <ul className="max-h-72 overflow-y-auto">
        {items.map((item) => {
          const checked = selection.isSelected(item.id);
          return (
            <li key={item.id} data-testid="session-batch-row">
              <label className="flex cursor-pointer items-center gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2)] transition-colors duration-100 hover:bg-[var(--color-bg-surface-3)] motion-reduce:transition-none">
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={busy}
                  onChange={() => selection.toggle(item.id)}
                  aria-label={t('sessions.batch_select_item', {
                    title: item.title,
                    defaultValue: '选择 {{title}}',
                  })}
                  className="size-4 shrink-0 accent-[var(--color-accent)]"
                />
                <span className="min-w-0 truncate text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                  {item.title}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default SessionBatchToolbar;
