import { useCallback } from 'react';
import { Hand, Gauge, Rocket } from 'lucide-react';

interface AutonomySliderProps {
  value: number; // 1-5
  onChange: (level: number) => void;
}

const levels = [
  { level: 1, label: '手动', description: '每个操作前询问', icon: Hand },
  { level: 2, label: '半自动', description: '危险操作询问', icon: Gauge },
  { level: 3, label: '平衡', description: '破坏性操作询问', icon: Gauge },
  { level: 4, label: '自主', description: '不可逆操作询问', icon: Rocket },
  { level: 5, label: '全自动', description: '从不询问', icon: Rocket },
];

const activeColors = [
  'text-blue-400',
  'text-cyan-400',
  'text-violet-400',
  'text-purple-400',
  'text-fuchsia-400',
];

const activeBgColors = [
  'bg-blue-500',
  'bg-cyan-500',
  'bg-violet-500',
  'bg-purple-500',
  'bg-fuchsia-500',
];

const trackFillColors = [
  'from-blue-500/20',
  'from-cyan-500/20',
  'from-violet-500/20',
  'from-purple-500/20',
  'from-fuchsia-500/20',
];

export function AutonomySlider({ value, onChange }: AutonomySliderProps) {
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  }, [onChange]);

  const currentLevel = levels[value - 1];
  if (!currentLevel) return null;
  const Icon = currentLevel.icon;

  const percentage = ((value - 1) / 4) * 100;

  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={15} className={activeColors[value - 1]} />
        <span className="text-xs font-medium text-[var(--color-text-primary)]">
          自主级别: <span className={activeColors[value - 1]}>{currentLevel.label}</span>
        </span>
        <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">{currentLevel.description}</span>
      </div>

      <div className="relative">
        <div className="relative h-2 bg-[var(--color-bg-surface-elevated)] rounded-full overflow-hidden">
          <div
            className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${trackFillColors[value - 1]} to-transparent transition-all duration-300`}
            style={{ width: `${percentage}%` }}
          />
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full ${activeBgColors[value - 1]} shadow-lg transition-all duration-300`}
            style={{ left: `${percentage}%` }}
          />
        </div>

        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={value}
          onChange={handleChange}
          aria-label="自主级别"
          aria-valuemin={1}
          aria-valuemax={5}
          aria-valuenow={value}
          aria-valuetext={`${currentLevel.label}（${currentLevel.description}）`}
          className="absolute inset-0 w-full h-2 opacity-0 cursor-pointer"
          style={{ top: '0px' }}
        />
      </div>

      <div className="flex justify-between mt-2 px-0.5">
        {levels.map((item) => {
          const isActive = item.level <= value;
          const isCurrent = item.level === value;
          return (
            <button
              key={item.level}
              type="button"
              onClick={() => onChange(item.level)}
              className={`flex flex-col items-center gap-0.5 transition-all duration-200 ${
                isCurrent ? 'scale-105' : ''
              }`}
            >
              <span className={`text-[10px] font-medium transition-colors ${
                isCurrent
                  ? activeColors[value - 1]
                  : isActive
                    ? 'text-[var(--color-text-secondary)]'
                    : 'text-[var(--color-text-muted)]'
              }`}>
                {item.label}
              </span>
              <div className={`w-1.5 h-1.5 rounded-full transition-colors ${
                isCurrent
                  ? activeBgColors[value - 1]
                  : isActive
                    ? 'bg-[var(--color-bg-surface-elevated)]/50'
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
