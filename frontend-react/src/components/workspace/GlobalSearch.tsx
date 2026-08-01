import { useState, useEffect, useCallback } from 'react';
import {
  Search, X, Database, FileText, Users,
} from 'lucide-react';
import { api } from '../../../api';

interface SearchResult {
  id: string;
  type: 'document' | 'memory' | 'group';
  title: string;
  preview: string;
  score: number;
  timestamp: string;
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

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim() || q.trim().length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(q, 20);
        setResults(data.results || []);
    } catch {
      setError('网络错误');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

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
    ? results.filter(r => r.type === filter)
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
      case 'document': return 'text-[#007AFF]';
      case 'memory': return 'text-[#AF52DE]';
      case 'group': return 'text-[#34C759]';
      default: return 'text-gray-500';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl bg-[#131A2A]/95 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/10">
          <Search size={20} className="text-gray-500 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="搜索文档、记忆、群组..."
            className="flex-1 bg-transparent text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none"
            autoFocus
          />
          <div className="flex gap-1">
            {['', 'document', 'memory', 'group'].map(f => (
              <button
                key={f || 'all'}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded-xl text-[10px] font-semibold transition-all duration-200 ${
                  filter === f
                    ? 'bg-[#007AFF]/20 text-white border border-[#007AFF]/30'
                    : 'text-gray-500 hover:text-gray-300 border border-transparent'
                }`}
              >
                 {f ? (f === 'document' ? '文档' : f === 'memory' ? '记忆' : f === 'group' ? '群组' : f) : '全部'}
              </button>
            ))}
          </div>
          <button onClick={onClose} className="p-1.5 text-gray-500 hover:text-gray-300 rounded-xl hover:bg-white/5 transition-all duration-200">
            <X size={16} />
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {loading && (
            <div className="px-4 py-8 text-center text-gray-500 text-sm">
              <div className="w-5 h-5 border-2 border-[#007AFF] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
               正在搜索...
            </div>
          )}
          {error && (
            <div className="px-4 py-8 text-center text-red-400 text-sm">{error}</div>
          )}
          {!loading && !error && filtered.length === 0 && query && (
            <div className="px-4 py-8 text-center text-gray-500 text-sm">
               未找到 "{query}" 的结果
            </div>
          )}
          {!loading && !error && filtered.map(result => {
            const Icon = typeIcon(result.type);
            return (
              <button
                key={result.id}
                className="w-full flex items-start gap-3 px-5 py-3 text-left hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
              >
                <div className={`p-1.5 rounded-xl shrink-0 mt-0.5 ${typeColor(result.type).replace('text-', 'bg-').replace(']', '/10]')}`}>
                  <Icon size={14} className={typeColor(result.type)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-100 truncate font-medium">{result.title}</span>
                    <span className="text-[10px] text-gray-500 capitalize font-medium">{result.type}</span>
                  </div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{result.preview}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
