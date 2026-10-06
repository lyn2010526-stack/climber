import { useCallback, useEffect, useState } from 'react';
import { ScrollText, AlertTriangle, RefreshCw, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { useI18n } from '../i18n/utils';
import { AlignmentPanel, DecisionChainPanel, EmergencyStopPanel } from '../components/observability/ObservabilityPanels';

interface AuditEntry {
  id: number | string;
  session_id: string | null;
  user_id: string | null;
  action: string;
  severity: string;
  details: Record<string, unknown> | null;
  result: string | null;
  created_at: string | null;
}

const PAGE_SIZE = 20;

const SEVERITY_FILTERS = ['all', 'info', 'warning', 'critical'] as const;
type SeverityFilter = (typeof SEVERITY_FILTERS)[number];

type AuditTab = 'events' | 'chain' | 'alignment' | 'estop';

/**
 * 审计日志页：dense 表格 + action/severity 过滤 + 分页。
 * 严重度仅三档（info/warning/critical），与后端 audit.py 写入的取值一致。
 */
export function AuditLogPage() {
  const { t } = useI18n();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState('');
  const [actionInput, setActionInput] = useState('');
  const [severity, setSeverity] = useState<SeverityFilter>('all');
  const [reloadKey, setReloadKey] = useState(0);
  const [tab, setTab] = useState<AuditTab>('events');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await api.listAuditLog({
        limit: PAGE_SIZE,
        offset,
        action: action || undefined,
        severity: severity === 'all' ? undefined : severity,
      });
      setEntries(Array.isArray(payload?.entries) ? payload.entries : []);
      setTotal(typeof payload?.total === 'number' ? payload.total : 0);
    } catch {
      setError(t('audit.load_failed', { defaultValue: '审计日志加载失败' }));
      setEntries([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [offset, action, severity, t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData, reloadKey]);

  const hasPrev = offset > 0;
  const hasNext = offset + entries.length < total;

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        <PageHeader
          title={t('audit.title', { defaultValue: '审计日志' })}
          icon={<ScrollText size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((key) => key + 1)} loading={loading} icon={<RefreshCw size={14} />}>
              {t('common.refresh')}
            </Button>
          }
        />

        <div role="tablist" aria-label={t('audit.tabs_label', { defaultValue: '审计视图' })} className="mb-4 flex flex-wrap gap-1 border-b border-[var(--color-border-subtle)]">
          {([
            ['events', t('audit.tab_events', { defaultValue: '事件日志' })],
            ['chain', t('audit.tab_chain', { defaultValue: '决策链' })],
            ['alignment', t('audit.tab_alignment', { defaultValue: '目标对齐' })],
            ['estop', t('audit.tab_estop', { defaultValue: '紧急停止' })],
          ] as Array<[AuditTab, string]>).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`rounded-t-[var(--radius-md)] px-3 py-2 text-[length:var(--text-xs)] transition-colors duration-150 motion-reduce:transition-none ${
                tab === id
                  ? 'bg-[var(--color-bg-surface-2)] font-medium text-[var(--color-text-primary)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'chain' && <DecisionChainPanel />}
        {tab === 'alignment' && <AlignmentPanel />}
        {tab === 'estop' && <EmergencyStopPanel />}

        {tab === 'events' && (
        <Card variant="default" padding="none" className="overflow-hidden">
          <CardContent>
            <form
              className="flex flex-wrap items-center gap-[var(--space-2)] px-3 py-3"
              onSubmit={(event) => {
                event.preventDefault();
                setOffset(0);
                setAction(actionInput.trim());
              }}
            >
              <div className="min-w-[220px] flex-1">
                <Input
                  value={actionInput}
                  onChange={(event) => setActionInput(event.target.value)}
                  leftIcon={<Search size={14} aria-hidden="true" />}
                  placeholder={t('audit.filter_action', { defaultValue: '按动作过滤，如 agent:run' })}
                  aria-label={t('audit.filter_action', { defaultValue: '按动作过滤，如 agent:run' })}
                  className="font-mono text-[length:var(--text-xs)]"
                />
              </div>
              <select
                value={severity}
                aria-label={t('audit.filter_severity', { defaultValue: '按严重度过滤' })}
                onChange={(event) => {
                  setSeverity(event.target.value as SeverityFilter);
                  setOffset(0);
                }}
                className="h-9 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
              >
                {SEVERITY_FILTERS.map((value) => (
                  <option key={value} value={value}>
                    {value === 'all' ? t('audit.severity_all', { defaultValue: '全部严重度' }) : value}
                  </option>
                ))}
              </select>
              <Button type="submit" variant="outline" size="sm">
                {t('audit.apply', { defaultValue: '应用' })}
              </Button>
            </form>

            {error && (
              <div className="mx-3 mb-3 flex items-center gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-[var(--space-2-5)] py-[var(--space-2)]">
                <AlertTriangle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
                <p className="flex-1 text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">{error}</p>
                <Button variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
                  {t('common.retry')}
                </Button>
              </div>
            )}

            {loading ? (
              <div role="status" aria-label={t('common.loading_data')} className="px-3 pb-3">
                <SkeletonList count={4} />
              </div>
            ) : entries.length === 0 ? (
              <EmptyState
                className="w-full"
                icon="file"
                title={error ? t('audit.no_results', { defaultValue: '无匹配条目' }) : t('audit.empty', { defaultValue: '暂无审计事件' })}
              />
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm text-[var(--color-text-primary)]">
                    <thead className="bg-[var(--color-bg-surface-2)] text-xs text-[var(--color-text-muted)]">
                      <tr>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_time', { defaultValue: '时间' })}</th>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_action', { defaultValue: '动作' })}</th>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_severity', { defaultValue: '严重度' })}</th>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_session', { defaultValue: '会话' })}</th>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_user', { defaultValue: '用户' })}</th>
                        <th scope="col" className="px-3 py-2 font-medium">{t('audit.col_result', { defaultValue: '结果' })}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border-subtle)]">
                      {entries.map((entry) => (
                        <tr key={String(entry.id)} className="transition-colors duration-150 motion-reduce:transition-none hover:bg-[var(--color-bg-surface-2)]">
                          <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-muted)]">
                            {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                          </td>
                          <td className="max-w-[220px] px-3 py-2.5">
                            <span className="block truncate font-mono text-[length:var(--text-xs)] text-[var(--color-text-primary)]" title={entry.action}>
                              {entry.action}
                            </span>
                          </td>
                          <td className="px-3 py-2.5">
                            <AuditSeverityBadge severity={entry.severity} />
                          </td>
                          <td className="max-w-[160px] px-3 py-2.5">
                            <span className="block truncate font-mono text-[length:var(--text-xs)] text-[var(--color-text-secondary)]" title={entry.session_id ?? undefined}>
                              {entry.session_id ?? '—'}
                            </span>
                          </td>
                          <td className="max-w-[120px] px-3 py-2.5">
                            <span className="block truncate font-mono text-[length:var(--text-xs)] text-[var(--color-text-secondary)]" title={entry.user_id ?? undefined}>
                              {entry.user_id ?? '—'}
                            </span>
                          </td>
                          <td className="max-w-[200px] px-3 py-2.5">
                            <span className="block truncate text-[length:var(--text-xs)] text-[var(--color-text-muted)]" title={entry.result ?? undefined}>
                              {entry.result ?? '—'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center justify-between border-t border-[var(--color-border-subtle)] px-3 py-2.5">
                  <p aria-live="polite" className="font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-text-muted)]">
                    {offset + 1}-{offset + entries.length} / {total}
                  </p>
                  <div className="flex items-center gap-[var(--space-1-5)]">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!hasPrev}
                      aria-label={t('audit.prev_page', { defaultValue: '上一页' })}
                      onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                      icon={<ChevronLeft size={14} />}
                    >
                      {t('audit.prev_page', { defaultValue: '上一页' })}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!hasNext}
                      aria-label={t('audit.next_page', { defaultValue: '下一页' })}
                      onClick={() => setOffset(offset + PAGE_SIZE)}
                    >
                      {t('audit.next_page', { defaultValue: '下一页' })}
                      <ChevronRight size={14} aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
        )}
      </div>
    </div>
  );
}

function AuditSeverityBadge({ severity }: { severity: string }) {
  const { t } = useI18n();
  const label = t(`audit.severity.${severity}`, { defaultValue: severity });
  if (severity === 'critical') {
    return <Badge variant="destructive" size="xs">{label}</Badge>;
  }
  if (severity === 'warning') {
    return <Badge variant="warning" size="xs">{label}</Badge>;
  }
  if (severity === 'info') {
    return <Badge variant="info" size="xs">{label}</Badge>;
  }
  return <Badge variant="secondary" size="xs">{label}</Badge>;
}

export default AuditLogPage;
