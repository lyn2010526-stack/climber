export const API_BASE_URL = '/api/v1';

function normalizePath(url: string): string {
  const path = url.startsWith('/') ? url : `/${url}`;
  return path.replace(/^\/api(?:\/v1)?(?=\/|[?#]|$)/, '');
}

function getToken(): string | null {
  try {
    return localStorage.getItem('auth_token');
  } catch {
    return null;
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

interface RequestConfig {
  headers?: Record<string, string>;
  skipAuth?: boolean;
  signal?: AbortSignal;
}

async function request<T>(method: string, url: string, body?: unknown, config: RequestConfig = {}): Promise<T> {
  const { headers = {}, skipAuth, signal } = config;

  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (!skipAuth) {
    Object.assign(finalHeaders, getAuthHeaders());
  }

  const res = await fetch(`${API_BASE_URL}${normalizePath(url)}`, {
    method,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let errorData: unknown;
    try {
      errorData = await res.clone().json();
    } catch {
      errorData = await res.text();
    }
    throw new ApiError(
      `API Error: ${res.status} ${res.statusText}`,
      res.status,
      errorData
    );
  }

  const contentType = res.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return res.text() as unknown as T;
}

export const apiClient = {
  get<T>(url: string, config?: RequestConfig): Promise<T> {
    return request<T>('GET', url, undefined, config);
  },

  post<T>(url: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return request<T>('POST', url, body, config);
  },

  put<T>(url: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return request<T>('PUT', url, body, config);
  },

  patch<T>(url: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return request<T>('PATCH', url, body, config);
  },

  delete<T>(url: string, config?: RequestConfig): Promise<T> {
    return request<T>('DELETE', url, undefined, config);
  },

  stream(
    url: string,
    body: unknown,
    signal?: AbortSignal
  ): Promise<Response> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    };

    return fetch(`${API_BASE_URL}${normalizePath(url)}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });
  },
};
