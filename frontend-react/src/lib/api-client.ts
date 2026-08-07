const BASE_URL = '';

function getToken(): string | null {
  try {
    return localStorage.getItem('climber-auth')
      ? JSON.parse(localStorage.getItem('climber-auth') || '{}')?.state?.token ?? null
      : null;
  } catch {
    return null;
  }
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
    const token = getToken();
    if (token) {
      finalHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${url}`, {
    method,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let errorData: unknown;
    try {
      errorData = await res.json();
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
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return fetch(`${BASE_URL}${url}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });
  },
};
