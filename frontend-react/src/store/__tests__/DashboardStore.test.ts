import { describe, it, expect, beforeEach } from 'vitest';
import { useDashboardStore } from '../DashboardStore';

describe('useDashboardStore', () => {
  beforeEach(() => {
    useDashboardStore.setState({
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
    const state = useDashboardStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useDashboardStore.getState().setItems(items);
    expect(useDashboardStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDashboardStore.getState().addItem(item);
    expect(useDashboardStore.getState().items).toHaveLength(1);
    expect(useDashboardStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDashboardStore.getState().addItem(item);
    useDashboardStore.getState().updateItem('1', { name: 'Updated' });
    expect(useDashboardStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDashboardStore.getState().addItem(item);
    useDashboardStore.getState().removeItem('1');
    expect(useDashboardStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useDashboardStore.getState().selectItem('1');
    expect(useDashboardStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useDashboardStore.getState().selectItem('1');
    useDashboardStore.getState().selectItem(null);
    expect(useDashboardStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useDashboardStore.getState().setLoading(true);
    expect(useDashboardStore.getState().loading).toBe(true);
    useDashboardStore.getState().setLoading(false);
    expect(useDashboardStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useDashboardStore.getState().setError('Something went wrong');
    expect(useDashboardStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useDashboardStore.getState().setError('Error');
    useDashboardStore.getState().setError(null);
    expect(useDashboardStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useDashboardStore.getState().setFilters(filters);
    expect(useDashboardStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useDashboardStore.getState().setPagination({ page: 3 });
    expect(useDashboardStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useDashboardStore.getState().setPagination({ pageSize: 50 });
    expect(useDashboardStore.getState().pagination.pageSize).toBe(50);
    expect(useDashboardStore.getState().pagination.page).toBe(1);
  });
});
