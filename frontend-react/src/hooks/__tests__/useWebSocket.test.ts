import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../useWebSocket';

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it('returns initial loading state when immediate is true', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: true }));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it('does not fetch when immediate is false', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: false }));
    expect(result.current.loading).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('fetches data on mount when immediate is true', async () => {
    const fetcher = vi.fn().mockResolvedValue('fetched-data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: true }));
    await act(async () => {
      await new Promise(r => setTimeout(r, 10));
    });
    expect(fetcher).toHaveBeenCalled();
  });

  it('refetch calls fetcher again', async () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: false }));
    await act(async () => {
      await result.current.refetch();
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('reset clears state', async () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: false }));
    await act(async () => {
      await result.current.refetch();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('mutate sets data directly', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    const { result } = renderHook(() => useWebSocket('test-key', fetcher, { immediate: false }));
    act(() => {
      result.current.mutate('mutated-data');
    });
    expect(result.current.data).toBe('mutated-data');
  });

  it('does not fetch when disabled', () => {
    const fetcher = vi.fn().mockResolvedValue('data');
    renderHook(() => useWebSocket('test-key', fetcher, { enabled: false, immediate: true }));
    expect(fetcher).not.toHaveBeenCalled();
  });
});
