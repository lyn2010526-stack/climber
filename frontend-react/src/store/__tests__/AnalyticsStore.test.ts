import { describe, it, expect, beforeEach } from 'vitest';
import { useAnalyticsStore } from '../AnalyticsStore';

describe('useAnalyticsStore', () => {
  beforeEach(() => {
    useAnalyticsStore.setState({
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
    const state = useAnalyticsStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useAnalyticsStore.getState().setItems(items);
    expect(useAnalyticsStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAnalyticsStore.getState().addItem(item);
    expect(useAnalyticsStore.getState().items).toHaveLength(1);
    expect(useAnalyticsStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAnalyticsStore.getState().addItem(item);
    useAnalyticsStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAnalyticsStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAnalyticsStore.getState().addItem(item);
    useAnalyticsStore.getState().removeItem('1');
    expect(useAnalyticsStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAnalyticsStore.getState().selectItem('1');
    expect(useAnalyticsStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useAnalyticsStore.getState().selectItem('1');
    useAnalyticsStore.getState().selectItem(null);
    expect(useAnalyticsStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useAnalyticsStore.getState().setLoading(true);
    expect(useAnalyticsStore.getState().loading).toBe(true);
    useAnalyticsStore.getState().setLoading(false);
    expect(useAnalyticsStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useAnalyticsStore.getState().setError('Something went wrong');
    expect(useAnalyticsStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useAnalyticsStore.getState().setError('Error');
    useAnalyticsStore.getState().setError(null);
    expect(useAnalyticsStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useAnalyticsStore.getState().setFilters(filters);
    expect(useAnalyticsStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useAnalyticsStore.getState().setPagination({ page: 3 });
    expect(useAnalyticsStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useAnalyticsStore.getState().setPagination({ pageSize: 50 });
    expect(useAnalyticsStore.getState().pagination.pageSize).toBe(50);
    expect(useAnalyticsStore.getState().pagination.page).toBe(1);
  });
});
