import { Activity, GitBranch } from 'lucide-react';
import { api } from '../../../../api';
import { useI18n } from '../../../../i18n';
import {
  PanelEmpty, PanelError, PanelLoading, resolveReportedCount, useAsyncData, useReportedCount, type ReportCount,
} from '../PanelState';
import { cn } from '../../../../lib/utils';
import { ringTone, textTone, toneForNodeStatus } from '../statusTone';

interface PlanNode {
  id: string;
  label: string;
  status: string;
}

interface TraceEntry {
  id: string;
  type: string;
  label: string;
  time: string;
  duration?: number;
  tokens?: number;
}

export function DagSection({ onCount }: { onCount?: ReportCount } = {}) {
  const { t } = useI18n();
  const { data, loading, error, reload } = useAsyncData<PlanNode[]>(async () => {
    const payload = await api.getClusterStatus();
    const nodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
    return nodes.map((item: Record<string, unknown>, index: number) => ({
      id: String(item.id ?? `node-${index}`),
      label: typeof item.name === 'string' ? item.name : '',
      status: typeof item.status === 'string' ? item.status : '',
    }));
  }, []);

  useReportedCount(resolveReportedCount({ data, loading, error }), onCount);

  if (loading) return <PanelLoading rows={3} />;
  if (error) return <PanelError onRetry={reload} />;
  if (!data || data.length === 0) {
    return (
      <PanelEmpty
        icon={GitBranch}
        title={t('right_panel.states.empty_dag')}
        hint={t('right_panel.states.empty_dag_hint')}
      />
    );
  }

  return (
    <ol>
      {data.map((node, index) => {
        const tone = toneForNodeStatus(node.status);
        return (
          <li key={node.id} className="flex items-start gap-2 py-[3px]">
            <span className="flex flex-col items-center self-stretch" aria-hidden="true">
              <span className={cn('mt-1 h-2 w-2 shrink-0 rounded-full border-2', ringTone(tone))} />
              {index < data.length - 1 && <span className="w-px flex-1 bg-[var(--color-border-subtle)]" />}
            </span>
            <span className={cn('min-w-0 flex-1 text-xs leading-4', textTone(tone))}>
              {node.label || t('right_panel.summary.none')}
            </span>
            <span className="sr-only">{node.status}</span>
          </li>
        );
      })}
    </ol>
  );
}

export function TraceSection({ onCount }: { onCount?: ReportCount } = {}) {
  const { t } = useI18n();
  const { data, loading, error, reload } = useAsyncData<TraceEntry[]>(async () => {
    const payload = await api.listTraces();
    const traces = Array.isArray(payload) ? payload : payload?.traces ?? [];
    return traces.map((item: Record<string, unknown>, index: number) => {
      const rawLabel = item.label ?? item.name;
      return {
        id: String(item.id ?? `trace-${index}`),
        type: typeof item.type === 'string' ? item.type : '',
        label: typeof rawLabel === 'string' && rawLabel.trim() ? rawLabel.trim() : '',
        time: typeof item.time === 'string' ? item.time : '',
        duration:
          typeof item.duration === 'number' && Number.isFinite(item.duration) && item.duration >= 0
            ? item.duration
            : undefined,
        tokens:
          typeof item.tokens === 'number' && Number.isFinite(item.tokens) && item.tokens > 0
            ? item.tokens
            : undefined,
      };
    });
  }, []);

  useReportedCount(resolveReportedCount({ data, loading, error }), onCount);

  if (loading) return <PanelLoading rows={2} />;
  if (error) return <PanelError onRetry={reload} />;
  if (!data || data.length === 0) {
    return (
      <PanelEmpty
        icon={Activity}
        title={t('right_panel.states.empty_trace')}
        hint={t('right_panel.states.empty_trace_hint')}
      />
    );
  }

  return (
    <ul>
      {data.map((trace) => {
        const hasMetrics = trace.duration !== undefined || trace.tokens !== undefined;
        return (
          <li
            key={trace.id}
            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2 py-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 flex-1 truncate text-xs text-[var(--color-text-secondary)]">
                {trace.label || t('right_panel.summary.none')}
              </span>
              {trace.type && (
                <span className="shrink-0 rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-3)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-muted)]">
                  {trace.type}
                </span>
              )}
              {trace.time && (
                <span className="shrink-0 text-[10px] tabular-nums text-[var(--color-text-muted)]">
                  {trace.time}
                </span>
              )}
            </div>
            {hasMetrics && (
              <div className="mt-0.5 flex gap-3 text-[10px] tabular-nums text-[var(--color-text-muted)]">
                {trace.duration !== undefined && (
                  <span>
                    {t('right_panel.trace.duration')} {trace.duration}ms
                  </span>
                )}
                {trace.tokens !== undefined && <span>{trace.tokens} {t('right_panel.trace.tokens')}</span>}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
