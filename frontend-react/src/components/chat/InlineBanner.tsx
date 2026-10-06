import { useEffect, useMemo, useState } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

/**
 * Ported from codex `tui/src/bottom_pane/actionable_banner.rs` (`ActionableBanner`
 * → `InlineBanner`). A notice that sits above the composer without interrupting
 * a draft: a bold title, an optional description, and either a numbered action
 * list (Actions variant) or a lone hint line (Information variant).
 *
 * Codex semantics preserved here:
 * - Header copy is word-wrapped and capped at eight display lines; an overflow
 *   shows seven lines plus a dim "…" (`BannerContent::wrapped_lines`).
 * - The footer hint is chosen from the four (dismissal × has-actions) cases and
 *   rendered dim.
 * - `esc` dismisses only a `dismissible` banner; digits 1-9 pick an action.
 *   Codex only reads these keys while the composer is empty so typing keeps
 *   flowing; the web port mirrors that by ignoring keys whose target is an
 *   editable element, so the banner never steals keystrokes.
 */

export type InlineBannerDismissal = 'dismissible' | 'persistent';

export interface InlineBannerAction {
  id: string;
  label: string;
}

export interface InlineBannerProps {
  title: string;
  description?: string;
  actions?: InlineBannerAction[];
  dismissal?: InlineBannerDismissal;
  onSelect?: (actionId: string) => void;
  onDismiss?: () => void;
  className?: string;
}

const MAX_HEADER_LINES = 8;

interface HeaderLine {
  text: string;
  bold: boolean;
}

interface HeaderLines {
  lines: HeaderLine[];
  truncated: boolean;
}

/**
 * Title lines are bold, description lines are not; the combined run is capped
 * the way codex caps `BannerContent` — at most seven real lines plus a "…".
 */
function buildHeaderLines(title: string, description?: string): HeaderLines {
  const titleLines = title
    .split('\n')
    .filter((line) => line.length > 0)
    .map((text) => ({ text, bold: true }));
  const descriptionLines = (description ?? '')
    .split('\n')
    .filter((line) => line.length > 0)
    .map((text) => ({ text, bold: false }));
  const lines = [...titleLines, ...descriptionLines];
  if (lines.length > MAX_HEADER_LINES) {
    return { lines: lines.slice(0, MAX_HEADER_LINES - 1), truncated: true };
  }
  return { lines, truncated: false };
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.isContentEditable
  );
}

export function InlineBanner({
  title,
  description,
  actions = [],
  dismissal = 'dismissible',
  onSelect,
  onDismiss,
  className,
}: InlineBannerProps) {
  const { t } = useI18n();
  const [dismissed, setDismissed] = useState(false);
  const hasActions = actions.length > 0;

  const header = useMemo(() => buildHeaderLines(title, description), [title, description]);
  const headerLines = header.lines;
  const truncated = header.truncated;

  // esc dismisses a dismissible banner; digits 1-9 fire an action. Keys aimed
  // at an editable element are left alone so typing continues into the composer.
  useEffect(() => {
    if (dismissed) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || isEditableTarget(event.target)) return;
      if (event.key === 'Escape') {
        if (dismissal !== 'dismissible') return;
        setDismissed(true);
        onDismiss?.();
        return;
      }
      if (!hasActions) return;
      if (event.key >= '1' && event.key <= '9') {
        const index = Number(event.key) - 1;
        const action = actions[index];
        if (action) onSelect?.(action.id);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [dismissed, dismissal, hasActions, actions, onSelect, onDismiss]);

  if (dismissed) return null;

  // The four (dismissal × has-actions) hint strings, dim in codex.
  const hint = dismissal === 'persistent'
    ? hasActions
      ? t('banner.hint_persistent_actions', { defaultValue: '按数字键选择' })
      : ''
    : hasActions
      ? t('banner.hint_dismissible_actions', { defaultValue: '按数字键选择 · esc 关闭 · 输入可继续' })
      : t('banner.hint_dismissible', { defaultValue: 'esc 关闭 · 输入可继续' });

  return (
    <div
      role="status"
      data-dismissal={dismissal}
      className={cn(
        'border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]',
        // codex insets the content by (1, 2, 1, 2) cells.
        'px-[var(--space-4)] py-[var(--space-2)]',
        className,
      )}
    >
      <div className="min-w-0">
        {headerLines.map((line, index) => (
          <p
            key={index}
            className={cn(
              'text-[length:var(--text-sm)] leading-[var(--leading-normal)]',
              line.bold
                ? 'font-semibold text-[var(--color-text-primary)]'
                : 'text-[var(--color-text-secondary)]',
            )}
          >
            {line.text}
          </p>
        ))}
        {truncated && (
          <p aria-hidden="true" className="text-[length:var(--text-sm)] text-[var(--color-text-muted)]">…</p>
        )}
      </div>

      {hasActions && (
        <ul className="mt-[var(--space-2)] flex flex-col gap-0.5">
          {actions.map((action, index) => (
            <li key={action.id}>
              <button
                type="button"
                onClick={() => onSelect?.(action.id)}
                className="group flex w-full items-baseline gap-[var(--space-2)] rounded-[var(--radius-md)] px-[var(--space-2)] py-[var(--space-1)] text-left text-[length:var(--text-sm)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] focus-visible:bg-[var(--color-bg-surface-2)]"
              >
                <span className="shrink-0 font-[var(--font-mono)] text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)]">
                  {index + 1}.
                </span>
                <span className="min-w-0">{action.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {hint && (
        <p className="mt-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
          {hint}
        </p>
      )}
    </div>
  );
}
