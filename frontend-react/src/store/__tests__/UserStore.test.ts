import { describe, it, expect, beforeEach } from 'vitest';
import { useUserStore } from '../UserStore';

describe('useUserStore', () => {
  beforeEach(() => {
    useUserStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
      sortBy: 'createdAt',
      sortOrder: 'desc',
      pagination: { page: 1, pageSize: 20, total: 0 },
    });
  });

  it('has initial state', () => {
    const state = useUserStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useUserStore.getState().setItems(items);
    expect(useUserStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserStore.getState().addItem(item);
    expect(useUserStore.getState().items).toHaveLength(1);
    expect(useUserStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserStore.getState().addItem(item);
    useUserStore.getState().updateItem('1', { name: 'Updated' });
    expect(useUserStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserStore.getState().addItem(item);
    useUserStore.getState().removeItem('1');
    expect(useUserStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useUserStore.getState().selectItem('1');
    expect(useUserStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useUserStore.getState().selectItem('1');
    useUserStore.getState().selectItem(null);
    expect(useUserStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useUserStore.getState().setLoading(true);
    expect(useUserStore.getState().loading).toBe(true);
    useUserStore.getState().setLoading(false);
    expect(useUserStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useUserStore.getState().setError('Something went wrong');
    expect(useUserStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useUserStore.getState().setError('Error');
    useUserStore.getState().setError(null);
    expect(useUserStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useUserStore.getState().setFilters(filters);
    expect(useUserStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useUserStore.getState().setPagination({ page: 3 });
    expect(useUserStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useUserStore.getState().setPagination({ pageSize: 50 });
    expect(useUserStore.getState().pagination.pageSize).toBe(50);
    expect(useUserStore.getState().pagination.page).toBe(1);
  });
});
