import { describe, expect, it } from 'vitest';
import type { TaskSummary } from '../../../types/api';
import { getTaskStatusPresentation, matchesTaskQueueFilter, summarizeTasks } from '../taskQueue';

const task = (status: string): TaskSummary => ({
  id: status,
  group_id: 'group-1',
  description: status,
  status,
});

describe('task queue state', () => {
  it('groups approval and review states into the review filter', () => {
    expect(matchesTaskQueueFilter(task('waiting_approval'), 'review')).toBe(true);
    expect(matchesTaskQueueFilter(task('reviewing'), 'review')).toBe(true);
  });

  it('counts task groups without dropping partial or cancelled tasks', () => {
    expect(summarizeTasks([
      task('running'),
      task('partial'),
      task('cancelled'),
      task('completed'),
    ])).toEqual({ total: 4, active: 1, review: 0, completed: 2, failed: 1 });
  });

  it('keeps unknown API states visible with a readable fallback', () => {
    expect(getTaskStatusPresentation('queued')).toEqual({ label: 'queued', tone: 'muted' });
  });
});
