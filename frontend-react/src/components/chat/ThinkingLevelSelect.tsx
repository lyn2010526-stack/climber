import { useCallback, useEffect, useState } from 'react';
import { Brain } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { api } from '../../api';

/**
 * Session-level thinking-effort selector (low / medium / high).
 *
 * The catalog and the current value come from the reasoning routes
 * (`GET /reasoning/levels`, `GET|PUT /reasoning/sessions/{id}/reasoning-level`);
 * the server persists the choice on the session's `context_data`. Selection is
 * optimistic with rollback on failure: a picker must never gate the composer
 * on a network round trip, and a failed write must not leave the UI lying
 * about the stored level.
 */

const FALLBACK_LEVELS = ['low', 'medium', 'high'] as const;

interface ThinkingLevelSelectProps {
  sessionId: string | null;
  className?: string;
}

export function ThinkingLevelSelect({ sessionId, className }: ThinkingLevelSelectProps) {
  const { t } = useI18n();
  const [level, setLevel] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setLevel(null);
    setError('');
    if (!sessionId) return undefined;
    let cancelled = false;
    api
      .getSessionThinkingLevel(sessionId)
      .then((data) => {
        if (!cancelled && typeof data?.level === 'string' && data.level) setLevel(data.level);
      })
      .catch(() => {
        // Unknown level: leave the control unselected; the first click still writes.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const select = useCallback(
    (next: string) => {
      if (!sessionId || pending || next === level) return;
      const previous = level;
      setLevel(next);
      setError('');
      setPending(true);
      api
        .updateSessionThinkingLevel(sessionId, next)
        .then(() => setPending(false))
        .catch(() => {
          setLevel(previous);
          setPending(false);
          setError(t('chat.thinking_level_error', { defaultValue: '思考等级保存失败，请重试' }));
        });
    },
    [sessionId, pending, level, t],
  );

  const groupLabel = t('chat.thinking_level', { defaultValue: '思考等级' });

  return (
    <div className={cn('flex min-w-0 flex-col items-end gap-0.5', className)}>
      <div
        role="group"
        aria-label={groupLabel}
        className="flex items-center gap-0.5 rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-0.5"
      >
        <Brain size={12} aria-hidden="true" className="ms-1.5 shrink-0 text-[var(--color-text-disabled)]" />
        {FALLBACK_LEVELS.map((id) => {
          const active = level === id;
          return (
            <button
              key={id}
              type="button"
              aria-pressed={active}
              disabled={!sessionId || pending}
              title={
                id === 'low'
                  ? t('chat.thinking_level_low_hint', { defaultValue: '低档：快速响应，适合简单问题' })
                  : id === 'high'
                    ? t('chat.thinking_level_high_hint', { defaultValue: '高档：深度推理，适合复杂问题' })
                    : t('chat.thinking_level_medium_hint', { defaultValue: '中档：速度与深度平衡（默认）' })
              }
              onClick={() => select(id)}
              className={cn(
                'h-6 rounded-full px-2.5 text-[length:var(--text-2xs)] font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
                active
                  ? 'bg-[var(--color-accent)] text-[var(--color-accent-foreground)]'
                  : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-secondary)]',
              )}
            >
              {id === 'low'
                ? t('chat.thinking_level_low', { defaultValue: '低' })
                : id === 'high'
                  ? t('chat.thinking_level_high', { defaultValue: '高' })
                  : t('chat.thinking_level_medium', { defaultValue: '中' })}
            </button>
          );
        })}
      </div>
      {error ? (
        <span role="alert" className="max-w-full truncate text-[length:var(--text-2xs)] text-[var(--color-error)]">
          {error}
        </span>
      ) : null}
    </div>
  );
}

export default ThinkingLevelSelect;
