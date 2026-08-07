import { describe, it, expect, beforeEach } from 'vitest';
import { useIncidentStore } from '../IncidentStore';

describe('useIncidentStore', () => {
  beforeEach(() => {
    useIncidentStore.setState({
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
    const state = useIncidentStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useIncidentStore.getState().setItems(items);
    expect(useIncidentStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useIncidentStore.getState().addItem(item);
    expect(useIncidentStore.getState().items).toHaveLength(1);
    expect(useIncidentStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useIncidentStore.getState().addItem(item);
    useIncidentStore.getState().updateItem('1', { name: 'Updated' });
    expect(useIncidentStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useIncidentStore.getState().addItem(item);
    useIncidentStore.getState().removeItem('1');
    expect(useIncidentStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useIncidentStore.getState().selectItem('1');
    expect(useIncidentStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useIncidentStore.getState().selectItem('1');
    useIncidentStore.getState().selectItem(null);
    expect(useIncidentStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useIncidentStore.getState().setLoading(true);
    expect(useIncidentStore.getState().loading).toBe(true);
    useIncidentStore.getState().setLoading(false);
    expect(useIncidentStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useIncidentStore.getState().setError('Something went wrong');
    expect(useIncidentStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useIncidentStore.getState().setError('Error');
    useIncidentStore.getState().setError(null);
    expect(useIncidentStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useIncidentStore.getState().setFilters(filters);
    expect(useIncidentStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useIncidentStore.getState().setPagination({ page: 3 });
    expect(useIncidentStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useIncidentStore.getState().setPagination({ pageSize: 50 });
    expect(useIncidentStore.getState().pagination.pageSize).toBe(50);
    expect(useIncidentStore.getState().pagination.page).toBe(1);
  });
});
