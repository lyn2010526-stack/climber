import { useState, useMemo } from 'react';
import { Search, FileInput, Bot, Wrench, GitBranch, FileOutput, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

interface PaletteItem {
  type: string;
  label: string;
  icon: any;
  description: string;
  category: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'input', label: 'Input', icon: FileInput, description: 'User input variables', category: 'Data' },
  { type: 'output', label: 'Output', icon: FileOutput, description: 'Return results', category: 'Data' },
  { type: 'llm', label: 'LLM', icon: Bot, description: 'Call a language model', category: 'Processing' },
  { type: 'tool', label: 'Tool', icon: Wrench, description: 'Execute a tool', category: 'Processing' },
  { type: 'condition', label: 'Condition', icon: GitBranch, description: 'Branch by condition', category: 'Logic' },
];

const CATEGORY_ORDER = ['Data', 'Processing', 'Logic'];

const categoryColors: Record<string, string> = {
  Data: 'text-sky-400',
  Processing: 'text-violet-400',
  Logic: 'text-amber-400',
};

export function NodePalette() {
  const [search, setSearch] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(CATEGORY_ORDER));

  const filteredItems = useMemo(() => {
    if (!search) return PALETTE_ITEMS;
    const q = search.toLowerCase();
    return PALETTE_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.type.toLowerCase().includes(q)
    );
  }, [search]);

  const groupedItems = useMemo(() => {
    const groups: Record<string, PaletteItem[]> = {};
    for (const item of filteredItems) {
      const cat = item.category;
      if (!groups[cat]) groups[cat] = [];
      groups[cat]!.push(item);
    }
    return groups;
  }, [filteredItems]);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  const onDragStart = (event: React.DragEvent, type: string) => {
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5">
          Node Palette
        </h3>
        <div className="relative">
          <Search
            size={12}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search nodes..."
            className={cn(
              'w-full pl-7 pr-3 py-1.5 rounded-lg text-[11px]',
              'bg-[var(--color-bg-deep)]/50 border border-[var(--color-border-subtle)]',
              'text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]/50',
              'focus:outline-none focus:border-[var(--color-accent)]/40 transition-colors'
            )}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {CATEGORY_ORDER.map((category) => {
          const items = groupedItems[category];
          if (!items || items.length === 0) return null;
          const isExpanded = expandedCategories.has(category);

          return (
            <div key={category}>
              <button
                onClick={() => toggleCategory(category)}
                className="flex items-center gap-1.5 w-full px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
              >
                {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                <span className={categoryColors[category]}>{category}</span>
                <span className="ml-auto text-[9px] opacity-50">{items.length}</span>
              </button>
              {isExpanded && (
                <div className="space-y-0.5 mt-0.5">
                  {items.map((item) => (
                    <div
                      key={item.type}
                      draggable
                      onDragStart={(e) => onDragStart(e, item.type)}
                      className={cn(
                        'flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-grab',
                        'bg-[var(--color-bg-surface-elevated)]/50 border border-transparent',
                        'hover:bg-[var(--color-bg-surface-elevated)] hover:border-[var(--color-border-elevated)]',
                        'active:cursor-grabbing active:scale-[0.98]',
                        'transition-all duration-150'
                      )}
                    >
                      <div className={cn(
                        'p-1.5 rounded-md',
                        item.category === 'Data' && 'bg-sky-500/10 text-sky-400',
                        item.category === 'Processing' && 'bg-violet-500/10 text-violet-400',
                        item.category === 'Logic' && 'bg-amber-500/10 text-amber-400',
                      )}>
                        <item.icon size={13} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-medium text-[var(--color-text-primary)] leading-tight">
                          {item.label}
                        </p>
                        <p className="text-[9px] text-[var(--color-text-muted)] truncate leading-tight mt-0.5">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
