import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { api } from '../../api';
import { Button } from '../ui/Button';

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

type ModelBinding = { provider: string; modelId: string };

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
  const [current, setCurrent] = useState<ModelBinding | null>(null);
  const [reasoningLevel, setReasoningLevel] = useState<string | null>(null);
  const [models, setModels] = useState<ModelEntry[] | null>(null);
  const [applying, setApplying] = useState(false);
  const [actionError, setActionError] = useState('');
  const [catalogError, setCatalogError] = useState('');
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const catalogRequestRef = useRef(0);

  useEffect(() => {
    setCurrent(null);
    setReasoningLevel(null);
    setActionError('');
    setCatalogError('');
    setModels(null);
    setActiveIndex(0);
    catalogRequestRef.current += 1;
    if (!sessionId) return undefined;
    let cancelled = false;
    void Promise.allSettled([
      api.getSession(sessionId),
      api.getSessionThinkingLevel(sessionId),
    ]).then(([sessionResult, reasoningResult]) => {
      if (cancelled) return;
      if (sessionResult.status === 'fulfilled') {
        const provider = typeof sessionResult.value?.provider === 'string' ? sessionResult.value.provider : '';
        const modelId = typeof sessionResult.value?.model_id === 'string' ? sessionResult.value.model_id : '';
        if (provider && modelId) setCurrent({ provider, modelId });
      }
      if (reasoningResult.status === 'fulfilled' && typeof reasoningResult.value?.level === 'string') {
        setReasoningLevel(reasoningResult.value.level);
      }
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

  const options = useMemo(() => grouped.flatMap((group) => group.entries), [grouped]);

  const loadCatalog = useCallback(() => {
    if (catalogLoading) return;
    const requestId = ++catalogRequestRef.current;
    setCatalogLoading(true);
    setCatalogError('');
    api
      .listModels()
      .then((data) => {
        if (requestId !== catalogRequestRef.current) return;
        const nextModels = Array.isArray(data) ? data : [];
        setModels(nextModels);
        setActiveIndex(Math.max(0, nextModels.findIndex((entry) => current?.provider === entry.provider && current?.modelId === entry.model_id)));
      })
      .catch(() => {
        if (requestId !== catalogRequestRef.current) return;
        setModels([]);
        setCatalogError(t('chat.model_catalog_error', { defaultValue: '模型目录加载失败' }));
      })
      .finally(() => {
        if (requestId === catalogRequestRef.current) setCatalogLoading(false);
      });
  }, [catalogLoading, current, t]);

  const toggleOpen = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      if (next && models === null) loadCatalog();
      if (next) setActionError('');
      return next;
    });
  }, [loadCatalog, models]);

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

  useEffect(() => {
    if (!open || !options.length) return;
    optionRefs.current[activeIndex]?.focus();
  }, [activeIndex, open, options.length]);

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
  const currentDisplay = reasoningLevel ? `${currentLabel} · ${t(`chat.thinking_level_${reasoningLevel}`, { defaultValue: reasoningLevel })}` : currentLabel;

  return (
    <div ref={rootRef} className={cn('relative min-w-0', className)}>
      <button
        type="button"
         aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled || !sessionId || applying}
        aria-label={currentLabel}
        title={currentDisplay}
        onClick={toggleOpen}
        className={cn(
          'flex min-w-0 items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-2 text-start text-[var(--color-text-secondary)] transition-colors duration-150 hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none',
          compact ? 'h-11 text-sm' : 'h-7 text-[length:var(--text-2xs)]',
        )}
      >
        <Cpu size={compact ? 16 : 12} aria-hidden="true" className="shrink-0 text-[var(--color-text-disabled)]" />
         <span className="min-w-0 truncate font-mono">{currentDisplay}</span>
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
               {catalogLoading || models === null
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
                     const optionIndex = options.indexOf(entry);
                     const selected = current?.provider === entry.provider && current?.modelId === entry.model_id;
                    return (
                      <li key={`${entry.provider}:${entry.model_id}`}>
                         <button
                           ref={(node) => { optionRefs.current[optionIndex] = node; }}
                           type="button"
                          role="option"
                           aria-selected={selected}
                           tabIndex={optionIndex === activeIndex ? 0 : -1}
                           onKeyDown={(event) => {
                             if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                               event.preventDefault();
                               setActiveIndex((optionIndex + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length);
                             } else if (event.key === 'Home' || event.key === 'End') {
                               event.preventDefault();
                               setActiveIndex(event.key === 'Home' ? 0 : options.length - 1);
                             } else if (event.key === 'Enter' || event.key === ' ') {
                               event.preventDefault();
                               applyModel(entry);
                             }
                           }}
                           onFocus={() => setActiveIndex(optionIndex)}
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
           {catalogError ? (
             <Button
               type="button"
               variant="ghost"
               size="xs"
               className="mx-2 mb-2"
               onClick={loadCatalog}
             >
               {t('chat.model_catalog_retry', { defaultValue: '重试' })}
             </Button>
           ) : null}
           {catalogError ? (
             <p role="alert" className="border-t border-[var(--color-border-subtle)] px-3 py-2 text-[length:var(--text-2xs)] text-[var(--color-error)]">
               {catalogError}
             </p>
           ) : null}
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
