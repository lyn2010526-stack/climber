import { describe, it, expect, beforeEach } from 'vitest';
import { useTagStore } from '../TagStore';

describe('useTagStore', () => {
  beforeEach(() => {
    useTagStore.setState({
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
    const state = useTagStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTagStore.getState().setItems(items);
    expect(useTagStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTagStore.getState().addItem(item);
    expect(useTagStore.getState().items).toHaveLength(1);
    expect(useTagStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTagStore.getState().addItem(item);
    useTagStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTagStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTagStore.getState().addItem(item);
    useTagStore.getState().removeItem('1');
    expect(useTagStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTagStore.getState().selectItem('1');
    expect(useTagStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useTagStore.getState().selectItem('1');
    useTagStore.getState().selectItem(null);
    expect(useTagStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useTagStore.getState().setLoading(true);
    expect(useTagStore.getState().loading).toBe(true);
    useTagStore.getState().setLoading(false);
    expect(useTagStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useTagStore.getState().setError('Something went wrong');
    expect(useTagStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useTagStore.getState().setError('Error');
    useTagStore.getState().setError(null);
    expect(useTagStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useTagStore.getState().setFilters(filters);
    expect(useTagStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useTagStore.getState().setPagination({ page: 3 });
    expect(useTagStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useTagStore.getState().setPagination({ pageSize: 50 });
    expect(useTagStore.getState().pagination.pageSize).toBe(50);
    expect(useTagStore.getState().pagination.page).toBe(1);
  });
});
