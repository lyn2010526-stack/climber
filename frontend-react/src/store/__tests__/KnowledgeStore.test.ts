import { describe, it, expect, beforeEach } from 'vitest';
import { useKnowledgeStore } from '../KnowledgeStore';

describe('useKnowledgeStore', () => {
  beforeEach(() => {
    useKnowledgeStore.setState({
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
    const state = useKnowledgeStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useKnowledgeStore.getState().setItems(items);
    expect(useKnowledgeStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useKnowledgeStore.getState().addItem(item);
    expect(useKnowledgeStore.getState().items).toHaveLength(1);
    expect(useKnowledgeStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useKnowledgeStore.getState().addItem(item);
    useKnowledgeStore.getState().updateItem('1', { name: 'Updated' });
    expect(useKnowledgeStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useKnowledgeStore.getState().addItem(item);
    useKnowledgeStore.getState().removeItem('1');
    expect(useKnowledgeStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useKnowledgeStore.getState().selectItem('1');
    expect(useKnowledgeStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useKnowledgeStore.getState().selectItem('1');
    useKnowledgeStore.getState().selectItem(null);
    expect(useKnowledgeStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useKnowledgeStore.getState().setLoading(true);
    expect(useKnowledgeStore.getState().loading).toBe(true);
    useKnowledgeStore.getState().setLoading(false);
    expect(useKnowledgeStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useKnowledgeStore.getState().setError('Something went wrong');
    expect(useKnowledgeStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useKnowledgeStore.getState().setError('Error');
    useKnowledgeStore.getState().setError(null);
    expect(useKnowledgeStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useKnowledgeStore.getState().setFilters(filters);
    expect(useKnowledgeStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useKnowledgeStore.getState().setPagination({ page: 3 });
    expect(useKnowledgeStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useKnowledgeStore.getState().setPagination({ pageSize: 50 });
    expect(useKnowledgeStore.getState().pagination.pageSize).toBe(50);
    expect(useKnowledgeStore.getState().pagination.page).toBe(1);
  });
});
