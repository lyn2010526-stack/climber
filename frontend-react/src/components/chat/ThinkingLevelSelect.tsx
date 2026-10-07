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

const LEVEL_TONE: Record<string, string> = {
  low: 'text-[var(--color-success)] data-[active=true]:bg-[var(--color-success)]/15',
  medium: 'text-[var(--color-warning)] data-[active=true]:bg-[var(--color-warning)]/15',
  high: 'text-[var(--color-info)] data-[active=true]:bg-[var(--color-info)]/15',
};

interface ThinkingLevelSelectProps {
  sessionId: string | null;
  className?: string;
}

export function ThinkingLevelSelect({ sessionId, className }: ThinkingLevelSelectProps) {
  const { t } = useI18n();
  const [level, setLevel] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  // Catalog from GET /reasoning/levels; the built-in trio stays as fallback so
  // a failed catalog read never leaves the composer without a picker.
  const [levels, setLevels] = useState<string[]>([...FALLBACK_LEVELS]);

  useEffect(() => {
    let cancelled = false;
    // Guard for test doubles that mock the api module without the catalog method.
    if (typeof api.getThinkingLevels !== 'function') return undefined;
    api
      .getThinkingLevels()
      .then((data) => {
        if (cancelled) return;
        const ids = Array.isArray(data?.levels)
          ? data.levels.map((entry) => entry?.id).filter((id): id is string => typeof id === 'string' && !!id)
          : [];
        if (ids.length > 0) setLevels(ids);
      })
      .catch(() => {
        // Catalog read failed: keep the fallback levels.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
  const currentLevel = level ?? levels[0];

  return (
    <div className={cn('flex min-w-0 flex-col items-end gap-0.5', className)}>
      <div
        role="group"
        aria-label={groupLabel}
        className="flex items-center gap-0.5 rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-0.5"
      >
        <Brain size={12} aria-hidden="true" className="ms-1.5 shrink-0 text-[var(--color-text-disabled)]" />
        {levels.map((id) => {
          const active = level === id;
          return (
            <button
              key={id}
              type="button"
              aria-pressed={active}
              data-active={active}
              disabled={!sessionId || pending}
              title={t(`chat.thinking_level_${id}_hint`, { defaultValue: id })}
              onClick={() => select(id)}
              className={cn(
                'h-6 rounded-full px-2.5 text-[11px] font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
                 LEVEL_TONE[id] ?? 'text-[var(--color-text-muted)]',
                 active
                   ? 'font-semibold'
                   : 'opacity-75 hover:bg-[var(--color-bg-surface-3)] hover:opacity-100',
              )}
            >
              {t(`chat.thinking_level_${id}`, { defaultValue: id })}
            </button>
          );
        })}
      </div>
      <span data-testid="thinking-level-description" className="max-w-[18rem] truncate text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t(`chat.thinking_level_${currentLevel}_hint`, { defaultValue: currentLevel })}
      </span>
      {error ? (
        <span role="alert" className="max-w-full truncate text-[length:var(--text-2xs)] text-[var(--color-error)]">
          {error}
        </span>
      ) : null}
    </div>
  );
}

export default ThinkingLevelSelect;
