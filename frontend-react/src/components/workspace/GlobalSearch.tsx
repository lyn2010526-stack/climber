import { useState, useEffect, useRef, useId } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {
  Search, Database, FileText, Users, ArrowUpDown, CornerDownLeft, ChevronDown, ChevronUp, Lock,
} from 'lucide-react';
import { api } from '../../api';
import { useI18n } from '../../i18n';
import type { Page } from '../../navigation/navConfig';

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;
const MAX_RESULTS = 20;

const RESULT_TYPES = ['document', 'memory', 'group'] as const;
type ResultType = (typeof RESULT_TYPES)[number];

interface SearchResult {
  id: string;
  type: ResultType;
  title: string;
  preview: string;
  score: number;
  timestamp: string;
}

/**
 * Where a result can be opened. `page` is the hash route from `App.tsx`, so it
 * has to be one of the navigation ids: the hash is read as a bare page name
 * (`getPageFromHash`) and anything else falls back to the chat page.
 */
export interface SearchTarget {
  page: Page;
  /** The row this target belongs to, so the page can locate it. */
  result: SearchResult;
}

/**
 * A group is the one result type with a real destination: `ClusterPage` lists
 * groups and shows the selected one, so `#cluster` is where a group is read.
 *
 * A document chunk has no detail surface. `GET /search` returns the chunk's
 * `document_id` and `content` and nothing that names the file, and the only
 * document view in the app is the chat right panel's file list, which takes no
 * selection. A memory has no endpoint, no page and no panel anywhere in the app.
 * Both are therefore preview-only: the row shows the text and says why it cannot
 * be opened, rather than routing somewhere that would not show the object.
 */
export function searchTarget(result: SearchResult): SearchTarget | null {
  return result.type === 'group' ? { page: 'cluster', result } : null;
}

const TYPE_ICONS = { document: FileText, memory: Database, group: Users } as const;
const TYPE_COLORS = {
  document: 'text-[var(--color-info)]',
  memory: 'text-[var(--color-accent)]',
  group: 'text-[var(--color-success)]',
} as const;

const isSearchResult = (item: unknown): item is SearchResult => {
  if (!item || typeof item !== 'object') return false;
  const candidate = item as Partial<SearchResult>;
  return typeof candidate.id === 'string'
    && typeof candidate.title === 'string'
    && typeof candidate.preview === 'string'
    && RESULT_TYPES.includes(candidate.type as ResultType);
};

/**
 * `GET /search` answers with document chunks as `{ id, document_id, content,
 * chunk_index, score, created_at }` and no `type`, `title` or `preview`, so those
 * rows are read as document chunks here. A row that already carries the display
 * fields is passed through, which keeps a future multi-type response working
 * without a second shape.
 */
const toSearchResult = (item: unknown): SearchResult | null => {
  if (isSearchResult(item)) return item;
  if (!item || typeof item !== 'object') return null;
  const chunk = item as Record<string, unknown>;
  if (typeof chunk.id !== 'string' || !chunk.id) return null;
  const documentId = typeof chunk.document_id === 'string' ? chunk.document_id : '';
  return {
    id: chunk.id,
    type: 'document',
    title: documentId || chunk.id,
    preview: typeof chunk.content === 'string' ? chunk.content : '',
    score: typeof chunk.score === 'number' ? chunk.score : 0,
    timestamp: typeof chunk.created_at === 'string' ? chunk.created_at : '',
  };
};

const readResults = (data: unknown): SearchResult[] | null => {
  const items = Array.isArray(data) ? data : (data as { results?: unknown } | null)?.results;
  if (!Array.isArray(items)) return null;
  const parsed = items.map(toSearchResult);
  return parsed.every((item): item is SearchResult => item !== null) ? parsed : null;
};

const resultKey = (result: SearchResult) => `${result.type}-${result.id}`;

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
  /**
   * Opens a result. Only results with a real destination reach it; a preview-only
   * result expands its text instead, so Enter never leaves the user somewhere
   * that does not show the object they picked.
   */
  onNavigate?: (target: SearchTarget) => void;
}

export function GlobalSearch({ isOpen, onClose, onNavigate }: GlobalSearchProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const listId = useId();

  useEffect(() => {
    let current = true;
    setResults([]);
    setError(null);
    setSelectedIndex(0);
    setExpanded(null);
    const trimmed = query.trim();
    if (!isOpen || trimmed.length < MIN_QUERY_LENGTH) {
      setLoading(false);
      return;
    }
    // Cleanup invalidates both pending debounce work and already running requests,
    // so a slower earlier response cannot land on top of a newer one.
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const items = readResults(await api.search(trimmed, MAX_RESULTS));
        if (!items) throw new Error('Invalid search response');
        if (current) setResults(items);
      } catch {
        if (current) setError(t('common.network_error'));
      } finally {
        if (current) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => { current = false; clearTimeout(timer); };
  }, [isOpen, query, retry, t]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setResults([]);
      setFilter('');
    }
  }, [isOpen]);

  const filtered = filter
    ? results.filter(r => r.type === filter)
    : results;
  const activeIndex = Math.min(selectedIndex, Math.max(filtered.length - 1, 0));

  /**
   * Open a result when it has a destination, otherwise reveal its full text. A
   * result with neither a destination nor a body would leave Enter inert, so
   * those rows report why they are preview-only.
   */
  const openResult = (result: SearchResult) => {
    const target = searchTarget(result);
    if (target && onNavigate) {
      onNavigate(target);
      onClose();
      return;
    }
    const key = resultKey(result);
    setExpanded(expanded === key ? null : key);
    inputRef.current?.focus();
  };

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView?.({ block: 'nearest' });
  }, [selectedIndex, filter, results]);

  return (
    <Dialog.Root open={isOpen} onOpenChange={open => { if (!open) onClose(); }}>
      <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/60" />
      <Dialog.Content
        aria-label={t('sidebar.global_search')}
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
        className="fixed left-1/2 top-[8dvh] z-[101] flex max-h-[84dvh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 flex-col overflow-hidden rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-xl)] outline-none sm:top-[12dvh] sm:max-h-[76dvh]"
      >
        {/* The field is the dialog's subject, so it opens the surface. */}
        <div className="flex items-center gap-3 px-4 py-3">
          <Search size={18} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-label={t('sidebar.global_search')}
            aria-expanded={true}
            aria-autocomplete="list"
            aria-controls={listId}
            aria-activedescendant={!loading && filtered[activeIndex] ? `${listId}-${resultKey(filtered[activeIndex])}` : undefined}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={event => {
              // Composition owns its own keys, and the list is stale mid-flight.
              if (event.nativeEvent.isComposing || loading) return;
              if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                setSelectedIndex(Math.max(0, Math.min(activeIndex + (event.key === 'ArrowDown' ? 1 : -1), filtered.length - 1)));
              } else if (event.key === 'Home' && filtered.length > 0) {
                event.preventDefault();
                setSelectedIndex(0);
              } else if (event.key === 'End' && filtered.length > 0) {
                event.preventDefault();
                setSelectedIndex(filtered.length - 1);
              } else if (event.key === 'Enter' && filtered[activeIndex]) {
                // Enter opens a result that has a destination, and reveals the
                // full text of one that is preview-only.
                event.preventDefault();
                openResult(filtered[activeIndex]);
              }
            }}
            placeholder={t('global_search.placeholder')}
            className="min-w-0 flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
          />
        </div>

        <div role="group" aria-label={t('common.filter')} className="flex flex-wrap gap-1 border-t border-[var(--color-border-subtle)] px-3 py-2">
          {(['', ...RESULT_TYPES] as const).map(f => {
            const label = f === '' ? t('global_search.all')
              : f === 'document' ? t('global_search.document')
              : f === 'memory' ? t('global_search.memory')
              : t('global_search.group');
            return (
              <button type="button"
                key={f || 'all'}
                 onClick={() => { setFilter(f); setSelectedIndex(0); setExpanded(null); }}
                 aria-pressed={filter === f}
                 className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                  filter === f
                    ? 'border border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]'
                    : 'border border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto border-t border-[var(--color-border-subtle)] p-2">
          {loading && (
            <div role="status" className="px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
              <div aria-hidden="true" className="mx-auto mb-2 h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent motion-reduce:animate-none" />
               {t('global_search.searching')}
            </div>
          )}
          {error && (
            <div role="alert" className="px-4 py-8 text-center text-sm text-[var(--color-error)]">
              <p>{error}</p>
              <button type="button" onClick={() => setRetry(value => value + 1)} className="mt-3 rounded-md border border-[var(--color-border-default)] px-3 py-1.5 text-[var(--color-text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">{t('common.retry')}</button>
            </div>
          )}
          {!loading && !error && filtered.length === 0 && (
            <div role="status" className="px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
               {query.trim().length < MIN_QUERY_LENGTH ? t('global_search.placeholder') : `${t('common.no_results')} "${query.trim()}"`}
            </div>
          )}
          <div ref={listRef} id={listId} role="listbox" aria-label={t('sidebar.global_search')} aria-busy={loading}>
          {!loading && !error && filtered.map((result, index) => {
            const Icon = TYPE_ICONS[result.type];
            const key = resultKey(result);
            const selected = index === activeIndex;
            const target = searchTarget(result);
            const canOpen = target !== null && onNavigate !== undefined;
            return (
              <button type="button"
                key={key}
                id={`${listId}-${key}`}
                role="option"
                 aria-selected={selected}
                 aria-describedby={`${listId}-${key}-preview${canOpen ? '' : ` ${listId}-${key}-note`}`}
                tabIndex={-1}
                onMouseDown={event => event.preventDefault()}
                onMouseEnter={() => setSelectedIndex(index)}
                onClick={() => { setSelectedIndex(index); openResult(result); }}
                className={`flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors ${selected ? 'bg-[var(--color-bg-surface-2)]' : 'hover:bg-[var(--color-bg-surface-2)]'}`}
              >
                <span className="shrink-0 pt-1">
                  <Icon size={14} aria-hidden="true" className={TYPE_COLORS[result.type]} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--color-text-primary)]">{result.title}</span>
                     <span className="shrink-0 text-[10px] text-[var(--color-text-muted)]">{t(`global_search.${result.type}`)}</span>
                  </span>
                   <span id={`${listId}-${key}-preview`} className={`mt-1 block text-xs leading-relaxed text-[var(--color-text-muted)] ${expanded === key ? 'whitespace-pre-wrap break-words' : 'truncate'}`}>{result.preview}</span>
                   {/* A row with no detail page says so, so pressing Enter on it
                       reads as "no place to go" instead of a dead key. */}
                   {!canOpen && (
                     <span id={`${listId}-${key}-note`} className="mt-1 flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
                       <Lock size={10} aria-hidden="true" className="shrink-0" />
                       {t(`global_search.preview_only.${result.type}`)}
                     </span>
                   )}
                 </span>
                 {canOpen
                   ? <CornerDownLeft size={14} aria-hidden="true" className="mt-1 shrink-0 text-[var(--color-text-muted)]" />
                   : expanded === key
                     ? <ChevronUp size={14} aria-hidden="true" className="mt-1 shrink-0 text-[var(--color-text-muted)]" />
                     : <ChevronDown size={14} aria-hidden="true" className="mt-1 shrink-0 text-[var(--color-text-muted)]" />}
              </button>
            );
          })}
          </div>
        </div>

        {/* The visible keys only: navigation, the open Enter performs, and
            closing through Escape needs no second label. */}
        <div className="flex items-center gap-4 border-t border-[var(--color-border-subtle)] px-4 py-2 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1"><ArrowUpDown size={12} aria-hidden="true" /> {t('common.navigate')}</span>
          <span className="flex items-center gap-1"><CornerDownLeft size={12} aria-hidden="true" /> {t('common.open')}</span>
        </div>
      </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
