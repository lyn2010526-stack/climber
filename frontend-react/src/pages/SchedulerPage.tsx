import { useState, useEffect, useCallback } from 'react';
import {
  Clock, Plus, Trash2, ToggleLeft, ToggleRight,
  Shield, Search, RefreshCw, AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import { useI18n, formatDateTime } from '../i18n/utils';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

interface ScheduledTask {
  id: string;
  name: string;
  description: string;
  cron: string;
  type?: string;
  enabled: boolean;
  last_run: number | null;
  next_run: number | null;
  /** Absent when the API omits it; rendering `0` would claim it never ran. */
  run_count?: number | null;
}

const TYPE_ICONS: Record<string, typeof Shield> = {
  inspect: Search,
  audit: Shield,
  backup: RefreshCw,
  custom: Clock,
};

/** Options the API accepts for `task_type`; each one is named in the locale. */
const TASK_TYPE_KEYS = ['custom', 'inspect', 'audit', 'backup'] as const;

export function SchedulerPage() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [newTask, setNewTask] = useState({ name: '', description: '', cron: '*/5 * * * *', type: 'custom' });

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSchedulerTasks();
      setTasks(data.map((task) => ({
        ...task,
        enabled: Boolean(task.enabled),
        last_run: task.last_run ?? null,
        next_run: task.next_run ?? null,
        // Keep a non-numeric or absent counter unreported rather than
        // collapsing it to 0: "0 runs" and "unknown count" are different facts.
        run_count: typeof task.run_count === 'number' && Number.isFinite(task.run_count) ? task.run_count : null,
      })));
    } catch (cause) {
      setError(t('scheduler.errors.load', { detail: cause instanceof Error ? cause.message : t('common.not_reported') }));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const toggleTask = async (task: ScheduledTask) => {
    setPending(true);
    setActionError(null);
    try {
      const updated = await api.updateSchedulerTask(task.id, { enabled: !task.enabled });
      setTasks(current => current.map(item => item.id === task.id ? { ...item, ...updated } : item));
    } catch {
      setActionError(t('scheduler.errors.update'));
    } finally { setPending(false); }
  };

  const deleteTask = async (id: string) => {
    setPending(true);
    setActionError(null);
    try {
      await api.deleteSchedulerTask(id);
      setTasks(current => current.filter(task => task.id !== id));
    } catch {
      setActionError(t('scheduler.errors.delete'));
    } finally { setPending(false); }
  };

  const addTask = async () => {
    if (!newTask.name.trim() || !newTask.cron.trim() || pending) return;
    setPending(true);
    setActionError(null);
    try {
      await api.createSchedulerTask({
        name: newTask.name,
        description: newTask.description,
        cron: newTask.cron,
        task_type: newTask.type,
      });
      setShowAdd(false);
      setNewTask({ name: '', description: '', cron: '*/5 * * * *', type: 'custom' });
      fetchTasks();
    } catch {
      setActionError(t('scheduler.errors.create'));
    } finally { setPending(false); }
  };

  /** An absent stamp stays unreported: "0" would claim the task never ran. */
  const runStamp = (ts: number | null) => (ts == null ? t('common.not_reported') : formatDateTime(ts));

  if (loading) {
    return (
      <div className="h-full overflow-y-auto page-transition">
        <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
          <PageHeader title={t('scheduler.title')} description={t('scheduler.description')} icon={<Clock size={20} />} />
          <SkeletonList count={3} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card variant="default" className="max-w-sm mx-auto">
          <CardContent className="p-6 text-center">
            <AlertCircle size={32} className="text-[var(--color-error)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">{error}</p>
            <Button variant="primary" size="sm" onClick={fetchTasks}>{t('common.retry')}</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <PageHeader
          title={t('scheduler.title')}
          description={t('scheduler.summary', {
            total: tasks.length,
            enabled: tasks.filter(task => task.enabled).length,
          })}
          icon={<Clock size={20} />}
          actions={
            <div className="flex gap-2">
            <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchTasks} disabled={pending}>{t('common.refresh')}</Button>
            <Button
              variant="primary"
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => setShowAdd(!showAdd)}
              disabled={pending}
              aria-expanded={showAdd}
            >
              {t('scheduler.add_task')}
            </Button>
            </div>
          }
        />

        {actionError && <p role="alert" className="mb-4 text-sm text-[var(--color-error)]">{actionError}</p>}

        {showAdd && (
          <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
            <CardContent className="p-5 space-y-3">
              <Input
                placeholder={t('scheduler.field.name_placeholder')}
                aria-label={t('scheduler.field.name_label')}
                disabled={pending}
                value={newTask.name}
                onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              />
              <Input
                placeholder={t('scheduler.field.description_placeholder')}
                aria-label={t('scheduler.field.description_label')}
                disabled={pending}
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              />
              <div className="flex flex-col sm:flex-row gap-3">
                <Input
                  placeholder={t('scheduler.field.cron_placeholder')}
                  aria-label={t('scheduler.field.cron_label')}
                  disabled={pending}
                  value={newTask.cron}
                  onChange={(e) => setNewTask({ ...newTask, cron: e.target.value })}
                  className="font-mono"
                />
                <select
                  aria-label={t('scheduler.field.type_label')}
                  disabled={pending}
                  value={newTask.type}
                  onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
                  className="px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                >
                  {TASK_TYPE_KEYS.map(key => <option key={key} value={key}>{t(`scheduler.type.${key}`)}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => setShowAdd(false)} disabled={pending}>{t('common.cancel')}</Button>
                <Button variant="primary" size="sm" onClick={addTask} disabled={pending || !newTask.name.trim() || !newTask.cron.trim()}>{t('scheduler.create_task')}</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {tasks.length === 0 ? (
          <EmptyState
            icon="file"
            title={t('scheduler.empty_title')}
            description={t('scheduler.empty_description')}
          />
        ) : (
          <div className="divide-y divide-[var(--color-border-subtle)] border-y border-[var(--color-border-subtle)]">
            {tasks.map((task) => {
              const Icon = TYPE_ICONS[task.type || ''] || Clock;
              return (
                <article key={task.id} aria-label={task.name}>
                  <div className="py-4">
                    <div className="flex items-start gap-3">
                      <div className="pt-1 text-[var(--color-text-muted)] shrink-0">
                        <Icon size={16} aria-hidden="true" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold break-words text-[var(--color-text-primary)]">{task.name}</span>
                          {task.type && <Badge variant="default" size="xs">{task.type}</Badge>}
                          <Badge variant={task.enabled ? 'success' : 'default'} size="xs">
                            {task.enabled ? t('scheduler.enabled') : t('scheduler.stopped')}
                          </Badge>
                        </div>
                        {task.description && (
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{task.description}</p>
                        )}
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-[var(--color-text-muted)]">
                          <span className="font-mono break-all">{task.cron}</span>
                          <span>{t('scheduler.last_run', { stamp: runStamp(task.last_run) })}</span>
                          <span>{t('scheduler.next_run', { stamp: runStamp(task.next_run) })}</span>
                          <span>{typeof task.run_count === 'number'
                            ? t('scheduler.run_count', { count: task.run_count })
                            : t('scheduler.run_count_unreported')}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => toggleTask(task)}
                          disabled={pending}
                          aria-label={`${task.enabled ? t('scheduler.disable') : t('scheduler.enable')} ${task.name}`}
                          title={task.enabled ? t('scheduler.disable') : t('scheduler.enable')}
                        >
                          {task.enabled ? (
                            <ToggleRight size={18} className="text-[var(--color-accent-foreground)]" />
                          ) : (
                            <ToggleLeft size={18} className="text-[var(--color-text-muted)]" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteTask(task.id)}
                          disabled={pending}
                          aria-label={t('scheduler.delete_named', { name: task.name })}
                          className="text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
