import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, FileText, Wrench, BookOpen, Hash } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface MentionItem {
  id: string;
  type: 'tool' | 'file' | 'knowledge' | 'prompt';
  name: string;
  description?: string;
  icon?: typeof FileText;
}

interface MentionPickerProps {
  items: MentionItem[];
  onSelect: (item: MentionItem) => void;
  onClose: () => void;
  position: { top: number; left: number };
  isOpen: boolean;
}

const typeConfig = {
  tool: { icon: Wrench, color: 'var(--color-error)', label: '工具' },
  file: { icon: FileText, color: 'var(--color-accent)', label: '文件' },
  knowledge: { icon: BookOpen, color: 'var(--color-success)', label: '知识库' },
  prompt: { icon: Hash, color: 'var(--color-warning)', label: '模板' },
};

export function MentionPicker({ items, onSelect, onClose, position, isOpen }: MentionPickerProps) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = items.filter(
    (item) =>
      item.name.toLowerCase().includes(query.toLowerCase()) ||
      item.description?.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filtered[activeIndex]) {
        e.preventDefault();
        onSelect(filtered[activeIndex]);
      } else if (e.key === 'Escape') {
        onClose();
      }
    },
    [filtered, activeIndex, onSelect, onClose],
  );

  useEffect(() => {
    const el = listRef.current?.children[activeIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  if (!isOpen) return null;

  return (
    <div
      className="absolute z-50 w-72 rounded-2xl border overflow-hidden"
      style={{
        bottom: `calc(100% - ${position.top}px)`,
        left: position.left,
        backgroundColor: 'var(--color-bg-surface-2)',
        borderColor: 'var(--color-border-default)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
      }}
    >
      <div className="p-2 border-b" style={{ borderColor: 'var(--color-border-subtle)' }}>
        <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-[var(--color-bg-surface-3)]">
          <Search size={12} className="text-[var(--color-text-muted)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索工具、文件、知识库..."
            className="flex-1 bg-transparent text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
          />
        </div>
      </div>

      <div ref={listRef} className="max-h-[200px] overflow-y-auto p-1.5">
        {filtered.length === 0 ? (
          <div className="px-3 py-4 text-center text-xs text-[var(--color-text-muted)]">
            未找到匹配项
          </div>
        ) : (
          filtered.map((item, index) => {
            const config = typeConfig[item.type];
            const Icon = item.icon ?? config.icon;
            return (
              <button
                key={item.id}
                onClick={() => onSelect(item)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-left transition-colors',
                  index === activeIndex
                    ? 'bg-[var(--color-bg-surface-3)]'
                    : 'hover:bg-[var(--color-bg-surface-3)]/50',
                )}
              >
                <div
                  className="p-1 rounded-md shrink-0"
                  style={{ backgroundColor: `${config.color}15`, color: config.color }}
                >
                  <Icon size={12} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-[var(--color-text-primary)] truncate">
                    {item.name}
                  </div>
                  {item.description && (
                    <div className="text-[10px] text-[var(--color-text-muted)] truncate">
                      {item.description}
                    </div>
                  )}
                </div>
                <span
                  className="text-[9px] font-medium px-1.5 py-0.5 rounded-md"
                  style={{ backgroundColor: `${config.color}15`, color: config.color }}
                >
                  {config.label}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
