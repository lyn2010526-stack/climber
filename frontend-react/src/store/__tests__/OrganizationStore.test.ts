import { describe, it, expect, beforeEach } from 'vitest';
import { useOrganizationStore } from '../OrganizationStore';

describe('useOrganizationStore', () => {
  beforeEach(() => {
    useOrganizationStore.setState({
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
    const state = useOrganizationStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useOrganizationStore.getState().setItems(items);
    expect(useOrganizationStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useOrganizationStore.getState().addItem(item);
    expect(useOrganizationStore.getState().items).toHaveLength(1);
    expect(useOrganizationStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useOrganizationStore.getState().addItem(item);
    useOrganizationStore.getState().updateItem('1', { name: 'Updated' });
    expect(useOrganizationStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useOrganizationStore.getState().addItem(item);
    useOrganizationStore.getState().removeItem('1');
    expect(useOrganizationStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useOrganizationStore.getState().selectItem('1');
    expect(useOrganizationStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useOrganizationStore.getState().selectItem('1');
    useOrganizationStore.getState().selectItem(null);
    expect(useOrganizationStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useOrganizationStore.getState().setLoading(true);
    expect(useOrganizationStore.getState().loading).toBe(true);
    useOrganizationStore.getState().setLoading(false);
    expect(useOrganizationStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useOrganizationStore.getState().setError('Something went wrong');
    expect(useOrganizationStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useOrganizationStore.getState().setError('Error');
    useOrganizationStore.getState().setError(null);
    expect(useOrganizationStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useOrganizationStore.getState().setFilters(filters);
    expect(useOrganizationStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useOrganizationStore.getState().setPagination({ page: 3 });
    expect(useOrganizationStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useOrganizationStore.getState().setPagination({ pageSize: 50 });
    expect(useOrganizationStore.getState().pagination.pageSize).toBe(50);
    expect(useOrganizationStore.getState().pagination.page).toBe(1);
  });
});
