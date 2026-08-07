import { describe, it, expect, beforeEach } from 'vitest';
import { useMetricStore } from '../MetricStore';

describe('useMetricStore', () => {
  beforeEach(() => {
    useMetricStore.setState({
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
    const state = useMetricStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useMetricStore.getState().setItems(items);
    expect(useMetricStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMetricStore.getState().addItem(item);
    expect(useMetricStore.getState().items).toHaveLength(1);
    expect(useMetricStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMetricStore.getState().addItem(item);
    useMetricStore.getState().updateItem('1', { name: 'Updated' });
    expect(useMetricStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMetricStore.getState().addItem(item);
    useMetricStore.getState().removeItem('1');
    expect(useMetricStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useMetricStore.getState().selectItem('1');
    expect(useMetricStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useMetricStore.getState().selectItem('1');
    useMetricStore.getState().selectItem(null);
    expect(useMetricStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useMetricStore.getState().setLoading(true);
    expect(useMetricStore.getState().loading).toBe(true);
    useMetricStore.getState().setLoading(false);
    expect(useMetricStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useMetricStore.getState().setError('Something went wrong');
    expect(useMetricStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useMetricStore.getState().setError('Error');
    useMetricStore.getState().setError(null);
    expect(useMetricStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useMetricStore.getState().setFilters(filters);
    expect(useMetricStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useMetricStore.getState().setPagination({ page: 3 });
    expect(useMetricStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useMetricStore.getState().setPagination({ pageSize: 50 });
    expect(useMetricStore.getState().pagination.pageSize).toBe(50);
    expect(useMetricStore.getState().pagination.page).toBe(1);
  });
});
