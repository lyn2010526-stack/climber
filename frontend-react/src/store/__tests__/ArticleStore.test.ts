import { describe, it, expect, beforeEach } from 'vitest';
import { useArticleStore } from '../ArticleStore';

describe('useArticleStore', () => {
  beforeEach(() => {
    useArticleStore.setState({
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
    const state = useArticleStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useArticleStore.getState().setItems(items);
    expect(useArticleStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useArticleStore.getState().addItem(item);
    expect(useArticleStore.getState().items).toHaveLength(1);
    expect(useArticleStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useArticleStore.getState().addItem(item);
    useArticleStore.getState().updateItem('1', { name: 'Updated' });
    expect(useArticleStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useArticleStore.getState().addItem(item);
    useArticleStore.getState().removeItem('1');
    expect(useArticleStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useArticleStore.getState().selectItem('1');
    expect(useArticleStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useArticleStore.getState().selectItem('1');
    useArticleStore.getState().selectItem(null);
    expect(useArticleStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useArticleStore.getState().setLoading(true);
    expect(useArticleStore.getState().loading).toBe(true);
    useArticleStore.getState().setLoading(false);
    expect(useArticleStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useArticleStore.getState().setError('Something went wrong');
    expect(useArticleStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useArticleStore.getState().setError('Error');
    useArticleStore.getState().setError(null);
    expect(useArticleStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useArticleStore.getState().setFilters(filters);
    expect(useArticleStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useArticleStore.getState().setPagination({ page: 3 });
    expect(useArticleStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useArticleStore.getState().setPagination({ pageSize: 50 });
    expect(useArticleStore.getState().pagination.pageSize).toBe(50);
    expect(useArticleStore.getState().pagination.page).toBe(1);
  });
});
