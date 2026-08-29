import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, X, Database, FileText, Users,
} from 'lucide-react';
import { api } from '../../api';

interface SearchResult {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  type?: 'document' | 'memory' | 'group';
  title?: string;
  preview?: string;
  score: number;
  created_at: string;
  timestamp?: string;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export function GlobalSearch({ isOpen, onClose }: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim() || q.trim().length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(q, 20);
      setResults(data);
    } catch {
      setError('网络错误');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    restoreFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    inputRef.current?.focus();

    return () => restoreFocusRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    const timer = setTimeout(() => performSearch(query), 300);
    return () => clearTimeout(timer);
  }, [query, performSearch]);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setResults([]);
      setFilter('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const filtered = filter
    ? results.filter(r => (r.type || 'document') === filter)
    : results;

  const typeIcon = (type: string) => {
    switch (type) {
      case 'document': return FileText;
      case 'memory': return Database;
      case 'group': return Users;
      default: return Search;
    }
  };

  const typeColor = (type: string) => {
    switch (type) {
      case 'document': return 'text-[var(--color-accent)]';
      case 'memory': return 'text-[var(--color-warning)]';
      case 'group': return 'text-[var(--color-success)]';
      default: return 'text-[var(--color-text-muted)]';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]" onClick={onClose} role="dialog" aria-modal="true" aria-label="全局搜索">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-[2px]" />
      <div
        className="relative w-full max-w-2xl overflow-hidden rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-lg)]"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-border-subtle)] px-4 py-3 sm:flex-nowrap">
          <Search size={20} className="text-[var(--color-text-muted)] shrink-0" />
           <input
             ref={inputRef}
             type="text"
             value={query}
             onChange={e => setQuery(e.target.value)}
             placeholder="搜索文档、记忆、群组..."
             aria-label="搜索文档、记忆和群组"
             className="min-w-48 flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
           />
          <div className="flex gap-1">
            {['', 'document', 'memory', 'group'].map(f => (
              <button
               key={f || 'all'}
                 type="button"
                 aria-label={`按${f ? (f === 'document' ? '文档' : f === 'memory' ? '记忆' : '群组') : '全部'}筛选`}
                 onClick={() => setFilter(f)}
                className={`rounded-md border px-2.5 py-1 text-[10px] font-semibold transition-colors duration-150 ${
                  filter === f
                    ? 'border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                    : 'border-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                 {f ? (f === 'document' ? '文档' : f === 'memory' ? '记忆' : f === 'group' ? '群组' : f) : '全部'}
              </button>
            ))}
          </div>
          <button onClick={onClose} aria-label="关闭全局搜索" className="rounded-lg p-1.5 text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]">
            <X size={16} />
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {loading && (
            <div className="px-4 py-8 text-center text-[var(--color-text-muted)] text-sm">
              <div className="mx-auto mb-2 h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent" />
               正在搜索...
            </div>
          )}
          {error && (
            <div className="px-4 py-8 text-center text-sm text-[var(--color-error)]">{error}</div>
          )}
          {!loading && !error && filtered.length === 0 && query && (
            <div className="px-4 py-8 text-center text-[var(--color-text-muted)] text-sm">
                未找到 "{query}" 的结果
            </div>
          )}
          {!loading && !error && filtered.map(result => {
            const resultType = result.type || 'document';
            const Icon = typeIcon(resultType);
            return (
              <button
                key={result.id}
                className="flex w-full items-start gap-3 border-b border-[var(--color-border-subtle)] px-5 py-3 text-left transition-colors last:border-0 hover:bg-[var(--color-bg-surface-2)]"
              >
                <div className="mt-0.5 shrink-0 rounded-md bg-[var(--color-bg-surface-2)] p-1.5">
                  <Icon size={14} className={typeColor(resultType)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{result.title || result.document_id}</span>
                    <span className="text-[10px] text-[var(--color-text-muted)] capitalize font-medium">{resultType}</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] truncate mt-0.5">{result.preview || result.content}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
