import { describe, it, expect, beforeEach } from 'vitest';
import { useWidgetStore } from '../WidgetStore';

describe('useWidgetStore', () => {
  beforeEach(() => {
    useWidgetStore.setState({
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
    const state = useWidgetStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useWidgetStore.getState().setItems(items);
    expect(useWidgetStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWidgetStore.getState().addItem(item);
    expect(useWidgetStore.getState().items).toHaveLength(1);
    expect(useWidgetStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWidgetStore.getState().addItem(item);
    useWidgetStore.getState().updateItem('1', { name: 'Updated' });
    expect(useWidgetStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWidgetStore.getState().addItem(item);
    useWidgetStore.getState().removeItem('1');
    expect(useWidgetStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useWidgetStore.getState().selectItem('1');
    expect(useWidgetStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useWidgetStore.getState().selectItem('1');
    useWidgetStore.getState().selectItem(null);
    expect(useWidgetStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useWidgetStore.getState().setLoading(true);
    expect(useWidgetStore.getState().loading).toBe(true);
    useWidgetStore.getState().setLoading(false);
    expect(useWidgetStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useWidgetStore.getState().setError('Something went wrong');
    expect(useWidgetStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useWidgetStore.getState().setError('Error');
    useWidgetStore.getState().setError(null);
    expect(useWidgetStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useWidgetStore.getState().setFilters(filters);
    expect(useWidgetStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useWidgetStore.getState().setPagination({ page: 3 });
    expect(useWidgetStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useWidgetStore.getState().setPagination({ pageSize: 50 });
    expect(useWidgetStore.getState().pagination.pageSize).toBe(50);
    expect(useWidgetStore.getState().pagination.page).toBe(1);
  });
});
