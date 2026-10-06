import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import type { DeliverableEntry } from './deliverables';
import { isWebsiteEntry } from './deliverables';

const VISIBLE_LIMIT = 3;

function pathParts(path: string): { parent: string; name: string } {
  const separator = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
  if (separator < 0) return { parent: '', name: path };
  return { parent: path.slice(0, separator + 1), name: path.slice(separator + 1) };
}

function openWebsite(path: string): void {
  if (typeof window !== 'undefined') window.open(path, '_blank', 'noopener,noreferrer');
}

/**
 * Codex 风格回合交付物卡片：聚合最近一轮的文件变更与网页交付物。
 * 默认展示前 3 项，可展开 / 收起；文件行打开文件预览，网页行新标签打开。
 */
export function DeliverablesCard({
  entries,
  onOpenFile,
  className,
  'data-testid': testId,
}: {
  entries: readonly DeliverableEntry[];
  onOpenFile: (path: string) => void;
  className?: string;
  'data-testid'?: string;
}) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const files = entries.filter(entry => !isWebsiteEntry(entry));
  const websites = entries.length - files.length;
  const visible = expanded ? entries : entries.slice(0, VISIBLE_LIMIT);
  const hidden = entries.length - visible.length;
  const hasFiles = files.length > 0;
  const firstWebsite = entries.find(isWebsiteEntry);

  const summary = files.length > 0 && websites === 0
    ? t('anchored.deliverables.edited_files', { count: files.length })
    : files.length === 0 && websites > 0
      ? t('anchored.deliverables.websites', { count: websites })
      : t('anchored.deliverables.items', { count: entries.length });

  const subtitleClass =
    'mt-0 flex items-center gap-[var(--space-1)] border-0 bg-transparent p-0 text-start text-[length:var(--text-xs)] ' +
    'text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] hover:underline ' +
    'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]';

  const itemClass =
    'flex min-w-0 items-center gap-0 border-0 bg-transparent p-0 py-[var(--space-0-5)] text-start font-inherit ' +
    'text-[length:var(--text-xs)] leading-[var(--leading-normal)] transition-colors hover:text-[var(--color-text-primary)] ' +
    'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]';

  const moreClass =
    'mt-[var(--space-1-5)] flex items-center gap-[var(--space-1)] self-start border-0 bg-transparent p-0 ' +
    'text-[length:var(--text-2xs)] text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] ' +
    'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]';

  return (
    <section
      aria-label={summary}
      data-testid={testId ?? 'deliverables-card'}
      data-deliverables-count={entries.length}
      className={cn(
        'not-prose rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-2-5)]',
        className,
      )}
    >
      <header className="flex items-start gap-[var(--space-3)] border-b border-[var(--color-border-subtle)] pb-[var(--space-2)]">
        <span
          aria-hidden="true"
          className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]"
        >
          <WorkbenchIcon name={hasFiles ? 'file' : 'preview'} size={20} />
        </span>
        <div className="flex min-w-0 flex-col gap-[var(--space-0-5)]">
          <strong className="truncate text-[length:var(--text-sm)] font-medium leading-[var(--leading-normal)] text-[var(--color-text-primary)]">
            {summary}
          </strong>
          {hasFiles ? (
            <button type="button" className={subtitleClass} onClick={() => { setExpanded(true); }}>
              {t('anchored.deliverables.view_changes')} ↗
            </button>
          ) : firstWebsite ? (
            <button type="button" className={subtitleClass} onClick={() => { openWebsite(firstWebsite.path); }}>
              {t('anchored.deliverables.open_website')} ↗
            </button>
          ) : null}
        </div>
      </header>
      <div className="flex min-w-0 flex-col px-[var(--space-1-5)] pt-[var(--space-1-5)]">
        {visible.map(entry => {
          const website = isWebsiteEntry(entry);
          const parts = pathParts(entry.path);
          return (
            <button
              key={`${entry.kind}:${entry.path}`}
              type="button"
              title={entry.path}
              className={itemClass}
              onClick={() => {
                if (website) openWebsite(entry.path);
                else onOpenFile(entry.path);
              }}
            >
              {website ? (
                <span className="min-w-0 flex-1 truncate text-[var(--color-text-secondary)]">{entry.path}</span>
              ) : (
                <span className="flex min-w-0 flex-1 items-center gap-0">
                  {parts.parent !== '' && (
                    <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-[var(--color-text-muted)]">
                      {parts.parent}
                    </span>
                  )}
                  <span className="shrink-0 text-[var(--color-text-secondary)]">{parts.name || entry.path}</span>
                </span>
              )}
              {!website && (entry.added > 0 || entry.removed > 0) && (
                <span className="ml-[var(--space-2)] flex shrink-0 items-center gap-[var(--space-1-5)] text-[length:var(--text-xs)]">
                  {entry.added > 0 && <span className="text-[var(--color-success)]">+{entry.added}</span>}
                  {entry.removed > 0 && <span className="text-[var(--color-error)]">-{entry.removed}</span>}
                </span>
              )}
              {website && <span aria-hidden="true" className="ml-[var(--space-1)] shrink-0 text-[var(--color-text-muted)]">↗</span>}
            </button>
          );
        })}
      </div>
      {hidden > 0 && (
        <button type="button" className={moreClass} onClick={() => { setExpanded(true); }}>
          {t('anchored.deliverables.more', { count: hidden })}
          <ChevronDown size={14} aria-hidden="true" />
        </button>
      )}
      {expanded && entries.length > VISIBLE_LIMIT && (
        <button type="button" className={moreClass} onClick={() => { setExpanded(false); }}>
          {t('anchored.deliverables.collapse')}
          <ChevronUp size={14} aria-hidden="true" />
        </button>
      )}
    </section>
  );
}