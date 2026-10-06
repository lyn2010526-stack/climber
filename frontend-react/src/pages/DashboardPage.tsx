import { useCallback, useEffect, useState, type ReactNode } from 'react';
import {
  AlertCircle, Bot, CheckCircle2, Clock, Cpu, DollarSign, MessageSquare,
  RefreshCw, Server, Workflow,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { HeroSection } from '../components/hero/HeroSection';
import { CostQuotaIndicator } from '../components/cost/CostQuotaIndicator';
import { api, type TaskSummary } from '../api';
import { useI18n } from '../i18n/utils';
import { formatNumber } from '../i18n/utils';
import { taskStatusColor, taskStatusLabel } from '../components/collaboration/taskStatus';

const RECENT_TASK_LIMIT = 5;
const NOT_REPORTED = '—';

type HealthState = 'loading' | 'online' | 'offline';
type DashboardSection = 'sessions' | 'agents' | 'cost' | 'cluster' | 'tasks';

interface DashboardSession {
  id: string;
  title?: string | null;
  status?: string | null;
}

interface DashboardAgent {
  id: string;
  name?: string | null;
}

interface CostRecordItem {
  id: string;
  total_cost?: number;
  created_at?: string | null;
}

interface ClusterNode {
  id: string;
  name?: string;
  status?: string;
  role?: string;
}

interface ClusterPayload {
  status?: string;
  total_nodes?: number;
  online_nodes?: number;
  nodes?: ClusterNode[];
}

interface MetricRow {
  section: DashboardSection;
  label: string;
  icon: ReactNode;
  value: string;
  hint?: string;
  detail?: ReactNode;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function settled<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === 'fulfilled' ? result.value : null;
}

function sumTodayCost(records: CostRecordItem[]): number {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const startTime = start.getTime();
  return records.reduce((sum, record) => {
    const createdAt = record.created_at;
    if (typeof createdAt !== 'string') return sum;
    const time = Date.parse(createdAt);
    if (!Number.isFinite(time) || time < startTime) return sum;
    const amount = record.total_cost;
    return typeof amount === 'number' && Number.isFinite(amount) ? sum + amount : sum;
  }, 0);
}

function RecentTaskRow({ task }: { task: TaskSummary }) {
  const { t } = useI18n();
  const hasProgress = typeof task.progress === 'number' && typeof task.total_steps === 'number';
  return (
    <li className="flex items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-[var(--color-text-primary)]">{task.objective}</p>
        {hasProgress && (
          <p className="mt-0.5 text-xs tabular-nums text-[var(--color-text-muted)]">
            {t('dashboard.task_progress', { progress: formatNumber(task.progress), total: formatNumber(task.total_steps) })}
          </p>
        )}
      </div>
      <span className={`shrink-0 text-xs font-medium ${taskStatusColor(task.status)}`}>
        {taskStatusLabel(task.status, t)}
      </span>
    </li>
  );
}

export function DashboardPage() {
  const { t } = useI18n();
  const [sessions, setSessions] = useState<DashboardSession[]>([]);
  const [agents, setAgents] = useState<DashboardAgent[]>([]);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [todayCost, setTodayCost] = useState<number | null>(null);
  const [cluster, setCluster] = useState<ClusterPayload | null>(null);
  const [health, setHealth] = useState<HealthState>('loading');
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<Partial<Record<DashboardSection, boolean>>>({});

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setErrors({});
    try {
      const results = await Promise.allSettled([
        api.listSessions(),
        api.listAgents(),
        api.listTasks({ limit: RECENT_TASK_LIMIT }),
        api.listCostRecords(),
        api.getClusterStatus(),
        api.checkHealth(),
      ]);
      const sessionsResult = results[0]!;
      const agentsResult = results[1]!;
      const tasksResult = results[2]!;
      const costResult = results[3]!;
      const clusterResult = results[4]!;
      const healthResult = results[5]!;

      setSessions(asArray(settled(sessionsResult)) as DashboardSession[]);
      setAgents(asArray(settled(agentsResult)) as DashboardAgent[]);
      setTasks(asArray(settled(tasksResult)) as TaskSummary[]);
      setTodayCost(costResult.status === 'fulfilled' ? sumTodayCost(asArray(costResult.value) as CostRecordItem[]) : null);

      const clusterValue = settled(clusterResult);
      setCluster(clusterValue && typeof clusterValue === 'object' ? clusterValue as ClusterPayload : null);
      setHealth(healthResult.status === 'fulfilled' && healthResult.value === true ? 'online' : 'offline');

      const failed: DashboardSection[] = [];
      if (sessionsResult.status === 'rejected') failed.push('sessions');
      if (agentsResult.status === 'rejected') failed.push('agents');
      if (costResult.status === 'rejected') failed.push('cost');
      if (clusterResult.status === 'rejected') failed.push('cluster');
      if (tasksResult.status === 'rejected') failed.push('tasks');
      setErrors(Object.fromEntries(failed.map((key) => [key, true])));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  const handleCreateAgent = useCallback(() => {
    window.location.hash = 'agents';
  }, []);

  const handleStartTask = useCallback(() => {
    window.location.hash = 'tasks';
  }, []);

  const clusterNodesOnline = typeof cluster?.online_nodes === 'number'
    ? cluster.online_nodes
    : (cluster?.nodes?.filter((node) => node.status === 'online').length ?? 0);
  const clusterNodesTotal = typeof cluster?.total_nodes === 'number'
    ? cluster.total_nodes
    : (cluster?.nodes?.length ?? 0);
  const hasClusterNodes = clusterNodesTotal > 0;

  const metrics: MetricRow[] = [
    {
      section: 'sessions',
      label: t('dashboard.stat.total_sessions'),
      icon: <MessageSquare size={14} />,
      value: loading ? '…' : errors.sessions ? NOT_REPORTED : formatNumber(sessions.length),
    },
    {
      section: 'agents',
      label: t('dashboard.stat.active_agents'),
      icon: <Bot size={14} />,
      value: loading ? '…' : errors.agents ? NOT_REPORTED : formatNumber(agents.length),
    },
    {
      section: 'cost',
      label: t('dashboard.stat.cost_today'),
      icon: <DollarSign size={14} />,
      value: loading
        ? '…'
        : errors.cost || todayCost === null
          ? NOT_REPORTED
          : t('dashboard.cost_amount', { amount: todayCost.toFixed(4) }),
      detail: <CostQuotaIndicator />,
    },
    {
      section: 'cluster',
      label: t('dashboard.stat.cluster_nodes'),
      icon: <Server size={14} />,
      value: loading ? '…' : errors.cluster || !hasClusterNodes ? NOT_REPORTED : t('dashboard.nodes_online', { online: formatNumber(clusterNodesOnline), total: formatNumber(clusterNodesTotal) }),
      hint: !loading && !errors.cluster && cluster !== null && !hasClusterNodes ? t('dashboard.cluster_empty') : undefined,
    },
  ];

  const failedSections = (Object.keys(errors) as DashboardSection[]).filter((key) => errors[key]);

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <HeroSection />

        <div className="space-y-4">
          <Card padding="none" role="status" aria-live="polite" className="flex flex-wrap items-center gap-3 px-3 py-2">
            {health === 'loading' && <RefreshCw size={18} className="animate-spin text-[var(--color-text-muted)]" />}
            {health === 'online' && <CheckCircle2 size={18} className="text-[var(--color-success)]" />}
            {health === 'offline' && <AlertCircle size={18} className="text-[var(--color-error)]" />}
            <div>
              <p className="text-sm text-[var(--color-text-primary)]">{health === 'loading' ? t('common.loading') : health === 'online' ? t('home.api_online') : t('home.api_offline')}</p>
            </div>
            <code className="text-xs text-[var(--color-text-muted)]">GET /health</code>
            <Button variant="ghost" size="sm" onClick={loadDashboard} disabled={loading} className="ml-auto" icon={<RefreshCw size={14} />}>{t('common.refresh')}</Button>
          </Card>

          <div className="flex flex-wrap gap-2" aria-label={t('home.quick_actions')}>
            <Button variant="secondary" size="sm" onClick={handleCreateAgent} icon={<Bot size={14} />}>{t('home.create_agent')}</Button>
            <Button variant="secondary" size="sm" onClick={handleStartTask} icon={<Cpu size={14} />}>{t('home.start_task')}</Button>
            <Button variant="secondary" size="sm" onClick={() => { window.location.hash = 'workflows'; }} icon={<Workflow size={14} />}>{t('nav.workflows', { defaultValue: '工作流' })}</Button>
          </div>

          {failedSections.length > 0 && (
            <Card variant="default" className="border-[var(--color-error)]/30">
              <CardContent className="flex items-center gap-3 p-4">
                <AlertCircle size={18} className="shrink-0 text-[var(--color-error)]" />
                <p className="flex-1 text-sm text-[var(--color-error)]">
                  {t('dashboard.load_error', { parts: failedSections.map((key) => t(`dashboard.section.${key}`)).join(t('dashboard.parts_separator')) })}
                </p>
                <Button variant="outline" size="sm" onClick={loadDashboard} loading={loading}>{t('common.retry')}</Button>
              </CardContent>
            </Card>
          )}

          <dl aria-busy={loading} aria-label={t('dashboard.stats_aria')} className="grid grid-cols-1 gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-border-subtle)] sm:grid-cols-2 lg:grid-cols-4">
            {metrics.map((metric) => (
              <div key={metric.section} className="bg-[var(--color-bg-surface-1)] p-4">
                <dt className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">{metric.icon}{metric.label}</dt>
                <dd className="mt-2 text-2xl font-semibold tabular-nums text-[var(--color-text-primary)]">{metric.value}</dd>
                {metric.detail && <div className="mt-1">{metric.detail}</div>}
                {metric.hint && <p className="mt-1 text-xs text-[var(--color-text-muted)]">{metric.hint}</p>}
              </div>
            ))}
          </dl>

          <Card variant="default" padding="none" className="overflow-hidden">
            <div className="flex items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] px-4 py-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
                <Clock size={14} className="text-[var(--color-text-muted)]" />
                {t('dashboard.recent_tasks')}
              </h2>
              <Button variant="ghost" size="sm" onClick={() => { window.location.hash = 'tasks'; }}>{t('dashboard.view_all')}</Button>
            </div>
            {loading ? (
              <div role="status" className="p-4"><SkeletonList count={3} /></div>
            ) : errors.tasks ? (
              <EmptyState
                className="min-h-0 py-8"
                icon="alert"
                title={t('dashboard.load_error', { parts: t('dashboard.section.tasks') })}
                action={<Button variant="outline" size="sm" onClick={loadDashboard}>{t('common.retry')}</Button>}
              />
            ) : tasks.length === 0 ? (
              <EmptyState className="min-h-0 py-8" icon="inbox" title={t('dashboard.tasks_empty')} />
            ) : (
              <ul className="divide-y divide-[var(--color-border-subtle)]" aria-label={t('dashboard.recent_tasks_aria')}>
                {tasks.map((task) => <RecentTaskRow key={task.task_id} task={task} />)}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
