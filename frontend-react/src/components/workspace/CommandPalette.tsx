import { useState, useEffect, useRef, useMemo, useId } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Search, ArrowUpDown, CornerDownLeft } from 'lucide-react';
import { ALL_NAV_ITEMS_BASE } from '../../navigation/navConfig';
import { rankCommands } from '../../lib/commandScore';
import { useI18n } from '../../i18n';

const MAX_DEFAULT_RESULTS = 8;

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
}

export default function CommandPalette({ isOpen, onClose, onNavigate }: CommandPaletteProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const listId = useId();

  const allItems = useMemo(() => ALL_NAV_ITEMS_BASE
    .map(item => ({
      id: item.id,
      label: t(item.labelKey ?? item.label ?? item.id),
      icon: item.icon,
      keywords: item.keywords ?? '',
      group: t(`nav_groups.${item.group ?? 'config'}`),
    })), [t]);

  /* An empty query shows the first eight entries in nav-config order, so the
     palette opens on the work group's leading commands rather than on a list
     reordered by a scorer that had nothing to score against. */
  const filtered = useMemo(() => {
    if (!query.trim()) return allItems.slice(0, MAX_DEFAULT_RESULTS);
    return rankCommands(allItems, query);
  }, [query, allItems]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView?.({ block: 'nearest' });
  }, [selectedIndex, query]);

  /* Groups keep the declaration order of the navigation config, so the rows a
     reader sees are the rows the arrow keys walk, and both end on one flat list. */
  const groupOrder = useMemo(() => {
    const seen = new Set<string>();
    for (const item of filtered) seen.add(item.group);
    return [...seen];
  }, [filtered]);
  const ordered = useMemo(
    () => groupOrder.flatMap(group => filtered.filter(item => item.group === group)),
    [groupOrder, filtered],
  );
  const activeIndex = Math.min(selectedIndex, Math.max(ordered.length - 1, 0));

  return (
    <Dialog.Root open={isOpen} onOpenChange={open => { if (!open) onClose(); }}>
      <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/60" />
      <Dialog.Content
        aria-label={t('common.command_palette')}
        aria-describedby={undefined}
        onOpenAutoFocus={event => {
          event.preventDefault();
          previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
          inputRef.current?.focus();
        }}
        onCloseAutoFocus={event => {
          event.preventDefault();
          if (previousFocusRef.current?.isConnected) previousFocusRef.current.focus();
        }}
        className="fixed left-1/2 top-[8dvh] z-[101] flex max-h-[84dvh] w-[calc(100%-2rem)] max-w-[600px] -translate-x-1/2 flex-col overflow-hidden rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-xl)] outline-none sm:top-[12dvh] sm:max-h-[min(560px,76dvh)]"
      >
        {/* The input is the palette; a heading and a tally above it restated it. */}
        <div className="flex items-center gap-3 px-4 py-3">
          <Search size={18} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-label={t('common.command_palette')}
            aria-expanded={true}
            aria-autocomplete="list"
            aria-controls={listId}
            aria-activedescendant={ordered[activeIndex] ? `${listId}-${ordered[activeIndex].id}` : undefined}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={event => {
              // A key that concludes IME composition belongs to the composition.
              if (event.nativeEvent.isComposing) return;
              if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                setSelectedIndex(Math.max(0, Math.min(activeIndex + (event.key === 'ArrowDown' ? 1 : -1), ordered.length - 1)));
              } else if (event.key === 'Home' && ordered.length > 0) {
                event.preventDefault();
                setSelectedIndex(0);
              } else if (event.key === 'End' && ordered.length > 0) {
                event.preventDefault();
                setSelectedIndex(ordered.length - 1);
              } else if (event.key === 'Enter' && ordered[activeIndex]) {
                event.preventDefault();
                onNavigate(ordered[activeIndex].id);
                onClose();
              }
            }}
            placeholder={`${t('common.search')}...`}
            className="min-w-0 flex-1 bg-transparent text-sm text-[var(--color-text-primary)] outline-none"
          />
        </div>

        <div ref={listRef} id={listId} role="listbox" aria-label={t('common.command_palette')} className="min-h-0 flex-1 overflow-y-auto border-t border-[var(--color-border-subtle)] p-2">
          {ordered.length === 0 ? (
            <div role="status" className="py-10 text-center text-sm text-[var(--color-text-muted)]">
              {t('common.no_results')} "{query}"
            </div>
          ) : (
            groupOrder.map(group => (
              <div key={group} role="group" aria-label={group} className="mb-2 last:mb-0">
                <div aria-hidden="true" className="px-3 py-2 text-[11px] font-medium text-[var(--color-text-muted)]">
                  {group}
                </div>
                <div className="space-y-0.5">
                  {filtered.filter(item => item.group === group).map((item) => {
                     const globalIndex = ordered.indexOf(item);
                    const IconComponent = item.icon;
                    const selected = globalIndex === activeIndex;
                    return (
                      <button type="button"
                        key={item.id}
                        id={`${listId}-${item.id}`}
                        role="option"
                        aria-selected={selected}
                        tabIndex={-1}
                        onMouseDown={event => event.preventDefault()}
                        onClick={() => { onNavigate(item.id); onClose(); }}
                        className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                          selected
                            ? 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)]'
                            : 'text-[var(--color-text-secondary)]'
                        }`}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                      >
                        <span className={`shrink-0 ${selected ? 'text-[var(--color-accent-foreground)]' : 'text-[var(--color-text-muted)]'}`}>
                          <IconComponent size={14} aria-hidden="true" />
                        </span>
                        <span className="min-w-0 flex-1 truncate">{item.label}</span>
                        {selected && <CornerDownLeft size={14} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Only the gestures that work are named here: these keys move and open
            rows, and Escape closes the dialog without a second label for it. */}
        <div className="flex items-center gap-4 border-t border-[var(--color-border-subtle)] px-4 py-2 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <ArrowUpDown size={12} aria-hidden="true" /> {t('common.navigate')}
          </span>
          <span className="flex items-center gap-1">
            <CornerDownLeft size={12} aria-hidden="true" /> {t('common.open')}
          </span>
        </div>
      </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
