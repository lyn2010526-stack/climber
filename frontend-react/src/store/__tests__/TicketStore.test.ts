import { describe, it, expect, beforeEach } from 'vitest';
import { useTicketStore } from '../TicketStore';

describe('useTicketStore', () => {
  beforeEach(() => {
    useTicketStore.setState({
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
    const state = useTicketStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTicketStore.getState().setItems(items);
    expect(useTicketStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTicketStore.getState().addItem(item);
    expect(useTicketStore.getState().items).toHaveLength(1);
    expect(useTicketStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTicketStore.getState().addItem(item);
    useTicketStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTicketStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTicketStore.getState().addItem(item);
    useTicketStore.getState().removeItem('1');
    expect(useTicketStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTicketStore.getState().selectItem('1');
    expect(useTicketStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useTicketStore.getState().selectItem('1');
    useTicketStore.getState().selectItem(null);
    expect(useTicketStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useTicketStore.getState().setLoading(true);
    expect(useTicketStore.getState().loading).toBe(true);
    useTicketStore.getState().setLoading(false);
    expect(useTicketStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useTicketStore.getState().setError('Something went wrong');
    expect(useTicketStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useTicketStore.getState().setError('Error');
    useTicketStore.getState().setError(null);
    expect(useTicketStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useTicketStore.getState().setFilters(filters);
    expect(useTicketStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useTicketStore.getState().setPagination({ page: 3 });
    expect(useTicketStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useTicketStore.getState().setPagination({ pageSize: 50 });
    expect(useTicketStore.getState().pagination.pageSize).toBe(50);
    expect(useTicketStore.getState().pagination.page).toBe(1);
  });
});
