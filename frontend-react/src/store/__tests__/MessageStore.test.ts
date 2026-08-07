import { describe, it, expect, beforeEach } from 'vitest';
import { useMessageStore } from '../MessageStore';

describe('useMessageStore', () => {
  beforeEach(() => {
    useMessageStore.setState({
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
    const state = useMessageStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useMessageStore.getState().setItems(items);
    expect(useMessageStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMessageStore.getState().addItem(item);
    expect(useMessageStore.getState().items).toHaveLength(1);
    expect(useMessageStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMessageStore.getState().addItem(item);
    useMessageStore.getState().updateItem('1', { name: 'Updated' });
    expect(useMessageStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useMessageStore.getState().addItem(item);
    useMessageStore.getState().removeItem('1');
    expect(useMessageStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useMessageStore.getState().selectItem('1');
    expect(useMessageStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useMessageStore.getState().selectItem('1');
    useMessageStore.getState().selectItem(null);
    expect(useMessageStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useMessageStore.getState().setLoading(true);
    expect(useMessageStore.getState().loading).toBe(true);
    useMessageStore.getState().setLoading(false);
    expect(useMessageStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useMessageStore.getState().setError('Something went wrong');
    expect(useMessageStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useMessageStore.getState().setError('Error');
    useMessageStore.getState().setError(null);
    expect(useMessageStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useMessageStore.getState().setFilters(filters);
    expect(useMessageStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useMessageStore.getState().setPagination({ page: 3 });
    expect(useMessageStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useMessageStore.getState().setPagination({ pageSize: 50 });
    expect(useMessageStore.getState().pagination.pageSize).toBe(50);
    expect(useMessageStore.getState().pagination.page).toBe(1);
  });
});
