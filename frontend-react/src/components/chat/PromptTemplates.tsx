import { useState } from 'react';
import { BookOpen, Code2, FileText, Search, Lightbulb, X, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface PromptTemplate {
  id: string;
  title: string;
  description: string;
  icon: typeof Code2;
  color: string;
  prompt: string;
  category: string;
}

interface PromptTemplatesProps {
  templates: PromptTemplate[];
  onSelect: (prompt: string) => void;
  className?: string;
}

export function PromptTemplates({ templates, onSelect, className }: PromptTemplatesProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = [...new Set(templates.map((t) => t.category))];
  const filtered = selectedCategory
    ? templates.filter((t) => t.category === selectedCategory)
    : templates;

  return (
    <div className={cn('w-full', className)}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium',
          'border transition-all duration-200',
          'hover:bg-[var(--color-bg-surface-3)]',
          isExpanded
            ? 'bg-[var(--color-bg-surface-3)] border-[var(--color-border-default)]'
            : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)]',
        )}
      >
        <BookOpen size={13} className="text-[var(--color-accent)]" />
        <span className="text-[var(--color-text-secondary)]">模板</span>
        <ChevronRight
          size={11}
          className={cn(
            'text-[var(--color-text-muted)] transition-transform duration-200',
            isExpanded && 'rotate-90',
          )}
        />
      </button>

      {isExpanded && (
        <div
          className="mt-3 rounded-2xl border overflow-hidden fade-enter"
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            borderColor: 'var(--color-border-default)',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
          }}
        >
          <div className="p-3">
            <div className="flex items-center gap-1.5 mb-3 flex-wrap">
              <button
                onClick={() => setSelectedCategory(null)}
                className={cn(
                  'px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors',
                  !selectedCategory
                    ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)]',
                )}
              >
                全部
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors',
                    selectedCategory === cat
                      ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)]',
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-2">
              {filtered.map((template) => {
                const Icon = template.icon;
                return (
                  <button
                    key={template.id}
                    onClick={() => {
                      onSelect(template.prompt);
                      setIsExpanded(false);
                    }}
                    className="flex items-start gap-2.5 p-2.5 rounded-xl text-left transition-colors hover:bg-[var(--color-bg-surface-3)]"
                  >
                    <div
                      className="p-1.5 rounded-lg shrink-0"
                      style={{ backgroundColor: `${template.color}15`, color: template.color }}
                    >
                      <Icon size={13} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-[var(--color-text-primary)] truncate">
                        {template.title}
                      </div>
                      <div className="text-[10px] text-[var(--color-text-muted)] line-clamp-2 mt-0.5">
                        {template.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
