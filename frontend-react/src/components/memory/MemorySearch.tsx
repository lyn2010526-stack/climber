import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Search, Filter, Sparkles, FileText, X,
  ChevronDown,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface SearchResult {
  id: string;
  fileName: string;
  path: string;
  snippet: string;
  score: number;
  scope: string;
  matchedTerms: string[];
}

const mockResults: SearchResult[] = [
  {
    id: '1', fileName: 'architecture.md', path: '/project/architecture.md',
    snippet: '基于微服务架构，使用 Rust 编写核心服务，前端使用 React + TypeScript...',
    score: 0.95, scope: 'project', matchedTerms: ['架构', '微服务'],
  },
  {
    id: '2', fileName: 'user-preferences.md', path: '/context/user-preferences.md',
    snippet: '用户偏好设置 - 界面语言: 简体中文，主题: 深色模式...',
    score: 0.87, scope: 'context', matchedTerms: ['用户', '偏好'],
  },
  {
    id: '3', fileName: 'decisions.md', path: '/project/decisions.md',
    snippet: 'ADR-001: 选择 Tokio 作为异步运行时，因为其性能优异...',
    score: 0.72, scope: 'project', matchedTerms: ['Tokio', '异步'],
  },
  {
    id: '4', fileName: 'session-notes.md', path: '/context/session-notes.md',
    snippet: '本次会话讨论了数据库迁移方案，决定使用渐进式迁移策略...',
    score: 0.65, scope: 'context', matchedTerms: ['数据库', '迁移'],
  },
];

const scopes = ['全部', 'project', 'context', 'memory'];

export function MemorySearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [activeScope, setActiveScope] = useState('全部');
  const [showScopeFilter, setShowScopeFilter] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const performSearch = useCallback((q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setSearching(true);
    setTimeout(() => {
      const filtered = mockResults.filter(r =>
        (activeScope === '全部' || r.scope === activeScope) &&
        (r.snippet.toLowerCase().includes(q.toLowerCase()) ||
         r.fileName.toLowerCase().includes(q.toLowerCase()) ||
         r.matchedTerms.some(t => t.toLowerCase().includes(q.toLowerCase())))
      );
      setResults(filtered.sort((a, b) => b.score - a.score));
      setSearching(false);
    }, 300);
  }, [activeScope]);

  const handleInputChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => performSearch(value), 200);
  };

  useEffect(() => {
    if (query) performSearch(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeScope]);

  const highlightText = (text: string, terms: string[]) => {
    let result = text;
    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      result = result.replace(regex, '<mark class="bg-[var(--color-accent)]/20 text-[var(--color-accent)] rounded px-0.5">$1</mark>');
    });
    return result;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search header */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-xl bg-gradient-to-br from-violet-500 to-purple-500 shadow-lg shadow-violet-500/20">
            <Sparkles size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">语义搜索</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">搜索所有记忆文件和上下文</p>
          </div>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => handleInputChange(e.target.value)}
            placeholder="搜索记忆内容..."
            className="w-full h-11 pl-11 pr-4 rounded-2xl bg-white/[0.04] border border-white/[0.08] text-sm text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/40 focus:bg-white/[0.06] focus:ring-1 focus:ring-[var(--color-accent)]/20 transition-all"
            autoFocus
          />
          {query && (
            <button
              onClick={() => { setQuery(''); setResults([]); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.06] transition-all"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {/* Scope filter */}
        <div className="flex items-center gap-2 mt-3">
          <div className="relative">
            <button
              onClick={() => setShowScopeFilter(!showScopeFilter)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[11px] text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.06] transition-all"
            >
              <Filter size={11} />
              {activeScope === '全部' ? '范围' : activeScope}
              <ChevronDown size={11} />
            </button>
            {showScopeFilter && (
              <div className="absolute top-full left-0 mt-1 py-1 bg-[#1A1A24] border border-white/[0.08] rounded-xl shadow-xl z-10 min-w-[120px]">
                {scopes.map(scope => (
                  <button
                    key={scope}
                    onClick={() => { setActiveScope(scope); setShowScopeFilter(false); }}
                    className={cn(
                      'w-full px-3 py-1.5 text-left text-[11px] transition-colors',
                       activeScope === scope ? 'text-[var(--color-accent)] bg-[var(--color-accent)]/10' : 'text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.04]'
                    )}
                  >
                    {scope}
                  </button>
                ))}
              </div>
            )}
          </div>
          {results.length > 0 && (
            <span className="text-[11px] text-[var(--color-text-muted)]">找到 {results.length} 个结果</span>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-5 pb-5">
        {searching ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-[var(--color-accent)]/30 border-t-[var(--color-accent)] rounded-full animate-spin mb-3" />
            <p className="text-xs text-[var(--color-text-muted)]">搜索中...</p>
          </div>
        ) : query && results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Search size={32} className="text-[var(--color-text-muted)] mb-3" />
            <p className="text-sm text-[var(--color-text-muted)]">没有找到相关结果</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">尝试其他关键词或调整范围</p>
          </div>
        ) : results.length > 0 ? (
          <div className="space-y-2">
            {results.map(result => (
              <SearchResultItem key={result.id} result={result} onHighlight={highlightText} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12">
            <Sparkles size={32} className="text-[var(--color-text-muted)] mb-3" />
            <p className="text-sm text-[var(--color-text-muted)]">开始搜索记忆</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">输入关键词查找相关文件和上下文</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SearchResultItem({ result, onHighlight }: { result: SearchResult; onHighlight: (text: string, terms: string[]) => string }) {
  const scorePercent = Math.round(result.score * 100);

  return (
    <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all cursor-pointer group">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={13} className="text-[var(--color-accent)] flex-shrink-0" />
          <span className="text-sm font-medium text-white truncate">{result.fileName}</span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div className={cn(
            'w-8 h-4 rounded-full flex items-center justify-center text-[9px] font-bold',
             scorePercent >= 80 ? 'bg-[var(--color-success)]/10 text-[var(--color-success)]' :
             scorePercent >= 50 ? 'bg-amber-500/10 text-amber-400' :
             'bg-[var(--color-text-muted)]/10 text-[var(--color-text-muted)]'
          )}>
            {scorePercent}
          </div>
        </div>
      </div>
      <p
         className="text-xs text-[var(--color-text-muted)] leading-relaxed line-clamp-2"
        dangerouslySetInnerHTML={{ __html: onHighlight(result.snippet, result.matchedTerms) }}
      />
      <div className="flex items-center gap-2 mt-2">
        <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-violet-500/10 text-violet-400">{result.scope}</span>
        <span className="text-[10px] text-[var(--color-text-muted)] truncate">{result.path}</span>
      </div>
    </div>
  );
}
