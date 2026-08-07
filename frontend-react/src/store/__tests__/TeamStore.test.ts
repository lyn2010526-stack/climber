import { describe, it, expect, beforeEach } from 'vitest';
import { useTeamStore } from '../TeamStore';

describe('useTeamStore', () => {
  beforeEach(() => {
    useTeamStore.setState({
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
    const state = useTeamStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTeamStore.getState().setItems(items);
    expect(useTeamStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTeamStore.getState().addItem(item);
    expect(useTeamStore.getState().items).toHaveLength(1);
    expect(useTeamStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTeamStore.getState().addItem(item);
    useTeamStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTeamStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTeamStore.getState().addItem(item);
    useTeamStore.getState().removeItem('1');
    expect(useTeamStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTeamStore.getState().selectItem('1');
    expect(useTeamStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useTeamStore.getState().selectItem('1');
    useTeamStore.getState().selectItem(null);
    expect(useTeamStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useTeamStore.getState().setLoading(true);
    expect(useTeamStore.getState().loading).toBe(true);
    useTeamStore.getState().setLoading(false);
    expect(useTeamStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useTeamStore.getState().setError('Something went wrong');
    expect(useTeamStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useTeamStore.getState().setError('Error');
    useTeamStore.getState().setError(null);
    expect(useTeamStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useTeamStore.getState().setFilters(filters);
    expect(useTeamStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useTeamStore.getState().setPagination({ page: 3 });
    expect(useTeamStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useTeamStore.getState().setPagination({ pageSize: 50 });
    expect(useTeamStore.getState().pagination.pageSize).toBe(50);
    expect(useTeamStore.getState().pagination.page).toBe(1);
  });
});
