import { describe, it, expect, beforeEach } from 'vitest';
import { useAlertStore } from '../AlertStore';

describe('useAlertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({
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
    const state = useAlertStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useAlertStore.getState().setItems(items);
    expect(useAlertStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAlertStore.getState().addItem(item);
    expect(useAlertStore.getState().items).toHaveLength(1);
    expect(useAlertStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAlertStore.getState().addItem(item);
    useAlertStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAlertStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAlertStore.getState().addItem(item);
    useAlertStore.getState().removeItem('1');
    expect(useAlertStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAlertStore.getState().selectItem('1');
    expect(useAlertStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useAlertStore.getState().selectItem('1');
    useAlertStore.getState().selectItem(null);
    expect(useAlertStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useAlertStore.getState().setLoading(true);
    expect(useAlertStore.getState().loading).toBe(true);
    useAlertStore.getState().setLoading(false);
    expect(useAlertStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useAlertStore.getState().setError('Something went wrong');
    expect(useAlertStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useAlertStore.getState().setError('Error');
    useAlertStore.getState().setError(null);
    expect(useAlertStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useAlertStore.getState().setFilters(filters);
    expect(useAlertStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useAlertStore.getState().setPagination({ page: 3 });
    expect(useAlertStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useAlertStore.getState().setPagination({ pageSize: 50 });
    expect(useAlertStore.getState().pagination.pageSize).toBe(50);
    expect(useAlertStore.getState().pagination.page).toBe(1);
  });
});
