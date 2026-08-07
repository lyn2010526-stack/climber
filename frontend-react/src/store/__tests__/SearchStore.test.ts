import { describe, it, expect, beforeEach } from 'vitest';
import { useSearchStore } from '../SearchStore';

describe('useSearchStore', () => {
  beforeEach(() => {
    useSearchStore.setState({
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
    const state = useSearchStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSearchStore.getState().setItems(items);
    expect(useSearchStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchStore.getState().addItem(item);
    expect(useSearchStore.getState().items).toHaveLength(1);
    expect(useSearchStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchStore.getState().addItem(item);
    useSearchStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSearchStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchStore.getState().addItem(item);
    useSearchStore.getState().removeItem('1');
    expect(useSearchStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSearchStore.getState().selectItem('1');
    expect(useSearchStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useSearchStore.getState().selectItem('1');
    useSearchStore.getState().selectItem(null);
    expect(useSearchStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useSearchStore.getState().setLoading(true);
    expect(useSearchStore.getState().loading).toBe(true);
    useSearchStore.getState().setLoading(false);
    expect(useSearchStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useSearchStore.getState().setError('Something went wrong');
    expect(useSearchStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useSearchStore.getState().setError('Error');
    useSearchStore.getState().setError(null);
    expect(useSearchStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useSearchStore.getState().setFilters(filters);
    expect(useSearchStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useSearchStore.getState().setPagination({ page: 3 });
    expect(useSearchStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useSearchStore.getState().setPagination({ pageSize: 50 });
    expect(useSearchStore.getState().pagination.pageSize).toBe(50);
    expect(useSearchStore.getState().pagination.page).toBe(1);
  });
});
