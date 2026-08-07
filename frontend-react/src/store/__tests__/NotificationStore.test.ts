import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationStore } from '../NotificationStore';

describe('useNotificationStore', () => {
  beforeEach(() => {
    useNotificationStore.setState({
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
    const state = useNotificationStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useNotificationStore.getState().setItems(items);
    expect(useNotificationStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationStore.getState().addItem(item);
    expect(useNotificationStore.getState().items).toHaveLength(1);
    expect(useNotificationStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationStore.getState().addItem(item);
    useNotificationStore.getState().updateItem('1', { name: 'Updated' });
    expect(useNotificationStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationStore.getState().addItem(item);
    useNotificationStore.getState().removeItem('1');
    expect(useNotificationStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useNotificationStore.getState().selectItem('1');
    expect(useNotificationStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useNotificationStore.getState().selectItem('1');
    useNotificationStore.getState().selectItem(null);
    expect(useNotificationStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useNotificationStore.getState().setLoading(true);
    expect(useNotificationStore.getState().loading).toBe(true);
    useNotificationStore.getState().setLoading(false);
    expect(useNotificationStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useNotificationStore.getState().setError('Something went wrong');
    expect(useNotificationStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useNotificationStore.getState().setError('Error');
    useNotificationStore.getState().setError(null);
    expect(useNotificationStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useNotificationStore.getState().setFilters(filters);
    expect(useNotificationStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useNotificationStore.getState().setPagination({ page: 3 });
    expect(useNotificationStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useNotificationStore.getState().setPagination({ pageSize: 50 });
    expect(useNotificationStore.getState().pagination.pageSize).toBe(50);
    expect(useNotificationStore.getState().pagination.page).toBe(1);
  });
});
