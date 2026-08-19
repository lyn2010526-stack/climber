import type { TaskSummary } from '../../types/api';

export type TaskQueueFilter = 'all' | 'active' | 'review' | 'completed' | 'failed';

export interface TaskStatusPresentation {
  label: string;
  tone: 'muted' | 'accent' | 'warning' | 'success' | 'error';
}

const STATUS_PRESENTATION: Record<string, TaskStatusPresentation> = {
  pending: { label: '等待中', tone: 'muted' },
  running: { label: '执行中', tone: 'accent' },
  waiting_approval: { label: '等待审批', tone: 'warning' },
  reviewing: { label: '审查中', tone: 'warning' },
  completed: { label: '已完成', tone: 'success' },
  partial: { label: '部分完成', tone: 'warning' },
  failed: { label: '失败', tone: 'error' },
  stopped: { label: '已停止', tone: 'muted' },
  cancelled: { label: '已取消', tone: 'muted' },
};

export function getTaskStatusPresentation(status: string): TaskStatusPresentation {
  return STATUS_PRESENTATION[status] || { label: status || '未知状态', tone: 'muted' };
}

export function matchesTaskQueueFilter(task: TaskSummary, filter: TaskQueueFilter): boolean {
  if (filter === 'all') return true;
  if (filter === 'active') return ['pending', 'running'].includes(task.status);
  if (filter === 'review') return ['waiting_approval', 'reviewing'].includes(task.status);
  if (filter === 'completed') return ['completed', 'partial'].includes(task.status);
  return ['failed', 'stopped', 'cancelled'].includes(task.status);
}

export function summarizeTasks(tasks: TaskSummary[]) {
  return {
    total: tasks.length,
    active: tasks.filter((task) => matchesTaskQueueFilter(task, 'active')).length,
    review: tasks.filter((task) => matchesTaskQueueFilter(task, 'review')).length,
    completed: tasks.filter((task) => matchesTaskQueueFilter(task, 'completed')).length,
    failed: tasks.filter((task) => matchesTaskQueueFilter(task, 'failed')).length,
  };
}
