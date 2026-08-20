import { Clock, Shield, Bot } from 'lucide-react';
import { ROLE_ICONS, ROLE_COLORS, STATUS_ICONS, STATUS_COLORS } from './types';
import type { ClusterTask } from './types';

function TaskNode({
  task,
  isSelected,
  onClick,
}: {
  task: ClusterTask;
  isSelected: boolean;
  onClick: () => void;
}) {
  const Icon = ROLE_ICONS[task.role] || Bot;
  const StatusIcon = STATUS_ICONS[task.status] || Clock;

  return (
    <div className="relative flex items-start gap-4 py-3">
      {/* Node circle */}
      <div className={`relative z-10 w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 cursor-pointer transition-all duration-200 ${
        task.status === 'completed' ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/20' :
        task.status === 'running' ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)]/20' :
        'bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)]'
      }`} onClick={onClick}>
        <Icon size={18} className={
          task.status === 'completed' ? 'text-[var(--color-success)]' :
          task.status === 'running' ? 'text-[var(--color-accent)]' :
          'text-[var(--color-text-muted)]'
        } />
      </div>

      {/* Card */}
      <div className={`flex-1 p-3 rounded-2xl cursor-pointer transition-all duration-200 border ${
        isSelected ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)]/30' : 'bg-[var(--color-bg-surface-1)] border-[var(--color-border-subtle)]'
      }`} onClick={onClick}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2 py-0.5 rounded-lg text-[10px] font-medium border ${ROLE_COLORS[task.role] || ROLE_COLORS['planner']}`}>
            {task.role}
          </span>
          <StatusIcon size={12} className={STATUS_COLORS[task.status]} />
          <span className="text-[10px] text-[var(--color-text-muted)] capitalize">{task.status}</span>
          {task.process_type && task.process_type !== 'sequential' && (
            <span className="px-2 py-0.5 rounded-lg text-[9px] bg-[var(--color-accent-secondary)]/10 text-[var(--color-accent-secondary)] border border-[var(--color-accent-secondary)]/20">
              {task.process_type}
            </span>
          )}
          {task.human_review_required && (
            <span className="px-2 py-0.5 rounded-lg text-[9px] bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/20">
              人工审批
            </span>
          )}
        </div>
        <p className="text-xs text-[var(--color-text-primary)] mt-1.5">{task.description}</p>
        {task.dependencies.length > 0 && (
           <p className="text-[10px] text-[var(--color-text-muted)] mt-1">依赖：{task.dependencies.join(', ')}</p>
        )}
        {task.guardrails && task.guardrails.length > 0 && (
          <div className="flex items-center gap-1 mt-1.5">
            <Shield size={10} className="text-[var(--color-text-muted)]" />
            <span className="text-[10px] text-[var(--color-text-muted)]">{task.guardrails.length} 个校验规则</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function TaskDagPanel({
  tasks,
  selectedTaskId,
  onTaskClick,
}: {
  tasks: ClusterTask[];
  selectedTaskId: string | null;
  onTaskClick: (taskId: string) => void;
}) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-[var(--color-text-primary)]">执行计划</h2>
      <div className="relative">
        {/* Connection line */}
        <div className="absolute left-6 top-8 bottom-8 w-px bg-[var(--color-border-subtle)]" />

        {tasks.map((task) => (
          <TaskNode
            key={task.id}
            task={task}
            isSelected={selectedTaskId === task.id}
            onClick={() => onTaskClick(task.id)}
          />
        ))}
      </div>
    </div>
  );
}
