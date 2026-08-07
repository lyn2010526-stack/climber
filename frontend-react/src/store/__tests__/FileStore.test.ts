import { describe, it, expect, beforeEach } from 'vitest';
import { useFileStore } from '../FileStore';

describe('useFileStore', () => {
  beforeEach(() => {
    useFileStore.setState({
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
    const state = useFileStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useFileStore.getState().setItems(items);
    expect(useFileStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFileStore.getState().addItem(item);
    expect(useFileStore.getState().items).toHaveLength(1);
    expect(useFileStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFileStore.getState().addItem(item);
    useFileStore.getState().updateItem('1', { name: 'Updated' });
    expect(useFileStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFileStore.getState().addItem(item);
    useFileStore.getState().removeItem('1');
    expect(useFileStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useFileStore.getState().selectItem('1');
    expect(useFileStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useFileStore.getState().selectItem('1');
    useFileStore.getState().selectItem(null);
    expect(useFileStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useFileStore.getState().setLoading(true);
    expect(useFileStore.getState().loading).toBe(true);
    useFileStore.getState().setLoading(false);
    expect(useFileStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useFileStore.getState().setError('Something went wrong');
    expect(useFileStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useFileStore.getState().setError('Error');
    useFileStore.getState().setError(null);
    expect(useFileStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useFileStore.getState().setFilters(filters);
    expect(useFileStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useFileStore.getState().setPagination({ page: 3 });
    expect(useFileStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useFileStore.getState().setPagination({ pageSize: 50 });
    expect(useFileStore.getState().pagination.pageSize).toBe(50);
    expect(useFileStore.getState().pagination.page).toBe(1);
  });
});
