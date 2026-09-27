import { useCallback } from 'react';
import { Hand, Gauge, Rocket } from 'lucide-react';
import type { PermissionMode } from '../../store/workspace';
import {
  AUTONOMY_STOPS,
  PERMISSION_MODE_INFO,
  autonomyLevelForMode,
  modeForAutonomyMove,
} from './permissionMode';

interface AutonomySliderProps {
  /** Mode reported by the backend, or `null` when nothing has been reported. */
  value: PermissionMode | null;
  onChange: (mode: PermissionMode) => void;
  disabled?: boolean;
}

/**
 * The scale is a view of the backend permission mode: each stop names the mode
 * it writes, and the caption states that mode's real rule instead of promising
 * an approval prompt the backend does not implement. An unreadable
 * configuration disables the control and says so.
 */
const STOP_ICONS = [Hand, Gauge, Gauge, Rocket, Rocket];

export function AutonomySlider({ value, onChange, disabled = false }: AutonomySliderProps) {
  const level = autonomyLevelForMode(value);
  const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    // The level is resolved to a mode here; the caller writes it to the backend.
    const next = modeForAutonomyMove(Number(event.target.value), value);
    if (next) onChange(next);
  }, [onChange, value]);

  if (value === null || level === null) {
    return (
      <div className="w-full">
        <p className="text-[11px] text-[var(--color-text-muted)]" role="status">
          自主级别未上报：后端权限模式读取失败，无法换算自主级别
        </p>
      </div>
    );
  }

  const percentage = ((level - 1) / 4) * 100;
  const Icon = STOP_ICONS[level - 1] ?? Gauge;

  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={15} className="text-[var(--color-text-secondary)]" aria-hidden="true" />
        <span className="text-xs font-medium text-[var(--color-text-primary)]">
          自主级别: <span className="text-[var(--color-text-secondary)]">{PERMISSION_MODE_INFO[value].label}</span>
        </span>
        <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
          {PERMISSION_MODE_INFO[value].summary}
        </span>
      </div>

      <div className="relative">
        <div className="relative h-2 bg-[var(--color-bg-surface-elevated)] rounded-full overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-[var(--color-accent)] transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-[var(--color-accent)] shadow-lg transition-all duration-300"
            style={{ left: `${percentage}%` }}
          />
        </div>

        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={level}
          disabled={disabled}
          onChange={handleChange}
          aria-label="自主级别（写入后端权限模式）"
          className="absolute inset-0 w-full h-2 opacity-0 cursor-pointer disabled:cursor-not-allowed"
          style={{ top: '0px' }}
        />
      </div>

      <div className="flex justify-between mt-2 px-0.5">
        {AUTONOMY_STOPS.map((stop) => {
          const isCurrent = stop.level === level;
          const isActive = stop.level <= level;
          const info = PERMISSION_MODE_INFO[stop.mode];
          return (
            <button
              key={stop.level}
              type="button"
              disabled={disabled}
              onClick={() => onChange(stop.mode)}
              title={info.summary}
              className={`flex flex-col items-center gap-0.5 transition-all duration-200 disabled:opacity-50 ${
                isCurrent ? 'scale-105' : ''
              }`}
            >
              <span className={`text-[10px] font-medium transition-colors ${
                isCurrent
                  ? 'text-[var(--color-text-secondary)]'
                  : isActive
                    ? 'text-[var(--color-text-muted)]'
                    : 'text-[var(--color-text-disabled)]'
              }`}>
                {info.label}
              </span>
              <div className={`w-1.5 h-1.5 rounded-full transition-colors ${
                isCurrent
                  ? 'bg-[var(--color-accent)]'
                  : isActive
                    ? 'bg-[var(--color-text-secondary)]'
                    : 'bg-[var(--color-bg-surface-elevated)]'
              }`} />
            </button>
          );
        })}
      </div>
      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: transparent;
          cursor: pointer;
        }
        input[type="range"]::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: transparent;
          border: none;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}
