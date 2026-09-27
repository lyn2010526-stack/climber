import { AlertTriangle, Loader2, RotateCcw, ShieldQuestion } from 'lucide-react';
import type { PermissionMode } from '../../store/workspace';
import { PERMISSION_MODES, PERMISSION_MODE_INFO } from './permissionMode';

interface PermissionModeToggleProps {
  /** Mode reported by the backend, or `null` when it has not reported one. */
  value: PermissionMode | null;
  onChange: (mode: PermissionMode) => void;
  disabled?: boolean;
  loading?: boolean;
  /** Reason the configuration could not be read or written, when there is one. */
  error?: string | null;
  onRetry?: () => void;
}

/**
 * One control for the permission mode the backend actually enforces. Every
 * button is a value of `PermissionMode`, so choosing one issues
 * `PUT /permissions/config` and nothing here claims an access level the rule
 * engine does not grant. While the configuration is unreadable the whole group
 * says so instead of defaulting to a mode.
 */
export function PermissionModeToggle({
  value,
  onChange,
  disabled = false,
  loading = false,
  error = null,
  onRetry,
}: PermissionModeToggleProps) {
  if (value === null) {
    return (
      <div className="space-y-1.5" role="status">
        <p className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
          {loading ? (
            <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          ) : (
            <ShieldQuestion size={13} aria-hidden="true" />
          )}
          {loading ? '正在读取后端权限模式' : '权限模式未上报'}
        </p>
        {error && (
          <p className="flex items-start gap-1.5 text-[11px] text-[var(--color-warning)]">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>后端未返回权限配置：{error}</span>
          </p>
        )}
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-2 py-1 text-[11px] text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
          >
            <RotateCcw size={11} aria-hidden="true" />
            重试读取
          </button>
        )}
      </div>
    );
  }

  const active = PERMISSION_MODE_INFO[value];

  return (
    <div className="space-y-1.5">
      <div role="radiogroup" aria-label="权限模式" className="flex flex-wrap gap-1">
        {PERMISSION_MODES.map((mode) => {
          const info = PERMISSION_MODE_INFO[mode];
          const selected = mode === value;
          return (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled || loading}
              onClick={() => onChange(mode)}
              title={info.summary}
              className={`rounded-[var(--radius-md)] border px-2 py-1 text-[11px] transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                selected
                  ? 'border-[var(--color-border-accent)] bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]'
                  : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-border-default)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {info.label}
            </button>
          );
        })}
      </div>
      <p className="text-[11px] text-[var(--color-text-muted)]">
        后端模式 <span className="font-mono text-[var(--color-text-secondary)]">{value}</span> · {active.summary}
      </p>
      {error && (
        <p role="alert" className="flex items-start gap-1.5 text-[11px] text-[var(--color-warning)]">
          <AlertTriangle size={12} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>权限模式更新失败：{error}</span>
        </p>
      )}
    </div>
  );
}
