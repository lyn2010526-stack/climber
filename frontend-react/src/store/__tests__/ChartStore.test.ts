import { describe, it, expect, beforeEach } from 'vitest';
import { useChartStore } from '../ChartStore';

describe('useChartStore', () => {
  beforeEach(() => {
    useChartStore.setState({
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
    const state = useChartStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useChartStore.getState().setItems(items);
    expect(useChartStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useChartStore.getState().addItem(item);
    expect(useChartStore.getState().items).toHaveLength(1);
    expect(useChartStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useChartStore.getState().addItem(item);
    useChartStore.getState().updateItem('1', { name: 'Updated' });
    expect(useChartStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useChartStore.getState().addItem(item);
    useChartStore.getState().removeItem('1');
    expect(useChartStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useChartStore.getState().selectItem('1');
    expect(useChartStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useChartStore.getState().selectItem('1');
    useChartStore.getState().selectItem(null);
    expect(useChartStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useChartStore.getState().setLoading(true);
    expect(useChartStore.getState().loading).toBe(true);
    useChartStore.getState().setLoading(false);
    expect(useChartStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useChartStore.getState().setError('Something went wrong');
    expect(useChartStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useChartStore.getState().setError('Error');
    useChartStore.getState().setError(null);
    expect(useChartStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useChartStore.getState().setFilters(filters);
    expect(useChartStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useChartStore.getState().setPagination({ page: 3 });
    expect(useChartStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useChartStore.getState().setPagination({ pageSize: 50 });
    expect(useChartStore.getState().pagination.pageSize).toBe(50);
    expect(useChartStore.getState().pagination.page).toBe(1);
  });
});
