import { describe, it, expect, beforeEach } from 'vitest';
import { useFolderStore } from '../FolderStore';

describe('useFolderStore', () => {
  beforeEach(() => {
    useFolderStore.setState({
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
    const state = useFolderStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useFolderStore.getState().setItems(items);
    expect(useFolderStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFolderStore.getState().addItem(item);
    expect(useFolderStore.getState().items).toHaveLength(1);
    expect(useFolderStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFolderStore.getState().addItem(item);
    useFolderStore.getState().updateItem('1', { name: 'Updated' });
    expect(useFolderStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useFolderStore.getState().addItem(item);
    useFolderStore.getState().removeItem('1');
    expect(useFolderStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useFolderStore.getState().selectItem('1');
    expect(useFolderStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useFolderStore.getState().selectItem('1');
    useFolderStore.getState().selectItem(null);
    expect(useFolderStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useFolderStore.getState().setLoading(true);
    expect(useFolderStore.getState().loading).toBe(true);
    useFolderStore.getState().setLoading(false);
    expect(useFolderStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useFolderStore.getState().setError('Something went wrong');
    expect(useFolderStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useFolderStore.getState().setError('Error');
    useFolderStore.getState().setError(null);
    expect(useFolderStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useFolderStore.getState().setFilters(filters);
    expect(useFolderStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useFolderStore.getState().setPagination({ page: 3 });
    expect(useFolderStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useFolderStore.getState().setPagination({ pageSize: 50 });
    expect(useFolderStore.getState().pagination.pageSize).toBe(50);
    expect(useFolderStore.getState().pagination.page).toBe(1);
  });
});
