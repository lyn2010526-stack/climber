// Shared API client infrastructure: singleton ApiClient with retry,
// request de-duplication, GET caching and cache invalidation.
// Resource-domain methods live in sibling modules and are merged onto
// ApiClient via declaration merging (see those files).

const BASE_URL = '/api/v1';
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 300;

export interface ApiError {
  detail: string;
}

export class ApiClient {
  private pendingRequests = new Map<string, Promise<any>>();
  private requestCache = new Map<string, { data: any; timestamp: number }>();
  private readonly CACHE_TTL = 5000;

  getAuthHeaders(): Record<string, string> {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async requestWithRetry<T>(fn: () => Promise<T>): Promise<T> {
    for (let i = 0; i <= MAX_RETRIES; i++) {
      try {
        return await fn();
      } catch (err) {
        if (this.isRetryableError(err) && i < MAX_RETRIES) {
          await new Promise(r => setTimeout(r, RETRY_DELAY_MS * (i + 1)));
          continue;
        }
        throw err;
      }
    }
    throw new Error('Unexpected retry failure');
  }

  private isRetryableError(err: unknown): boolean {
    const message = (err as Error)?.message || '';
    const statusMatch = message.match(/HTTP (\d+)/);
    if (!statusMatch?.[1]) {
      // No HTTP status embedded: treat as a network-level failure and retry.
      return true;
    }
    const status = parseInt(statusMatch[1], 10);
    // Retry only on timeout, rate limiting and server errors.
    // Client errors (401/403/other 4xx) are non-retryable.
    return status === 408 || status === 429 || status >= 500;
  }

  private async deduplicatedRequest<T>(key: string, fn: () => Promise<T>): Promise<T> {
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key) as Promise<T>;
    }
    const promise = this.requestWithRetry(fn).finally(() => {
      this.pendingRequests.delete(key);
    });
    this.pendingRequests.set(key, promise);
    return promise;
  }

  private cachedGet<T>(key: string, fn: () => Promise<T>): Promise<T> {
    const cached = this.requestCache.get(key);
    if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
      return Promise.resolve(cached.data);
    }
    const pending = this.pendingRequests.get(key);
    if (pending) return pending as Promise<T>;
    const promise = this.requestWithRetry(fn)
      .then(data => {
        this.requestCache.set(key, { data, timestamp: Date.now() });
        return data;
      })
      .finally(() => this.pendingRequests.delete(key));
    this.pendingRequests.set(key, promise);
    return promise;
  }

  resetCache() {
    this.pendingRequests.clear();
    this.requestCache.clear();
  }

  // Invalidate only cache entries for a given resource prefix (e.g. '/sessions').
  // Falls back to a full cache reset when no prefix is provided.
  invalidateCache(prefix?: string) {
    if (!prefix) {
      this.resetCache();
      return;
    }
    const matches = (key: string) => {
      const pathPart = key.split(':').slice(1).join(':');
      return pathPart === prefix || pathPart.startsWith(`${prefix}/`) || pathPart.startsWith(`${prefix}?`);
    };
    for (const key of [...this.pendingRequests.keys()]) {
      if (matches(key)) this.pendingRequests.delete(key);
    }
    for (const key of [...this.requestCache.keys()]) {
      if (matches(key)) this.requestCache.delete(key);
    }
  }

  // Derive the top-level resource prefix from a path, e.g.
  // '/sessions/123/chat' -> '/sessions', '/workflows/templates/x' -> '/workflows'.
  private resourcePrefix(path: string): string {
    const match = path.match(/^(\/[^/]+)/);
    return match?.[1] ?? path;
  }

  async request<T>(path: string, options: RequestInit = {}, useCache = true): Promise<T> {
    const isMutation = options.method === 'POST' || options.method === 'PUT' || options.method === 'PATCH' || options.method === 'DELETE';
    const isCacheable = useCache && !isMutation;
    const cacheKey = isCacheable ? `${options.method || 'GET'}:${path}` : null;

    const doRequest = async (): Promise<T> => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers as Record<string, string>,
      };

      const response = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      if (isMutation) {
        // Only invalidate caches related to the mutated resource instead of
        // wiping every cached GET.
        this.invalidateCache(this.resourcePrefix(path));
      }

      return response.json();
    };

    if (cacheKey) {
      return this.cachedGet(cacheKey, doRequest);
    }
    if (isMutation) {
      return this.requestWithRetry(doRequest);
    }
    return this.deduplicatedRequest(path, doRequest);
  }
}

export { BASE_URL };

export const api = new ApiClient();
