import { describe, it, expect, beforeEach } from 'vitest';
import { useActivityStore } from '../ActivityStore';

describe('useActivityStore', () => {
  beforeEach(() => {
    useActivityStore.setState({
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
    const state = useActivityStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useActivityStore.getState().setItems(items);
    expect(useActivityStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useActivityStore.getState().addItem(item);
    expect(useActivityStore.getState().items).toContain(item);
  });

  it('updateItem updates an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useActivityStore.getState().addItem(item);
    useActivityStore.getState().updateItem('1', { name: 'Updated' });
    expect(useActivityStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useActivityStore.getState().addItem(item);
    useActivityStore.getState().removeItem('1');
    expect(useActivityStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useActivityStore.getState().selectItem('1');
    expect(useActivityStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useActivityStore.getState().setLoading(true);
    expect(useActivityStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useActivityStore.getState().setError('Error');
    expect(useActivityStore.getState().error).toBe('Error');
  });

  it('setFilters sets filters', () => {
    useActivityStore.getState().setFilters({ status: 'active' });
    expect(useActivityStore.getState().filters).toEqual({ status: 'active' });
  });

  it('setSort sets sort', () => {
    useActivityStore.getState().setSort('name', 'asc');
    expect(useActivityStore.getState().sortBy).toBe('name');
    expect(useActivityStore.getState().sortOrder).toBe('asc');
  });

  it('setPagination sets pagination', () => {
    useActivityStore.getState().setPagination({ page: 2 });
    expect(useActivityStore.getState().pagination.page).toBe(2);
  });

  it('reset resets state', () => {
    useActivityStore.getState().setItems([{ id: '1', name: 'Test', createdAt: '', updatedAt: '' }]);
    useActivityStore.getState().reset();
    expect(useActivityStore.getState().items).toEqual([]);
  });
});
