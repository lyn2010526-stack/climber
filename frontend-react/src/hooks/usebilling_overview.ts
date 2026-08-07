import { useState, useEffect, useCallback, useRef } from "react";

export interface BillingOverviewHookOptions {
  autoFetch?: boolean;
  pollingInterval?: number;
  retryCount?: number;
  retryDelay?: number;
  cacheTime?: number;
  onSuccess?: (data: unknown) => void;
  onError?: (error: Error) => void;
}

export interface BillingOverviewHookResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  reset: () => void;
  isStale: boolean;
  lastFetchedAt: Date | null;
}

const cache = new Map<string, { data: unknown; timestamp: number }>();

export function useBillingOverview<T = unknown>(
  key: string,
  fetcher: () => Promise<T>,
  options: BillingOverviewHookOptions = {}
): BillingOverviewHookResult<T> {
  const {
    autoFetch = true,
    pollingInterval,
    
    
    onSuccess,
    onError,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(autoFetch);
  const [error, setError] = useState<Error | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (!mountedRef.current) return;
      setData(result);
      setLastFetchedAt(new Date());
      onSuccess?.(result);
    } catch (err) {
      if (!mountedRef.current) return;
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [fetcher, onSuccess, onError]);

  const refetch = useCallback(async () => {
    cache.delete(key);
    await fetchData();
  }, [key, fetchData]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
    setLastFetchedAt(null);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (autoFetch) fetchData();
    return () => { mountedRef.current = false; };
  }, [autoFetch, fetchData]);

  useEffect(() => {
    if (!pollingInterval) return;
    const interval = setInterval(() => {
      if (!loading) refetch();
    }, pollingInterval);
    return () => clearInterval(interval);
  }, [pollingInterval, loading, refetch]);

  return { data, loading, error, refetch, reset, isStale: false, lastFetchedAt };
}

export function useBillingOverviewMutation<T = unknown, V = unknown>(
  mutator: (variables: V) => Promise<T>
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (variables: V) => {
    setLoading(true);
    setError(null);
    try {
      const result = await mutator(variables);
      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [mutator]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { mutate, data, loading, error, reset };
}
