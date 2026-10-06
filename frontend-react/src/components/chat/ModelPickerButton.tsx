import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { api } from '../../api';

/**
 * Session model picker for the chat composer.
 *
 * The catalog is `GET /models` (lazily fetched the first time the popover
 * opens); the binding is read from `GET /sessions/{id}` and written through
 * `api.setSessionModel`, which drives the server's `/model` slash command —
 * the only write path that persists a session's `model_settings` and rebinds
 * a warm engine session. Errors surface inside the popover, so a closed
 * picker never contributes unexpected content to the accessible tree.
 */

interface ModelEntry {
  provider: string;
  model_id: string;
  label?: string | null;
}

interface ModelPickerButtonProps {
  sessionId: string | null;
  /** Disabled while a turn streams so the binding cannot shift mid-run. */
  disabled?: boolean;
  /** Mobile composer height; desktop uses the compact composer scale. */
  compact?: boolean;
  className?: string;
}

export function ModelPickerButton({ sessionId, disabled = false, compact = false, className }: ModelPickerButtonProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<{ provider: string; modelId: string } | null>(null);
  const [models, setModels] = useState<ModelEntry[] | null>(null);
  const [applying, setApplying] = useState(false);
  const [actionError, setActionError] = useState('');
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setCurrent(null);
    setActionError('');
    if (!sessionId) return undefined;
    let cancelled = false;
    api
      .getSession(sessionId)
      .then((session) => {
        if (cancelled) return;
        const provider = typeof session?.provider === 'string' ? session.provider : '';
        const modelId = typeof session?.model_id === 'string' ? session.model_id : '';
        if (provider && modelId) setCurrent({ provider, modelId });
      })
      .catch(() => {
        // Unknown binding: the button falls back to a generic label until a
        // model is picked.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const grouped = useMemo(() => {
    if (!models) return [] as Array<{ provider: string; entries: ModelEntry[] }>;
    const byProvider = new Map<string, ModelEntry[]>();
    for (const entry of models) {
      if (!entry || typeof entry.provider !== 'string' || typeof entry.model_id !== 'string') continue;
      const bucket = byProvider.get(entry.provider) ?? [];
      bucket.push(entry);
      byProvider.set(entry.provider, bucket);
    }
    return [...byProvider.entries()].map(([provider, entries]) => ({ provider, entries }));
  }, [models]);

  const toggleOpen = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      if (next && models === null) {
        api
          .listModels()
          .then((data) => setModels(Array.isArray(data) ? data : []))
          .catch(() => {
            setModels([]);
            setActionError(t('chat.model_catalog_error', { defaultValue: '模型目录加载失败' }));
          });
      }
      if (next) setActionError('');
      return next;
    });
  }, [models, t]);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const applyModel = useCallback(
    (entry: ModelEntry) => {
      if (!sessionId || applying) return;
      setApplying(true);
      setActionError('');
      const previous = current;
      setCurrent({ provider: entry.provider, modelId: entry.model_id });
      api
        .setSessionModel(sessionId, entry.provider, entry.model_id)
        .then((applied) => {
          setCurrent({ provider: applied.provider, modelId: applied.modelId });
          setApplying(false);
          setOpen(false);
        })
        .catch((err: unknown) => {
          setCurrent(previous);
          setApplying(false);
          const message = err instanceof Error && err.message ? err.message : '';
          setActionError(
            message || t('chat.model_switch_error', { defaultValue: '模型切换失败，请重试' }),
          );
        });
    },
    [sessionId, applying, current, t],
  );

  const currentLabel = current ? `${current.provider}:${current.modelId}` : t('chat.model_picker', { defaultValue: '模型' });

  return (
    <div ref={rootRef} className={cn('relative min-w-0', className)}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled || !sessionId || applying}
        title={t('chat.model_picker_hint', { defaultValue: '切换本会话使用的模型' })}
        onClick={toggleOpen}
        className={cn(
          'flex min-w-0 items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-2 text-start text-[var(--color-text-secondary)] transition-colors duration-150 hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none',
          compact ? 'h-11 text-sm' : 'h-7 text-[length:var(--text-2xs)]',
        )}
      >
        <Cpu size={compact ? 16 : 12} aria-hidden="true" className="shrink-0 text-[var(--color-text-disabled)]" />
        <span className="min-w-0 truncate font-mono">{currentLabel}</span>
        <ChevronDown
          size={compact ? 16 : 12}
          aria-hidden="true"
          className={cn('shrink-0 text-[var(--color-text-disabled)] transition-transform duration-150 motion-reduce:transition-none', open && 'rotate-180')}
        />
      </button>
      {open ? (
        <div
          role="listbox"
          aria-label={t('chat.model_picker', { defaultValue: '模型' })}
          className="absolute bottom-full left-0 z-30 mb-2 max-h-72 w-64 overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] shadow-lg"
        >
          {grouped.length === 0 ? (
            <p className="px-3 py-2 text-xs text-[var(--color-text-muted)]">
              {models === null
                ? t('chat.model_catalog_loading', { defaultValue: '模型目录加载中…' })
                : t('chat.model_catalog_empty', { defaultValue: '暂无可用模型' })}
            </p>
          ) : (
            grouped.map((group) => (
              <div key={group.provider}>
                <p className="px-3 pt-2 pb-1 text-[length:var(--text-2xs)] uppercase tracking-wide text-[var(--color-text-muted)]">
                  {group.provider}
                </p>
                <ul className="pb-1">
                  {group.entries.map((entry) => {
                    const selected = current?.provider === entry.provider && current?.modelId === entry.model_id;
                    return (
                      <li key={`${entry.provider}:${entry.model_id}`}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={selected}
                          onClick={() => applyModel(entry)}
                          className="flex w-full items-center gap-2 px-3 py-1.5 text-start transition-colors duration-100 hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none motion-reduce:transition-none"
                        >
                          <span className="min-w-0 flex-1 truncate font-mono text-xs text-[var(--color-text-primary)]">
                            {entry.label || entry.model_id}
                          </span>
                          {selected ? (
                            <Check size={12} aria-hidden="true" className="shrink-0 text-[var(--color-accent)]" />
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
          {actionError ? (
            <p
              role="alert"
              className="border-t border-[var(--color-border-subtle)] px-3 py-2 text-[length:var(--text-2xs)] text-[var(--color-error)]"
            >
              {actionError}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default ModelPickerButton;
