import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../api';
import { isActiveTaskStatus } from './taskStatus';
import { consumeTaskEvents, mergeTaskEvent, type LiveTask, type TaskEvent } from '../anchored/taskApi';

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
  /** 当前群组标识：在异步响应落地前核对，避免旧群组响应写进新群组状态。 */
  const groupIdRef = useRef(groupId);
  groupIdRef.current = groupId;

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
  /** Whether the error on screen was raised by the poll itself. */
  const pollFailed = useRef(false);

  useEffect(() => {
    if (!taskId || !active) return;
    const controller = new AbortController();
    let cursor: { epoch: string; sequence: number } | undefined;
    void consumeTaskEvents(taskId, controller.signal, (event: TaskEvent) => {
      setTask(previous => {
        if (!previous || previous.task_id !== taskId) return previous;
        const updated = mergeTaskEvent(previous as LiveTask, event, cursor);
        if (updated === previous) return previous;
        cursor = { epoch: event.epoch, sequence: event.sequence };
        return updated as Task;
      });
    }).catch(() => {
      // The detail poll below remains authoritative when the stream disconnects.
    });
    return () => controller.abort();
  }, [taskId, active]);

  useEffect(() => {
    if (!taskId || !active) {
      pollFailed.current = false;
      return;
    }
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const result = await api.getTask(taskId);
        if (!disposed) {
          setTask(result);
          // Only retire the error this poll raised. A refused cancellation or a
          // failed submission belongs to the user's action and must stay on
          // screen until the user does something else.
          if (pollFailed.current) {
            pollFailed.current = false;
            setError('');
          }
        }
      } catch (reason) {
        if (!disposed) {
          pollFailed.current = true;
          setError(reason instanceof Error ? reason.message : '查询任务失败');
        }
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
      const requestGroupId = groupId;
      setSubmitting(true);
      setError('');
      setLastSubmission({ objective, maxSteps });
      try {
        const result = await api.createTask({
          task_type: 'agent_run',
          payload: { group_id: groupId, objective, max_steps: maxSteps },
        });
        // A submit that resolves after the user switched groups must not write
        // its task into the new group's slot (R10-01).
        if (!mounted.current || groupIdRef.current !== requestGroupId) return;
        setTask({
          ...result,
          objective,
        } as Task);
      } catch (reason) {
        if (mounted.current && groupIdRef.current === requestGroupId) {
          setError(reason instanceof Error ? reason.message : '提交任务失败');
        }
      } finally {
        if (mounted.current && groupIdRef.current === requestGroupId) setSubmitting(false);
      }
    },
    [active, groupId, submitting],
  );

  const refreshTask = useCallback(async (updatedTaskId = taskId) => {
    if (!updatedTaskId || updatedTaskId !== taskId) return;
    const requestGroupId = groupIdRef.current;
    try {
      const latest = await api.getTask(updatedTaskId);
      if (mounted.current && groupIdRef.current === requestGroupId) setTask(latest);
    } catch (reason) {
      if (mounted.current && groupIdRef.current === requestGroupId) setError(reason instanceof Error ? reason.message : '查询任务失败');
    }
  }, [taskId]);

  const retryTask = useCallback(() => {
    if (lastSubmission && !active) void submitTask(lastSubmission.objective, lastSubmission.maxSteps);
  }, [active, lastSubmission, submitTask]);

  const cancelTask = useCallback(async () => {
    if (!taskId || cancelling) return;
    const requestGroupId = groupIdRef.current;
    setCancelling(true);
    setError('');
    try {
      const result = await api.stopTask(taskId);
      if (!result.cancelled) throw new Error('任务取消未确认');
      // The cancel endpoint only acknowledges the request; re-read the task so
      // the rendered status is the one the backend actually persisted.
      const latest = await api.getTask(taskId);
      if (mounted.current && groupIdRef.current === requestGroupId) setTask(latest);
    } catch (reason) {
      if (mounted.current && groupIdRef.current === requestGroupId) setError(reason instanceof Error ? reason.message : '取消任务失败');
    } finally {
      if (mounted.current && groupIdRef.current === requestGroupId) setCancelling(false);
    }
  }, [cancelling, taskId]);

  const resetTask = useCallback(() => {
    setTask(null);
    setError('');
  }, []);

  return { task, taskId, active, submitting, cancelling, error, submitTask, cancelTask, resetTask, retryTask, refreshTask };
}
