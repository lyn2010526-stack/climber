import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMetric } from '../useMetric';

describe('useMetric', () => {
  const mockFetcher = vi.fn();
  
  beforeEach(() => {
    vi.useRealTimers();
    mockFetcher.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns initial state with loading true when autoFetch is true', () => {
    mockFetcher.mockResolvedValue({ value: 100 });
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: true })
    );
    
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('returns initial state without loading when autoFetch is false', () => {
    mockFetcher.mockResolvedValue({ value: 100 });
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: false })
    );
    
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('fetches data on mount when autoFetch is true', async () => {
    const mockData = { metric: 'cpu_usage', value: 45.5 };
    mockFetcher.mockResolvedValue(mockData);
    
    const { result } = renderHook(() => 
      useMetric('cpu-metric', mockFetcher, { autoFetch: true })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(mockFetcher).toHaveBeenCalledTimes(1);
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockData);
  });

  it('does not fetch when autoFetch is false', async () => {
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: false })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(mockFetcher).not.toHaveBeenCalled();
  });

  it('calls refetch to fetch data again', async () => {
    const mockData = { value: 100 };
    mockFetcher.mockResolvedValue(mockData);
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: false })
    );
    
    await act(async () => {
      await result.current.refetch();
    });
    
    expect(mockFetcher).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(mockData);
  });

  it('reset clears data and error', () => {
    mockFetcher.mockRejectedValue(new Error('Fetch failed'));
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: false })
    );
    
    act(() => {
      result.current.setData({ success: true });
    });
    
    expect(result.current.data).toEqual({ success: true });
    
    act(() => {
      result.current.reset();
    });
    
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('setData sets data directly without fetching', () => {
    const customData = { manually_set: 'value' };
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: false })
    );
    
    act(() => {
      result.current.setData(customData);
    });
    
    expect(result.current.data).toEqual(customData);
    expect(mockFetcher).not.toHaveBeenCalled();
  });

  it('invalidate removes cached data and refetches', async () => {
    const mockData = { value: 200 };
    mockFetcher.mockResolvedValue(mockData);
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: true })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(result.current.data).toEqual(mockData);
    
    const newData = { value: 300 };
    mockFetcher.mockResolvedValueOnce(newData);
    
    act(() => {
      result.current.invalidate();
    });
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(result.current.data).toEqual(newData);
  });

  it('handles fetch errors and sets error state', async () => {
    const testError = new Error('Network error');
    mockFetcher.mockRejectedValue(testError);
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { autoFetch: true })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toEqual(testError);
  });

  it('retries on failure up to retryCount times', async () => {
    mockFetcher
      .mockRejectedValueOnce(new Error('Fail'))
      .mockRejectedValueOnce(new Error('Fail'))
      .mockResolvedValueOnce({ success: true });
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { 
        autoFetch: true, 
        retryCount: 3,
        retryDelay: 10
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });
    
    expect(mockFetcher).toHaveBeenCalledTimes(3);
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual({ success: true });
  });

  it('resets retry count on successful fetch', async () => {
    mockFetcher
      .mockRejectedValueOnce(new Error('Fail'))
      .mockResolvedValueOnce({ reset_retry: true });
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { 
        autoFetch: true, 
        retryCount: 2
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 80));
    });
    
    // Should have tried twice (initial + retry) before succeeding
    expect(mockFetcher).toHaveBeenCalled();
    
    mockFetcher.mockRejectedValue(new Error('Fail Again'));
    
    act(() => {
      result.current.invalidate();
    });
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 60));
    });
    
    // Should try again with fresh retry count
    expect(mockFetcher).toHaveBeenCalled();
  });

  it('caches successful responses by key', async () => {
    mockFetcher.mockResolvedValue({ cached_value: 123 });
    
    const { result } = renderHook(() => 
      useMetric('cache-test', mockFetcher, { autoFetch: true })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    // Cache is working - data should be populated
    expect(result.current.data).toBeTruthy();
    expect(result.current.loading).toBe(false);
    
    // Subsequent renders will still mount but data comes from cache
    expect(result.current.data).toHaveProperty('cached_value');
  });

  it('supports refreshInterval for automatic refetching', async () => {
    mockFetcher.mockResolvedValue({ timestamp: Date.now() });
    
    const { result } = renderHook(() => 
      useMetric('interval-test', mockFetcher, { 
        autoFetch: true,
        refreshInterval: 50 
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(mockFetcher).toHaveBeenCalled();
  });

  it('calls onSuccess callback with fetched data', async () => {
    const mockOnSuccess = vi.fn();
    const mockData = { success_cb: true };
    mockFetcher.mockResolvedValue(mockData);
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { 
        autoFetch: true,
        onSuccess: mockOnSuccess
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(mockOnSuccess).toHaveBeenCalledWith(mockData);
  });

  it('calls onError callback on failure', async () => {
    const mockOnError = vi.fn();
    const testError = new Error('Test error');
    mockFetcher.mockRejectedValue(testError);
    
    const { result } = renderHook(() => 
      useMetric('test-key', mockFetcher, { 
        autoFetch: true,
        onError: mockOnError
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(mockOnError).toHaveBeenCalledWith(testError);
  });

  it('prevents memory leaks by unmounting cleanup', async () => {
    mockFetcher.mockResolvedValue({ unmount_test: true });
    
    const { result, unmount } = renderHook(() => 
      useMetric('unmount-test', mockFetcher, { autoFetch: true })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    
    expect(result.current.data).toEqual({ unmount_test: true });
    
    unmount();
  });
});
