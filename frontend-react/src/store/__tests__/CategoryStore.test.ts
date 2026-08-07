import { describe, it, expect, beforeEach } from 'vitest';
import { useCategoryStore } from '../CategoryStore';

describe('useCategoryStore', () => {
  beforeEach(() => {
    useCategoryStore.setState({
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
    const state = useCategoryStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useCategoryStore.getState().setItems(items);
    expect(useCategoryStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCategoryStore.getState().addItem(item);
    expect(useCategoryStore.getState().items).toHaveLength(1);
    expect(useCategoryStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCategoryStore.getState().addItem(item);
    useCategoryStore.getState().updateItem('1', { name: 'Updated' });
    expect(useCategoryStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCategoryStore.getState().addItem(item);
    useCategoryStore.getState().removeItem('1');
    expect(useCategoryStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useCategoryStore.getState().selectItem('1');
    expect(useCategoryStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useCategoryStore.getState().selectItem('1');
    useCategoryStore.getState().selectItem(null);
    expect(useCategoryStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useCategoryStore.getState().setLoading(true);
    expect(useCategoryStore.getState().loading).toBe(true);
    useCategoryStore.getState().setLoading(false);
    expect(useCategoryStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useCategoryStore.getState().setError('Something went wrong');
    expect(useCategoryStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useCategoryStore.getState().setError('Error');
    useCategoryStore.getState().setError(null);
    expect(useCategoryStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useCategoryStore.getState().setFilters(filters);
    expect(useCategoryStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useCategoryStore.getState().setPagination({ page: 3 });
    expect(useCategoryStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useCategoryStore.getState().setPagination({ pageSize: 50 });
    expect(useCategoryStore.getState().pagination.pageSize).toBe(50);
    expect(useCategoryStore.getState().pagination.page).toBe(1);
  });
});
