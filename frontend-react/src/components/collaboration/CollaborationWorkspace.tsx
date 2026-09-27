import { TaskProgress } from './TaskProgress';
import { useI18n } from '../../i18n';

export interface TaskView {
  taskId?: string;
  status?: string;
  progress?: number;
  totalSteps?: number;
  objective?: string;
  result?: unknown;
  error?: string | null;
  cancelling: boolean;
  /** Transport or cancellation error, kept separate from the task's own error field. */
  requestError?: string;
}

export interface CollaborationWorkspaceProps {
  /** Authoritative task state; owned by the group so the sidebar and workspace agree. */
  task: TaskView;
  onCancel: () => void;
  onReset: () => void;
  onRetry: () => void;
}

/**
 * Read side of the group task surface. Submission lives in the collaboration
 * sidebar, so the workspace only reports what the backend returned and offers
 * no second input panel.
 *
 * Whether a run is still cancellable is decided once, by TaskProgress, from the
 * same status predicate the sidebar's polling uses. This component only
 * forwards the callback.
 */
export function CollaborationWorkspace({ task, onCancel, onReset, onRetry }: CollaborationWorkspaceProps) {
  const { t } = useI18n();
  return (
    <section aria-labelledby="group-task-heading" className="min-w-0">
      <h2 id="group-task-heading" className="mb-3 text-sm font-semibold">
        {t('collaboration.heading_task')}
      </h2>
      {task.requestError && (
        <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">
          {task.requestError}
        </p>
      )}
      <TaskProgress
        taskId={task.taskId}
        status={task.status}
        progress={task.progress}
        totalSteps={task.totalSteps}
        objective={task.objective}
        result={task.result}
        error={task.error}
        onCancel={onCancel}
        cancelling={task.cancelling}
          onReset={onReset}
          onRetry={onRetry}
      />
    </section>
  );
}
