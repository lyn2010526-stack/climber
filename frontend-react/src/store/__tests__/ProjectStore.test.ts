import { describe, it, expect, beforeEach } from 'vitest';
import { useProjectStore } from '../ProjectStore';

describe('useProjectStore', () => {
  beforeEach(() => {
    useProjectStore.setState({
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
    const state = useProjectStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useProjectStore.getState().setItems(items);
    expect(useProjectStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useProjectStore.getState().addItem(item);
    expect(useProjectStore.getState().items).toHaveLength(1);
    expect(useProjectStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useProjectStore.getState().addItem(item);
    useProjectStore.getState().updateItem('1', { name: 'Updated' });
    expect(useProjectStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useProjectStore.getState().addItem(item);
    useProjectStore.getState().removeItem('1');
    expect(useProjectStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useProjectStore.getState().selectItem('1');
    expect(useProjectStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useProjectStore.getState().selectItem('1');
    useProjectStore.getState().selectItem(null);
    expect(useProjectStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useProjectStore.getState().setLoading(true);
    expect(useProjectStore.getState().loading).toBe(true);
    useProjectStore.getState().setLoading(false);
    expect(useProjectStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useProjectStore.getState().setError('Something went wrong');
    expect(useProjectStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useProjectStore.getState().setError('Error');
    useProjectStore.getState().setError(null);
    expect(useProjectStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useProjectStore.getState().setFilters(filters);
    expect(useProjectStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useProjectStore.getState().setPagination({ page: 3 });
    expect(useProjectStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useProjectStore.getState().setPagination({ pageSize: 50 });
    expect(useProjectStore.getState().pagination.pageSize).toBe(50);
    expect(useProjectStore.getState().pagination.page).toBe(1);
  });
});
