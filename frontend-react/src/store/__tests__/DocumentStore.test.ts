import { describe, it, expect, beforeEach } from 'vitest';
import { useDocumentStore } from '../DocumentStore';

describe('useDocumentStore', () => {
  beforeEach(() => {
    useDocumentStore.setState({
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
    const state = useDocumentStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useDocumentStore.getState().setItems(items);
    expect(useDocumentStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDocumentStore.getState().addItem(item);
    expect(useDocumentStore.getState().items).toHaveLength(1);
    expect(useDocumentStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDocumentStore.getState().addItem(item);
    useDocumentStore.getState().updateItem('1', { name: 'Updated' });
    expect(useDocumentStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useDocumentStore.getState().addItem(item);
    useDocumentStore.getState().removeItem('1');
    expect(useDocumentStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useDocumentStore.getState().selectItem('1');
    expect(useDocumentStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useDocumentStore.getState().selectItem('1');
    useDocumentStore.getState().selectItem(null);
    expect(useDocumentStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useDocumentStore.getState().setLoading(true);
    expect(useDocumentStore.getState().loading).toBe(true);
    useDocumentStore.getState().setLoading(false);
    expect(useDocumentStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useDocumentStore.getState().setError('Something went wrong');
    expect(useDocumentStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useDocumentStore.getState().setError('Error');
    useDocumentStore.getState().setError(null);
    expect(useDocumentStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useDocumentStore.getState().setFilters(filters);
    expect(useDocumentStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useDocumentStore.getState().setPagination({ page: 3 });
    expect(useDocumentStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useDocumentStore.getState().setPagination({ pageSize: 50 });
    expect(useDocumentStore.getState().pagination.pageSize).toBe(50);
    expect(useDocumentStore.getState().pagination.page).toBe(1);
  });
});
