import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../api';
import { isActiveTaskStatus } from './taskStatus';

type Task = Awaited<ReturnType<typeof api.getTask>>;

const POLL_INTERVAL_MS = 2000;

/**
 * Owns the single task of a group: submission, authoritative polling and
 * cancellation. The collaboration sidebar submits through it and the workspace
 * renders it, so only one input panel and one status source exist.
 */
export function useGroupTask(groupId: string) {
  const [task, setTask] = useState<Task | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState('');
  const [lastSubmission, setLastSubmission] = useState<{ objective: string; maxSteps: number } | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Reset per group so a previous group's run never leaks into the new context.
  useEffect(() => {
    setTask(null);
    setError('');
    setSubmitting(false);
    setCancelling(false);
    setLastSubmission(null);
  }, [groupId]);

  const taskId = task?.task_id;
  const active = !!task && isActiveTaskStatus(task.status);

  useEffect(() => {
    if (!taskId || !active) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const result = await api.getTask(taskId);
        if (!disposed) {
          setTask(result);
          setError('');
        }
      } catch (reason) {
        if (!disposed) setError(reason instanceof Error ? reason.message : '查询任务失败');
      } finally {
        if (!disposed) timer = setTimeout(refresh, POLL_INTERVAL_MS);
      }
    };
    void refresh();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [taskId, active]);

  const submitTask = useCallback(
    async (objective: string, maxSteps: number) => {
      if (submitting || active) return;
      setSubmitting(true);
      setError('');
      setLastSubmission({ objective, maxSteps });
      try {
        const result = await api.createTask({
          task_type: 'agent_run',
          payload: { group_id: groupId, objective, max_steps: maxSteps },
        });
        if (mounted.current) setTask(result);
      } catch (reason) {
        if (mounted.current) setError(reason instanceof Error ? reason.message : '提交任务失败');
      } finally {
        if (mounted.current) setSubmitting(false);
      }
    },
    [active, groupId, submitting],
  );

  const refreshTask = useCallback(async (updatedTaskId = taskId) => {
    if (!updatedTaskId || updatedTaskId !== taskId) return;
    try {
      const latest = await api.getTask(updatedTaskId);
      if (mounted.current) setTask(latest);
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : '查询任务失败');
    }
  }, [taskId]);

  const retryTask = useCallback(() => {
    if (lastSubmission && !active) void submitTask(lastSubmission.objective, lastSubmission.maxSteps);
  }, [active, lastSubmission, submitTask]);

  const cancelTask = useCallback(async () => {
    if (!taskId || cancelling) return;
    setCancelling(true);
    setError('');
    try {
      const result = await api.stopTask(taskId);
      if (!result.cancelled) throw new Error('任务取消未确认');
      // The cancel endpoint only acknowledges the request; re-read the task so
      // the rendered status is the one the backend actually persisted.
      const latest = await api.getTask(taskId);
      if (mounted.current) setTask(latest);
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : '取消任务失败');
    } finally {
      if (mounted.current) setCancelling(false);
    }
  }, [cancelling, taskId]);

  const resetTask = useCallback(() => {
    setTask(null);
    setError('');
  }, []);

  return { task, taskId, active, submitting, cancelling, error, submitTask, cancelTask, resetTask, retryTask, refreshTask };
}
