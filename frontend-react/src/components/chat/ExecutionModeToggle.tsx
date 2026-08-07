import { useState } from 'react';
import { Brain, Zap, ChevronDown, Check, type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ExecutionMode = 'plan' | 'act' | 'auto';

interface ExecutionModeConfig {
  id: ExecutionMode;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
}

const modes: ExecutionModeConfig[] = [
  {
    id: 'plan',
    label: 'Plan',
    description: '先规划后执行，需确认',
    icon: Brain,
    color: 'var(--color-warning)',
  },
  {
    id: 'act',
    label: 'Act',
    description: '自主执行，无需确认',
    icon: Zap,
    color: 'var(--color-success)',
  },
  {
    id: 'auto',
    label: 'Auto',
    description: '智能判断执行策略',
    icon: Zap,
    color: 'var(--color-accent)',
  },
];

interface ExecutionModeToggleProps {
  mode: ExecutionMode;
  onChange: (mode: ExecutionMode) => void;
  className?: string;
}

export function ExecutionModeToggle({ mode, onChange, className }: ExecutionModeToggleProps) {
  const [isOpen, setIsOpen] = useState(false);
  const activeMode = modes.find((m) => m.id === mode) ?? modes[0]!;
  const ActiveIcon = activeMode?.icon;

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium',
          'border transition-all duration-200',
          'hover:bg-[var(--color-bg-surface-3)]',
          isOpen
            ? 'bg-[var(--color-bg-surface-3)] border-[var(--color-border-default)]'
            : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)]',
        )}
      >
        <ActiveIcon size={12} style={{ color: activeMode?.color }} />
        <span className="text-[var(--color-text-primary)]">{activeMode?.label}</span>
        <ChevronDown
          size={11}
          className={cn(
            'text-[var(--color-text-muted)] transition-transform duration-200',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-52 rounded-2xl border overflow-hidden z-50 fade-enter"
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            borderColor: 'var(--color-border-default)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          }}
        >
          <div className="p-1.5">
            {modes.map((m) => {
              const Icon = m.icon;
              const isSelected = m.id === mode;
              return (
                <button
                  key={m.id}
                  onClick={() => {
                    onChange(m.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left transition-colors',
                    isSelected
                      ? 'bg-[var(--color-accent-subtle)]'
                      : 'hover:bg-[var(--color-bg-surface-3)]',
                  )}
                >
                  <div
                    className="p-1 rounded-md"
                    style={{ backgroundColor: `${m.color}15`, color: m.color }}
                  >
                    <Icon size={12} />
                  </div>
                  <div className="flex-1">
                    <div className="text-xs font-medium text-[var(--color-text-primary)]">
                      {m.label}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-muted)]">{m.description}</div>
                  </div>
                  {isSelected && <Check size={12} className="text-[var(--color-accent)]" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
