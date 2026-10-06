import { useState } from 'react';
import { Globe, Loader2 } from 'lucide-react';
import { api } from '../../api';
import { useI18n } from '../../i18n';

interface ResearchFinding {
  source: string;
  title: string;
  key_points: string[];
  rel_score: number;
}

interface ResearchResult {
  ok: boolean;
  query: string;
  summary: string;
  findings: ResearchFinding[];
  sources: string[];
  generated_at: string;
}

/**
 * Zero-key web research form (POST /research). Result replaces the previous
 * run entirely — a failed run never leaves a stale report on screen.
 */
export function ResearchPanel() {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [sources, setSources] = useState(3);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.runResearch({ query: query.trim(), sources }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('research.error', { defaultValue: '研究请求失败' }));
    } finally {
      setRunning(false);
    }
  };

  return (
    <section aria-label={t('research.heading', { defaultValue: '在线研究' })} className="border-t border-[var(--color-border-subtle)] p-4">
      <h2 className="mb-3 flex items-center gap-2 text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">
        <Globe size={16} aria-hidden="true" className="text-[var(--color-text-muted)]" />
        {t('research.heading', { defaultValue: '在线研究' })}
      </h2>
      <form className="flex flex-wrap items-center gap-2" onSubmit={(event) => void submit(event)}>
        <input
          aria-label={t('research.query_label', { defaultValue: '研究问题' })}
          placeholder={t('research.query_placeholder', { defaultValue: '输入要研究的问题…' })}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-sm"
        />
        <select
          aria-label={t('research.sources_label', { defaultValue: '来源数量' })}
          value={sources}
          onChange={(event) => setSources(Number(event.target.value))}
          className="h-9 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-2 text-xs text-[var(--color-text-primary)]"
        >
          {[1, 2, 3, 5, 8].map((count) => (
            <option key={count} value={count}>{t('research.sources_count', { count, defaultValue: `${count} 个来源` })}</option>
          ))}
        </select>
        <button
          type="submit"
          disabled={running || !query.trim()}
          className="flex h-9 items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--color-accent)] px-3 text-xs font-medium text-[var(--color-accent-text)] disabled:opacity-50"
        >
          {running && <Loader2 size={12} className="animate-spin" aria-hidden="true" />}
          {running ? t('common.loading') : t('research.run', { defaultValue: '开始研究' })}
        </button>
      </form>
      {error && <p role="alert" className="mt-3 text-sm text-[var(--color-error)]">{error}</p>}
      {result && (
        <div className="mt-4 space-y-3">
          <p className="whitespace-pre-wrap break-words text-sm text-[var(--color-text-secondary)]">{result.summary}</p>
          {result.findings.length > 0 && (
            <ul className="space-y-2">
              {result.findings.map((finding, index) => (
                <li key={`${finding.source}-${index}`} className="rounded-lg border border-[var(--color-border-subtle)] p-3">
                  <p className="text-sm font-medium">{finding.title || finding.source}</p>
                  <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{finding.source}</p>
                  {finding.key_points.length > 0 && (
                    <ul className="mt-1 list-disc space-y-0.5 ps-4 text-xs text-[var(--color-text-secondary)]">
                      {finding.key_points.map((point, pointIndex) => <li key={pointIndex}>{point}</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
          {result.sources.length > 0 && (
            <p className="break-words text-xs text-[var(--color-text-muted)]">
              {t('research.sources_used', { defaultValue: '来源：' })}{result.sources.join(' · ')}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
