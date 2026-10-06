import { useState, useEffect } from 'react';
import { Clock, ChevronRight, ArrowLeft, RefreshCw } from 'lucide-react';
import { api } from '../api';
import { useI18n } from '../i18n';
import { formatDateTime } from '../i18n/utils';
import { formatDuration } from '../lib/duration';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { SkeletonList } from '../components/ui/Skeleton';
import { ReasoningTraceDetail } from '../components/workspace/ReasoningTraceDetail';

interface HistoryItem {
  trace_id: string | null;
  task: string;
  mode: string;
  candidates: number;
  best_confidence: number;
  coverage_score: number | null;
  duration_ms: number;
  created_at: string | null;
}

const PAGE_SIZE = 50;

export function ReasoningHistoryPage() {
  const { t } = useI18n();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selected, setSelected] = useState<HistoryItem | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const filteredHistory = history.filter(item => `${item.task} ${item.trace_id ?? ''} ${item.mode}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const formatTime = (value: string | null) => value && Number.isFinite(Date.parse(value)) ? formatDateTime(value) : '-';

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    setError(false);
    try {
      const page = await api.listReasoningHistory(PAGE_SIZE, 0);
      setHistory(page);
      setHasMore(page.length >= PAGE_SIZE);
    } catch { setError(true); } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    setError(false);
    try {
      const page = await api.listReasoningHistory(PAGE_SIZE, history.length);
      setHistory(previous => [...previous, ...page]);
      setHasMore(page.length >= PAGE_SIZE);
    } catch { setError(true); } finally {
      setLoadingMore(false);
    }
  };

  if (selected) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="p-4 max-w-5xl mx-auto">
          <Button
            variant="ghost"
            size="sm"
            icon={<ArrowLeft size={14} />}
            onClick={() => setSelected(null)}
            className="mb-4"
          >
            {t('common.back')}
          </Button>

          <Card variant="default">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    推理会话
                  </h3>
                  {selected.created_at && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                      {formatTime(selected.created_at)}
                    </p>
                  )}
                </div>
              </div>
              <p className="mb-3 break-all font-mono text-xs text-[var(--color-text-muted)]">ID: {selected.trace_id || '-'}</p>

              <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed mb-4 p-4 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)]">
                {selected.task}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">模式</p>
                  <Badge variant="default" size="sm">{selected.mode}</Badge>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">候选数</p>
                  <p className="text-sm font-semibold tabular-nums text-[var(--color-text-primary)]">{selected.candidates}</p>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">置信度</p>
                  <p className="text-sm font-semibold tabular-nums text-[var(--color-text-primary)]">{(selected.best_confidence * 100).toFixed(0)}%</p>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">耗时</p>
                  <p className="text-sm font-semibold tabular-nums text-[var(--color-text-primary)] flex items-center justify-center gap-1">
                    <Clock size={12} />
                    {formatDuration(selected.duration_ms, 'ms')}
                  </p>
                </div>
              </div>

              {selected.coverage_score !== null && (
                <div className="mt-3 p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">覆盖率</span>
                  <span className="text-sm font-semibold tabular-nums text-[var(--color-text-primary)]">
                    {(selected.coverage_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {selected.trace_id && <ReasoningTraceDetail traceId={selected.trace_id} />}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col text-[var(--color-text-primary)]">
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <h1 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{t('navigation.reasoning_history')} <span className="ml-2 font-normal tabular-nums text-[var(--color-text-muted)]">{filteredHistory.length} / {history.length}{hasMore ? '+' : ''}</span></h1>
        <Button variant="secondary" size="sm" icon={<RefreshCw size={14} />} onClick={loadHistory} disabled={loading}>{t('common.refresh')}</Button>
      </header>
      <div className="px-4 py-2 border-b border-[var(--color-border-subtle)]">
        <input aria-label={t('common.search')} placeholder={t('common.search')} value={query} onChange={event => setQuery(event.target.value)} className="w-full sm:max-w-sm rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-[length:var(--text-xs)] text-[var(--color-text-primary)]" />
      </div>
      {error && <div role="alert" className="flex items-center gap-3 px-4 py-2 text-xs text-[var(--color-error)]">{t('right_panel.states.load_failed')}<button type="button" onClick={loadHistory} className="underline">{t('common.retry')}</button></div>}
      <div className="flex-1 min-h-0 overflow-auto" aria-busy={loading}>
        {loading ? <SkeletonList count={3} /> : <>
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="sticky top-0 bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]"><tr>
              {[t('navigation.tasks'), t('common.type'), t('common.created'), t('right_panel.trace.duration'), '置信度', t('common.actions')].map(label => <th key={label} scope="col" className="px-4 py-2 font-medium whitespace-nowrap">{label}</th>)}
            </tr></thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {filteredHistory.map((item, index) => <tr key={item.trace_id || index} className="hover:bg-[var(--color-bg-surface-2)]">
                <td className="max-w-xs px-4 py-2.5"><p className="truncate" title={item.task}>{item.task}</p><p className="mt-1 truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]" title={item.trace_id || undefined}>{item.trace_id || '-'}</p></td>
                <td className="px-4 py-2.5">{item.mode}</td>
                <td className="px-4 py-2.5 whitespace-nowrap tabular-nums text-[var(--color-text-secondary)]">{formatTime(item.created_at)}</td>
                <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-secondary)]">{formatDuration(item.duration_ms, 'ms')}</td>
                <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-secondary)]">{(item.best_confidence * 100).toFixed(0)}%</td>
                <td className="px-4 py-2"><button type="button" onClick={() => setSelected(item)} aria-label={`${t('common.open')}: ${item.task}`} className="inline-flex items-center gap-1 rounded-[var(--radius-md)] px-2 py-1.5 transition-colors hover:bg-[var(--color-bg-surface-3)] motion-reduce:transition-none">{t('common.open')}<ChevronRight size={14} /></button></td>
              </tr>)}
            </tbody>
          </table>
          {!error && filteredHistory.length === 0 && <p className="p-8 text-center text-xs text-[var(--color-text-muted)]">{t(history.length ? 'common.no_results' : 'common.no_data')}</p>}
          {!error && hasMore && (
            <div className="p-3 text-center">
              <Button variant="secondary" size="sm" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? t('common.loading') : t('common.load_more')}
              </Button>
            </div>
          )}
        </>}
      </div>
    </div>
  );
}
