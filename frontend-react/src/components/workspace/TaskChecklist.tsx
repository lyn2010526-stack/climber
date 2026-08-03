import { ChevronDown, ChevronRight, Circle, Loader2, Check, X } from 'lucide-react';

interface Task {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

interface TaskChecklistProps {
  tasks: Task[];
  isVisible: boolean;
  onToggle: () => void;
}

function TaskIcon({ status }: { status: Task['status'] }) {
  switch (status) {
    case 'pending':
      return <Circle size={14} className="text-[var(--color-text-muted)]" />;
    case 'in_progress':
      return <Loader2 size={14} className="text-blue-400 animate-spin" />;
    case 'completed':
      return <Check size={14} className="text-green-400" />;
    case 'failed':
      return <X size={14} className="text-red-400" />;
  }
}

function statusTextClass(status: Task['status']): string {
  switch (status) {
    case 'pending':
      return 'text-[var(--color-text-secondary)]';
    case 'in_progress':
      return 'text-[var(--color-text-primary)]';
    case 'completed':
      return 'text-[var(--color-text-muted)] line-through';
    case 'failed':
      return 'text-red-400';
  }
}

export function TaskChecklist({ tasks, isVisible, onToggle }: TaskChecklistProps) {
  const completed = tasks.filter(t => t.status === 'completed').length;
  const total = tasks.length;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)]/50 transition-colors"
      >
        {isVisible ? <ChevronDown size={14} className="text-[var(--color-text-secondary)]" /> : <ChevronRight size={14} className="text-[var(--color-text-secondary)]" />}
         <span>任务计划</span>
        <span className="ml-auto text-[var(--color-text-muted)]">{completed}/{total}</span>
      </button>

      {isVisible && (
        <div className="border-t border-[var(--color-border-subtle)]">
          <div className="h-1 bg-[var(--color-bg-surface-2)]">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-green-400 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <ul className="py-1">
            {tasks.map(task => (
              <li
                key={task.id}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-bg-surface-2)]/30 transition-colors"
              >
                <TaskIcon status={task.status} />
                <span className={`flex-1 ${statusTextClass(task.status)}`}>
                  {task.description}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
