import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactNode } from 'react';
import { useRisks } from '../useRisks';

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}));
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 1, username: 'test' } }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

const wrapper = ({ children }: { children: ReactNode }) =>
  createElement(QueryClientProvider, { client: queryClient }, children);

const mockPage = { items: [{ id: 1, name: 'Item 1' }], total: 1 };

describe('useRisks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useRisks(), { wrapper });
    expect(result.current.data).toBeUndefined();
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(20);
    expect(result.current.selectedIds).toEqual([]);
    expect(result.current.filters).toEqual({});
  });

  it('fetch loads data from apiClient', async () => {
    const { apiClient } = await import('@/lib/api-client');
    (apiClient.get as any).mockResolvedValue({ data: mockPage });
    const { result } = renderHook(() => useRisks(), { wrapper });
    await act(async () => {
      await result.current.fetch();
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(apiClient.get).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockPage);
  });

  it('create posts to /risks', async () => {
    const { apiClient } = await import('@/lib/api-client');
    (apiClient.post as any).mockResolvedValue({ data: { id: 2 } });
    const { result } = renderHook(() => useRisks(), { wrapper });
    await act(async () => {
      await result.current.create({ name: 'New Item' });
    });
    expect(apiClient.post).toHaveBeenCalledWith('/risks', { name: 'New Item' });
  });

  it('update puts to /risks/{id}', async () => {
    const { apiClient } = await import('@/lib/api-client');
    (apiClient.put as any).mockResolvedValue({ data: { id: 1 } });
    const { result } = renderHook(() => useRisks(), { wrapper });
    await act(async () => {
      await result.current.update(1, { name: 'Updated' });
    });
    expect(apiClient.put).toHaveBeenCalledWith('/risks/1', { name: 'Updated' });
  });

  it('remove deletes /risks/{id}', async () => {
    const { apiClient } = await import('@/lib/api-client');
    (apiClient.delete as any).mockResolvedValue({ data: {} });
    const { result } = renderHook(() => useRisks(), { wrapper });
    await act(async () => {
      await result.current.remove(1);
    });
    expect(apiClient.delete).toHaveBeenCalledWith('/risks/1');
  });

  it('setPage updates page state', () => {
    const { result } = renderHook(() => useRisks(), { wrapper });
    act(() => result.current.setPage(3));
    expect(result.current.page).toBe(3);
  });

  it('setSorting updates sort state', () => {
    const { result } = renderHook(() => useRisks(), { wrapper });
    act(() => result.current.setSorting('name', 'asc'));
    expect(result.current.sortBy).toBe('name');
    expect(result.current.sortOrder).toBe('asc');
  });

  it('selectItem updates selectedIds', () => {
    const { result } = renderHook(() => useRisks(), { wrapper });
    act(() => result.current.selectItem(5, true));
    expect(result.current.selectedIds).toContain(5);
    act(() => result.current.selectItem(5, false));
    expect(result.current.selectedIds).not.toContain(5);
  });
});
