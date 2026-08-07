import { describe, it, expect, beforeEach } from 'vitest';
import { useTaskStore } from '../TaskStore';

describe('useTaskStore', () => {
  beforeEach(() => {
    useTaskStore.setState({
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
    const state = useTaskStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTaskStore.getState().setItems(items);
    expect(useTaskStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskStore.getState().addItem(item);
    expect(useTaskStore.getState().items).toHaveLength(1);
    expect(useTaskStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskStore.getState().addItem(item);
    useTaskStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTaskStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskStore.getState().addItem(item);
    useTaskStore.getState().removeItem('1');
    expect(useTaskStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTaskStore.getState().selectItem('1');
    expect(useTaskStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useTaskStore.getState().selectItem('1');
    useTaskStore.getState().selectItem(null);
    expect(useTaskStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useTaskStore.getState().setLoading(true);
    expect(useTaskStore.getState().loading).toBe(true);
    useTaskStore.getState().setLoading(false);
    expect(useTaskStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useTaskStore.getState().setError('Something went wrong');
    expect(useTaskStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useTaskStore.getState().setError('Error');
    useTaskStore.getState().setError(null);
    expect(useTaskStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useTaskStore.getState().setFilters(filters);
    expect(useTaskStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useTaskStore.getState().setPagination({ page: 3 });
    expect(useTaskStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useTaskStore.getState().setPagination({ pageSize: 50 });
    expect(useTaskStore.getState().pagination.pageSize).toBe(50);
    expect(useTaskStore.getState().pagination.page).toBe(1);
  });
});
