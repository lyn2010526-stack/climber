import React, { useState } from 'react';
import { Shield, Eye, Zap, Check, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

export type PermissionMode = 'manual' | 'plan' | 'auto';

interface PermissionModeConfig {
  id: PermissionMode;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  features: string[];
}

const modes: PermissionModeConfig[] = [
  {
    id: 'manual',
    label: '手动模式',
    description: '每个操作都需要你的确认',
    icon: Shield,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    features: ['文件操作需确认', '命令执行需确认', '网络访问需确认', 'MCP 工具需确认'],
  },
  {
    id: 'plan',
    label: '计划模式',
    description: '先预览再执行',
    icon: Eye,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    features: ['只读预览操作', '显示执行计划', '批量确认变更', '可撤销任何操作'],
  },
  {
    id: 'auto',
    label: '自动模式',
    description: '全自动执行，仅高风险操作确认',
    icon: Zap,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    features: ['低风险自动执行', '高风险需确认', '网络访问需确认', '删除操作需确认'],
  },
];

interface PermissionModesProps {
  currentMode: PermissionMode;
  onModeChange: (mode: PermissionMode) => void;
  className?: string;
}

export function PermissionModes({
  currentMode,
  onModeChange,
  className,
}: PermissionModesProps) {
  const [hoveredMode, setHoveredMode] = useState<PermissionMode | null>(null);

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2 px-1 mb-3">
        <Shield size={14} className="text-[var(--color-text-secondary)]" />
        <span className="text-[11px] font-medium text-[var(--color-text-secondary)]">权限模式</span>
      </div>

      <div className="space-y-1.5">
        {modes.map((mode) => {
          const isActive = currentMode === mode.id;
          const isHovered = hoveredMode === mode.id;
          const Icon = mode.icon;

          return (
            <button
              key={mode.id}
              className={cn(
                'w-full flex items-start gap-3 px-3 py-2.5 rounded-xl border transition-all duration-200 text-left',
                isActive
                  ? 'border-white/[0.12] bg-white/[0.04]'
                  : 'border-white/[0.04] bg-transparent hover:bg-white/[0.02] hover:border-white/[0.08]'
              )}
              onClick={() => onModeChange(mode.id)}
              onMouseEnter={() => setHoveredMode(mode.id)}
              onMouseLeave={() => setHoveredMode(null)}
            >
              <div className={cn(
                'p-2 rounded-lg transition-colors',
                isActive ? mode.bgColor : 'bg-white/[0.03]'
              )}>
                <Icon
                  size={14}
                  className={cn(
                    'transition-colors',
                    isActive ? mode.color : 'text-[var(--color-text-secondary)]'
                  )}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'text-xs font-medium transition-colors',
                    isActive ? 'text-white' : 'text-[var(--color-text-secondary)]'
                  )}>
                    {mode.label}
                  </span>
                  {isActive && (
                    <Check size={11} className="text-green-400" />
                  )}
                  {mode.id === 'auto' && !isActive && (
                    <AlertTriangle size={10} className="text-amber-400/60" />
                  )}
                </div>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
                  {mode.description}
                </p>

                {/* Features tooltip on hover */}
                {isHovered && !isActive && (
                  <div className="mt-2 space-y-1 animate-[fadeIn_0.15s_ease_forwards]">
                    {mode.features.map((feature, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-secondary)]">
                        <div className="w-1 h-1 rounded-full bg-[var(--color-bg-surface-elevated)]" />
                        {feature}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Warning for auto mode */}
      {currentMode === 'auto' && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-500/[0.04] border border-amber-500/10 animate-[fadeIn_0.2s_ease_forwards]">
          <AlertTriangle size={12} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[10px] text-amber-400/80 leading-relaxed">
            自动模式下，智能体将直接执行低风险操作。高风险操作（如删除文件、网络访问）仍会请求确认。
          </p>
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-3px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export { modes as permissionModes };
