import { Bot, Sparkles, Code2, Search, FileText } from 'lucide-react';
import { cn } from '../../lib/utils';

interface Suggestion {
  icon: 'code' | 'search' | 'file' | 'sparkle';
  title: string;
  prompt: string;
}

interface EmptyStateProps {
  title?: string;
  description?: string;
  suggestions?: Suggestion[];
  onSelectSuggestion?: (prompt: string) => void;
}

const iconMap = {
  code: Code2,
  search: Search,
  file: FileText,
  sparkle: Sparkles,
};

export function EmptyState({
  title = '开始新的对话',
  description = '输入任何问题或任务，AI 助手将为你自主执行。',
  suggestions = [
    { icon: 'code', title: '编写代码', prompt: '帮我写一个 Python 脚本来处理 CSV 文件' },
    { icon: 'search', title: '分析数据', prompt: '分析这段数据的趋势和异常值' },
    { icon: 'file', title: '文档处理', prompt: '帮我整理这份文档的结构' },
    { icon: 'sparkle', title: '创意思考', prompt: '给我一些产品设计的灵感' },
  ],
  onSelectSuggestion,
}: EmptyStateProps) {
  return (
    <div className="flex items-center justify-center h-full px-6">
      <div className="text-center max-w-lg">
        {/* Logo */}
        <div
          className="w-20 h-20 rounded-3xl flex items-center justify-center mx-auto mb-6"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent-glow), rgba(139, 92, 246, 0.1))',
            boxShadow: '0 0 40px var(--color-accent-glow)',
          }}
        >
          <Bot size={36} className="text-[var(--color-accent)]" />
        </div>

        {/* Title & Description */}
        <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2 tracking-tight">
          {title}
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-8 leading-relaxed max-w-sm mx-auto">
          {description}
        </p>

        {/* Suggestions grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
          {suggestions.map((suggestion, idx) => {
            const Icon = iconMap[suggestion.icon];
            return (
              <button
                key={idx}
                onClick={() => onSelectSuggestion?.(suggestion.prompt)}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-2xl text-sm text-left',
                  'border transition-all duration-200',
                  'hover:scale-[1.02] active:scale-[0.98]',
                )}
                style={{
                  backgroundColor: 'var(--color-bg-surface-1)',
                  borderColor: 'var(--color-border-subtle)',
                  color: 'var(--color-text-secondary)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-border-accent)';
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                  e.currentTarget.style.color = 'var(--color-text-primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-1)';
                  e.currentTarget.style.color = 'var(--color-text-secondary)';
                }}
              >
                <span
                  className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: 'var(--color-accent-subtle)' }}
                >
                  <Icon size={14} className="text-[var(--color-accent)]" />
                </span>
                <div className="min-w-0">
                  <div className="text-xs font-medium">{suggestion.title}</div>
                  <div className="text-[10px] text-[var(--color-text-muted)] truncate">
                    {suggestion.prompt}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
