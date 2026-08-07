import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessions } from '../useSessions';

const { mockApiClient, mockRefetch, mockQueryData } = vi.hoisted(() => ({
  mockApiClient: {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    post: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    put: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    delete: vi.fn().mockResolvedValue({ data: null }),
  },
  mockRefetch: vi.fn(),
  mockQueryData: { items: [{ id: 1 }, { id: 2 }], total: 2 },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: mockQueryData,
    isLoading: false,
    error: null,
    refetch: mockRefetch,
  }),
  useMutation: (opts: any) => ({ mutateAsync: opts.mutationFn, isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

vi.mock('@/lib/api-client', () => ({
  apiClient: mockApiClient,
}));

vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ showToast: vi.fn(), toast: vi.fn(), removeToast: vi.fn(), toasts: [] }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
    reset: vi.fn(),
    mutate: vi.fn(),
  }),
}));

describe('useSessions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useSessions());
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(20);
    expect(result.current.total).toBe(0);
    expect(result.current.sortBy).toBe('created_at');
    expect(result.current.sortOrder).toBe('desc');
    expect(result.current.selectedIds).toEqual([]);
    expect(result.current.filters).toEqual({});
  });

  it('setPage updates the page', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.setPage(3));
    expect(result.current.page).toBe(3);
  });

  it('setPageSize updates size and resets page', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.setPage(4));
    act(() => result.current.setPageSize(50));
    expect(result.current.pageSize).toBe(50);
    expect(result.current.page).toBe(1);
  });

  it('setFilters updates filters and resets page', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.setFilters({ status: 'active' }));
    expect(result.current.filters).toEqual({ status: 'active' });
    expect(result.current.page).toBe(1);
  });

  it('setSorting updates sortBy and sortOrder', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.setSorting('name', 'asc'));
    expect(result.current.sortBy).toBe('name');
    expect(result.current.sortOrder).toBe('asc');
  });

  it('selectItem toggles selected ids', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.selectItem(5, true));
    expect(result.current.selectedIds).toContain(5);
    act(() => result.current.selectItem(5, false));
    expect(result.current.selectedIds).not.toContain(5);
  });

  it('selectAll selects all item ids from data', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.selectAll(true));
    expect(result.current.selectedIds).toEqual([1, 2]);
    act(() => result.current.selectAll(false));
    expect(result.current.selectedIds).toEqual([]);
  });

  it('resetFilters clears filters and resets page', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.setFilters({ status: 'active' }));
    act(() => result.current.resetFilters());
    expect(result.current.filters).toEqual({});
    expect(result.current.page).toBe(1);
  });

  it('refresh triggers a refetch', () => {
    const { result } = renderHook(() => useSessions());
    act(() => result.current.refresh());
    expect(mockRefetch).toHaveBeenCalled();
  });

  it('create posts to the API', async () => {
    const { result } = renderHook(() => useSessions());
    await act(async () => {
      await result.current.create({ name: 'session-a' });
    });
    expect(mockApiClient.post).toHaveBeenCalledWith('/sessions', { name: 'session-a' });
  });

  it('update puts to the API', async () => {
    const { result } = renderHook(() => useSessions());
    await act(async () => {
      await result.current.update(1, { name: 'session-b' });
    });
    expect(mockApiClient.put).toHaveBeenCalledWith('/sessions/1', { name: 'session-b' });
  });

  it('remove deletes from the API', async () => {
    const { result } = renderHook(() => useSessions());
    await act(async () => {
      await result.current.remove(1);
    });
    expect(mockApiClient.delete).toHaveBeenCalledWith('/sessions/1');
  });
});
