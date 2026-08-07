import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Cpu, Zap, Globe, Code2, Eye, MessageSquare, Sparkles, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  capabilities: ModelCapability[];
  contextWindow: number;
  status: 'available' | 'busy' | 'offline';
  latency?: number;
  costPer1k?: number;
}

export type ModelCapability = 'chat' | 'code' | 'vision' | 'tools' | 'reasoning' | 'search';

const capabilityConfig: Record<ModelCapability, { icon: typeof Cpu; label: string; color: string }> = {
  chat: { icon: MessageSquare, label: '对话', color: 'var(--color-accent)' },
  code: { icon: Code2, label: '代码', color: 'var(--color-success)' },
  vision: { icon: Eye, label: '视觉', color: 'var(--color-warning)' },
  tools: { icon: Zap, label: '工具', color: 'var(--color-error)' },
  reasoning: { icon: Sparkles, label: '推理', color: 'var(--color-accent)' },
  search: { icon: Globe, label: '搜索', color: 'var(--color-success)' },
};

const statusConfig = {
  available: { label: '可用', color: 'var(--color-success)', dot: 'var(--color-success)' },
  busy: { label: '繁忙', color: 'var(--color-warning)', dot: 'var(--color-warning)' },
  offline: { label: '离线', color: 'var(--color-text-muted)', dot: 'var(--color-text-muted)' },
};

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
  className?: string;
}

export function ModelSelector({ models, selectedModel, onSelect, className }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const activeModel = models.find((m) => m.id === selectedModel) ?? models[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium',
          'border transition-all duration-200',
          'hover:bg-[var(--color-bg-surface-3)]',
          isOpen
            ? 'bg-[var(--color-bg-surface-3)] border-[var(--color-border-default)]'
            : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)]',
        )}
      >
        <Cpu size={13} className="text-[var(--color-accent)]" />
        <span className="text-[var(--color-text-primary)] max-w-[100px] truncate">
          {activeModel?.name ?? '选择模型'}
        </span>
        <ChevronDown
          size={12}
          className={cn(
            'text-[var(--color-text-muted)] transition-transform duration-200',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-80 rounded-2xl border overflow-hidden z-50 fade-enter"
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            borderColor: 'var(--color-border-default)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          }}
        >
          <div className="p-2 max-h-[320px] overflow-y-auto">
            {models.map((model) => {
              const CapIcon = model.capabilities[0]
                ? capabilityConfig[model.capabilities[0]].icon
                : Cpu;
              const isSelected = model.id === selectedModel;
              const status = statusConfig[model.status];

              return (
                <button
                  key={model.id}
                  onClick={() => {
                    onSelect(model.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-start gap-3 p-2.5 rounded-xl text-left transition-colors',
                    isSelected
                      ? 'bg-[var(--color-accent-subtle)]'
                      : 'hover:bg-[var(--color-bg-surface-3)]',
                  )}
                >
                  <div
                    className="p-1.5 rounded-lg shrink-0 mt-0.5"
                    style={{
                      backgroundColor: isSelected
                        ? 'var(--color-accent-subtle)'
                        : 'var(--color-bg-surface-3)',
                      color: isSelected ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                    }}
                  >
                    <CapIcon size={14} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                        {model.name}
                      </span>
                      {isSelected && (
                        <Check size={12} className="text-[var(--color-accent)] shrink-0" />
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        {model.provider}
                      </span>
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: status.dot }}
                      />
                      <span className="text-[10px]" style={{ color: status.color }}>
                        {status.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                      {model.capabilities.map((cap) => {
                        const config = capabilityConfig[cap];
                        const CapIcon = config.icon;
                        return (
                          <span
                            key={cap}
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[9px] font-medium"
                            style={{
                              backgroundColor: `${config.color}15`,
                              color: config.color,
                            }}
                          >
                            <CapIcon size={9} />
                            {config.label}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  {model.latency && (
                    <div className="text-[10px] text-[var(--color-text-muted)] shrink-0 mt-1">
                      {model.latency}ms
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
