import { cn } from '../../lib/utils';

interface ToggleSwitchProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  status?: 'idle' | 'starting' | 'ready' | 'error';
  className?: string;
}

export function ToggleSwitch({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  status = 'idle',
  className,
}: ToggleSwitchProps) {
  const statusColors = {
    idle: '',
    starting: 'border-yellow-500/50',
    ready: 'border-green-500/50',
    error: 'border-red-500/50',
  };

  const statusBadge = {
    idle: null,
    starting: <span className="text-[10px] text-yellow-400">启动中...</span>,
    ready: <span className="text-[10px] text-green-400">就绪</span>,
    error: <span className="text-[10px] text-red-400">失败</span>,
  };

  return (
    <div
      className={cn(
        'flex flex-col gap-3 p-5 rounded-2xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] transition-all duration-200',
        statusColors[status],
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{label}</h3>
            {statusBadge[status]}
          </div>
          <p className="mt-1 text-xs text-[var(--color-text-secondary)] leading-relaxed">
            {description}
          </p>
        </div>
        <button
          role="switch"
          aria-checked={checked}
          onClick={() => !disabled && onChange(!checked)}
          disabled={disabled}
          className={cn(
            'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200',
            checked ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-surface-2)]',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <span
            className={cn(
              'inline-block h-4 w-4 rounded-full bg-white shadow-lg transition-transform duration-200',
              checked ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
      </div>
    </div>
  );
}
