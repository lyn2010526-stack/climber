import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from '../WorkspaceStore';

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
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
    const state = useWorkspaceStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useWorkspaceStore.getState().setItems(items);
    expect(useWorkspaceStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkspaceStore.getState().addItem(item);
    expect(useWorkspaceStore.getState().items).toHaveLength(1);
    expect(useWorkspaceStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkspaceStore.getState().addItem(item);
    useWorkspaceStore.getState().updateItem('1', { name: 'Updated' });
    expect(useWorkspaceStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkspaceStore.getState().addItem(item);
    useWorkspaceStore.getState().removeItem('1');
    expect(useWorkspaceStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useWorkspaceStore.getState().selectItem('1');
    expect(useWorkspaceStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useWorkspaceStore.getState().selectItem('1');
    useWorkspaceStore.getState().selectItem(null);
    expect(useWorkspaceStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useWorkspaceStore.getState().setLoading(true);
    expect(useWorkspaceStore.getState().loading).toBe(true);
    useWorkspaceStore.getState().setLoading(false);
    expect(useWorkspaceStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useWorkspaceStore.getState().setError('Something went wrong');
    expect(useWorkspaceStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useWorkspaceStore.getState().setError('Error');
    useWorkspaceStore.getState().setError(null);
    expect(useWorkspaceStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useWorkspaceStore.getState().setFilters(filters);
    expect(useWorkspaceStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useWorkspaceStore.getState().setPagination({ page: 3 });
    expect(useWorkspaceStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useWorkspaceStore.getState().setPagination({ pageSize: 50 });
    expect(useWorkspaceStore.getState().pagination.pageSize).toBe(50);
    expect(useWorkspaceStore.getState().pagination.page).toBe(1);
  });
});
