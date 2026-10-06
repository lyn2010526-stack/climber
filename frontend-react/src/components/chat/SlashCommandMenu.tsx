import React, { useEffect, useMemo } from 'react';
import { Terminal } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import type { SlashCommandInfo } from './slashCommands';

/**
 * Autocomplete dropdown for the chat composer. Purely presentational:
 * the composer owns which entries are visible and what selection does.
 *
 * Keyboard contract (handled by the composer, documented here):
 * - ArrowUp/ArrowDown move the highlight
 * - Enter/Tab accept the highlighted entry (Enter only completes, never sends)
 * - Escape closes the menu
 */
interface SlashCommandMenuProps {
  items: SlashCommandInfo[];
  activeIndex: number;
  onSelect: (command: SlashCommandInfo) => void;
  onHover: (index: number) => void;
  visible: boolean;
}

export const SlashCommandMenu: React.FC<SlashCommandMenuProps> = ({
  items,
  activeIndex,
  onSelect,
  onHover,
  visible,
}) => {
  const { t } = useI18n();
  const listId = 'slash-command-menu';
  const localized = useMemo(
    () =>
      items.map(item => ({
        ...item,
        localizedSummary: t(`slash.commands.${item.name}`, { defaultValue: item.summary }),
      })),
    [items, t],
  );

  useEffect(() => {
    if (!visible) return;
    const node = document.getElementById(`${listId}-item-${activeIndex}`);
    node?.scrollIntoView?.({ block: 'nearest' });
  }, [activeIndex, visible]);

  if (!visible || items.length === 0) return null;

  return (
    <div
      id={listId}
      role="listbox"
      aria-label={t('slash.menu_label', { defaultValue: '斜杠命令' })}
      className="absolute bottom-full left-0 right-0 z-30 mb-2 max-h-72 overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-lg"
    >
      <p className="px-3 pt-2 pb-1 text-[length:var(--text-2xs)] uppercase tracking-wide text-[var(--color-text-muted)]">
        {t('slash.menu_title', { defaultValue: '命令' })}
      </p>
      <ul className="pb-1">
        {localized.map((item, index) => (
          <li key={item.name}>
            <button
              type="button"
              id={`${listId}-item-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              onMouseEnter={() => onHover(index)}
              onMouseDown={e => {
                // mousedown so the textarea keeps focus when accepting.
                e.preventDefault();
                onSelect(item);
              }}
              className={cn(
                'flex w-full items-start gap-2 px-3 py-2 text-start transition-colors duration-100',
                index === activeIndex
                  ? 'bg-[var(--color-bg-surface-2)]'
                  : 'hover:bg-[var(--color-bg-surface-2)]',
                'focus-visible:outline-none',
              )}
            >
              <Terminal
                size={14}
                aria-hidden="true"
                className="mt-0.5 shrink-0 text-[var(--color-text-muted)]"
              />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-mono text-[13px] font-semibold text-[var(--color-text-primary)]">
                    /{item.name}
                  </span>
                  <span className="truncate font-mono text-xs text-[var(--color-text-muted)]">
                    {item.usage}
                  </span>
                </span>
                <span className="mt-0.5 block text-[13px] leading-normal text-[var(--color-text-secondary)]">
                  {item.localizedSummary}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SlashCommandMenu;
