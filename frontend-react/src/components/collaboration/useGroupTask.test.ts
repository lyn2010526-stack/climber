import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { useGroupTask } from './useGroupTask';

vi.mock('../../api', () => ({
  api: {
    createTask: vi.fn(),
    getTask: vi.fn(),
    stopTask: vi.fn(),
  },
}));

type Task = Awaited<ReturnType<typeof api.getTask>>;

const POLL_INTERVAL_MS = 2000;

const runningTask = { task_id: 't1', status: 'running' } as unknown as Task;

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

/** Submits the group's one task and lets the first poll settle. */
async function submit(result: { current: ReturnType<typeof useGroupTask> }) {
  await act(async () => {
    await result.current.submitTask('objective', 3);
  });
  await act(async () => {});
}

describe('useGroupTask polling', () => {
  it('keeps a refused cancellation on screen across a poll tick', async () => {
    vi.mocked(api.createTask).mockResolvedValue(runningTask);
    vi.mocked(api.getTask).mockResolvedValue(runningTask);
    vi.mocked(api.stopTask).mockResolvedValue({ cancelled: false } as unknown as Awaited<ReturnType<typeof api.stopTask>>);

    const { result, unmount } = renderHook(() => useGroupTask('g1'));
    await submit(result);
    expect(result.current.active).toBe(true);

    await act(async () => {
      await result.current.cancelTask();
    });
    expect(result.current.error).toBe('任务取消未确认');

    // The refusal belongs to the user's action: an authoritative poll that
    // still reports the task running must not retire it.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    });
    expect(result.current.error).toBe('任务取消未确认');

    unmount();
  });

  it('clears an error the poll itself raised once a poll succeeds', async () => {
    vi.mocked(api.createTask).mockResolvedValue(runningTask);
    vi.mocked(api.getTask)
      .mockRejectedValueOnce(new Error('查询任务失败'))
      .mockResolvedValue(runningTask);

    const { result, unmount } = renderHook(() => useGroupTask('g1'));
    await submit(result);
    expect(result.current.error).toBe('查询任务失败');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    });
    expect(result.current.error).toBe('');

    unmount();
  });
});
