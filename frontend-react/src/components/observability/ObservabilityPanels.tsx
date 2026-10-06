import { useCallback, useEffect, useState } from 'react';
import { AlertOctagon, RefreshCw, ShieldCheck } from 'lucide-react';
import { api } from '../../api';
import { useI18n } from '../../i18n/utils';
import { Card, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { EmptyState } from '../ui/EmptyState';
import { SkeletonList } from '../ui/Skeleton';

/** GET /observability/audit — hash-chained decision entries. */
export function DecisionChainPanel() {
  const { t } = useI18n();
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await api.getObservabilityAudit({ limit: 50 });
      setEntries(Array.isArray(payload?.entries) ? payload.entries : []);
    } catch (e) {
      setEntries([]);
      setError(e instanceof Error ? e.message : t('audit.chain_load_failed', { defaultValue: '决策链加载失败' }));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Card variant="default" padding="none" className="overflow-hidden">
      <CardContent>
        <div className="flex items-center justify-between px-3 py-3">
          <h2 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">
            {t('audit.chain_title', { defaultValue: '决策链' })}
          </h2>
          <Button variant="ghost" size="xs" onClick={() => void load()} disabled={loading} icon={<RefreshCw size={12} />}>
            {t('common.refresh')}
          </Button>
        </div>
        {error && <p role="alert" className="px-3 pb-2 text-[length:var(--text-xs)] text-[var(--color-error)]">{error}</p>}
        {loading ? (
          <div role="status" className="px-3 pb-3"><SkeletonList count={3} /></div>
        ) : entries.length === 0 && !error ? (
          <EmptyState className="w-full" icon="file" title={t('audit.chain_empty', { defaultValue: '暂无决策记录' })} />
        ) : (
          <ul className="divide-y divide-[var(--color-border-subtle)]">
            {entries.map((entry, index) => (
              <li key={typeof entry.id === 'string' || typeof entry.id === 'number' ? String(entry.id) : index} className="px-3 py-2.5">
                <p className="font-mono text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                  {typeof entry.decision_type === 'string' ? entry.decision_type : typeof entry.type === 'string' ? entry.type : '—'}
                </p>
                <p className="mt-1 whitespace-pre-wrap break-words text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                  {JSON.stringify(entry)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/** GET /observability/alignment — goal tracker + drift score. */
export function AlignmentPanel() {
  const { t } = useI18n();
  const [data, setData] = useState<{ goals: Array<Record<string, unknown>>; drift_score: number; threshold: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.getAlignmentStatus());
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : t('audit.alignment_load_failed', { defaultValue: '对齐状态加载失败' }));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const drift = data?.drift_score;
  const threshold = data?.threshold;
  const drifting = typeof drift === 'number' && typeof threshold === 'number' && drift > threshold;

  return (
    <Card variant="default" padding="none" className="overflow-hidden">
      <CardContent>
        <div className="flex items-center justify-between px-3 py-3">
          <h2 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">
            {t('audit.alignment_title', { defaultValue: '目标对齐' })}
          </h2>
          <Button variant="ghost" size="xs" onClick={() => void load()} disabled={loading} icon={<RefreshCw size={12} />}>
            {t('common.refresh')}
          </Button>
        </div>
        {error && <p role="alert" className="px-3 pb-2 text-[length:var(--text-xs)] text-[var(--color-error)]">{error}</p>}
        {loading ? (
          <div role="status" className="px-3 pb-3"><SkeletonList count={2} /></div>
        ) : data && (
          <div className="space-y-3 px-3 pb-3">
            <p className={`text-[length:var(--text-xs)] ${drifting ? 'text-[var(--color-error)]' : 'text-[var(--color-text-secondary)]'}`}>
              {t('audit.alignment_drift', { defaultValue: '漂移分数' })}: <span className="font-mono tabular-nums">{drift?.toFixed(3) ?? '—'}</span>
              {typeof threshold === 'number' && <> / {t('audit.alignment_threshold', { defaultValue: '阈值' })} <span className="font-mono tabular-nums">{threshold.toFixed(3)}</span></>}
              {drifting && <> — {t('audit.alignment_drifting', { defaultValue: '已超阈值' })}</>}
            </p>
            {data.goals.length === 0 ? (
              <p className="text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{t('audit.alignment_no_goals', { defaultValue: '暂无目标' })}</p>
            ) : (
              <ul className="space-y-2">
                {data.goals.map((goal, index) => (
                  <li key={typeof goal.id === 'string' ? goal.id : index} className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-3 py-2">
                    <p className="text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                      {typeof goal.description === 'string' ? goal.description : typeof goal.title === 'string' ? goal.title : '—'}
                    </p>
                    <p className="mt-0.5 font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                      {typeof goal.status === 'string' ? goal.status : ''}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** GET/POST/DELETE /observability/emergency-stop — kill switch, 二次确认。 */
export function EmergencyStopPanel() {
  const { t } = useI18n();
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await api.getEmergencyStopStatus());
    } catch (e) {
      setStatus(null);
      setError(e instanceof Error ? e.message : t('audit.estop_load_failed', { defaultValue: '紧急停止状态加载失败' }));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const activated = status?.activated === true || status?.is_activated === true || status?.status === 'activated';

  const toggle = async () => {
    if (busy) return;
    const confirmation = activated
      ? t('audit.estop_deactivate_confirm', { defaultValue: '确认解除紧急停止？' })
      : t('audit.estop_activate_confirm', { defaultValue: '确认触发紧急停止？所有运行中的任务将被中断。' });
    if (!window.confirm(confirmation)) return;
    setBusy(true);
    setError(null);
    try {
      if (activated) {
        await api.deactivateEmergencyStop({ reason: reason.trim() || undefined });
      } else {
        await api.activateEmergencyStop({ reason: reason.trim() || 'manual activation' });
      }
      setReason('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('audit.estop_failed', { defaultValue: '紧急停止操作失败' }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="default" padding="none" className={`overflow-hidden ${activated ? 'border-[var(--color-error)]/40' : ''}`}>
      <CardContent>
        <div className="flex items-center justify-between px-3 py-3">
          <h2 className="flex items-center gap-2 text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">
            {activated
              ? <AlertOctagon size={16} aria-hidden="true" className="text-[var(--color-error)]" />
              : <ShieldCheck size={16} aria-hidden="true" className="text-[var(--color-text-muted)]" />}
            {t('audit.estop_title', { defaultValue: '紧急停止' })}
          </h2>
          <Button variant="ghost" size="xs" onClick={() => void load()} disabled={loading} icon={<RefreshCw size={12} />}>
            {t('common.refresh')}
          </Button>
        </div>
        {error && <p role="alert" className="px-3 pb-2 text-[length:var(--text-xs)] text-[var(--color-error)]">{error}</p>}
        {loading ? (
          <div role="status" className="px-3 pb-3"><SkeletonList count={1} /></div>
        ) : (
          <div className="space-y-3 px-3 pb-3">
            <p role="status" className={`text-[length:var(--text-xs)] ${activated ? 'text-[var(--color-error)]' : 'text-[var(--color-text-secondary)]'}`}>
              {activated
                ? t('audit.estop_active', { defaultValue: '状态：已触发，系统处于紧急停止中' })
                : t('audit.estop_inactive', { defaultValue: '状态：未触发' })}
            </p>
            <div className="max-w-sm">
              <Input
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder={t('audit.estop_reason', { defaultValue: '原因（可选）' })}
                aria-label={t('audit.estop_reason', { defaultValue: '原因（可选）' })}
              />
            </div>
            <Button
              variant={activated ? 'outline' : 'destructive'}
              size="sm"
              disabled={busy}
              loading={busy}
              onClick={() => void toggle()}
            >
              {activated
                ? t('audit.estop_deactivate', { defaultValue: '解除紧急停止' })
                : t('audit.estop_activate', { defaultValue: '触发紧急停止' })}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
