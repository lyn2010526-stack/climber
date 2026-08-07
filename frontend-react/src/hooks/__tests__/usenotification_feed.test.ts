import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNotificationFeed} from '../usenotification_feed';

describe('usenotification_feed', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it('returns initial loading state when autoFetch is true', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: true }));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it('does not fetch when autoFetch is false', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: false }));
    expect(result.current.loading).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('fetches data on mount when autoFetch is true', async () => {
    const fetcher = vi.fn().mockResolvedValue('fetched-data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: true }));
    await act(async () => {
      await new Promise(r => setTimeout(r, 10));
    });
    expect(fetcher).toHaveBeenCalled();
  });

  it('refetch calls fetcher again', async () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: false }));
    await act(async () => {
      await result.current.refetch();
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('reset clears state', async () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: false }));
    await act(async () => {
      await result.current.refetch();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('refetch updates data', async () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: false }));
    await act(async () => {
      await result.current.refetch();
    });
    expect(result.current.data).toBe('data');
  });

  it('does not fetch when autoFetch is disabled', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    renderHook(() => useNotificationFeed('test-key', fetcher, { autoFetch: false }));
    expect(fetcher).not.toHaveBeenCalled();
  });
});
