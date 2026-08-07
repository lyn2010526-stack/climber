import { describe, it, expect, beforeEach } from 'vitest';
import { useCommentStore } from '../CommentStore';

describe('useCommentStore', () => {
  beforeEach(() => {
    useCommentStore.setState({
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
    const state = useCommentStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useCommentStore.getState().setItems(items);
    expect(useCommentStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCommentStore.getState().addItem(item);
    expect(useCommentStore.getState().items).toHaveLength(1);
    expect(useCommentStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCommentStore.getState().addItem(item);
    useCommentStore.getState().updateItem('1', { name: 'Updated' });
    expect(useCommentStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useCommentStore.getState().addItem(item);
    useCommentStore.getState().removeItem('1');
    expect(useCommentStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useCommentStore.getState().selectItem('1');
    expect(useCommentStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useCommentStore.getState().selectItem('1');
    useCommentStore.getState().selectItem(null);
    expect(useCommentStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useCommentStore.getState().setLoading(true);
    expect(useCommentStore.getState().loading).toBe(true);
    useCommentStore.getState().setLoading(false);
    expect(useCommentStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useCommentStore.getState().setError('Something went wrong');
    expect(useCommentStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useCommentStore.getState().setError('Error');
    useCommentStore.getState().setError(null);
    expect(useCommentStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useCommentStore.getState().setFilters(filters);
    expect(useCommentStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useCommentStore.getState().setPagination({ page: 3 });
    expect(useCommentStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useCommentStore.getState().setPagination({ pageSize: 50 });
    expect(useCommentStore.getState().pagination.pageSize).toBe(50);
    expect(useCommentStore.getState().pagination.page).toBe(1);
  });
});
