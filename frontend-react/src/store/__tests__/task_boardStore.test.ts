import { describe, it, expect, beforeEach } from 'vitest';
import { useTaskBoardStore } from '../task_boardStore';

describe('useTaskBoardStore', () => {
  beforeEach(() => {
    useTaskBoardStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
            filter: {
        search: '',
        status: null,
        sortBy: 'createdAt',
        sortOrder: 'desc',
        page: 1,
        pageSize: 10,
      },
    });
  });

  it('has initial state', () => {
    const state = useTaskBoardStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTaskBoardStore.getState().setItems(items);
    expect(useTaskBoardStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskBoardStore.getState().addItem(item);
    expect(useTaskBoardStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskBoardStore.getState().addItem(item);
    useTaskBoardStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTaskBoardStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTaskBoardStore.getState().addItem(item);
    useTaskBoardStore.getState().removeItem('1');
    expect(useTaskBoardStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTaskBoardStore.getState().selectItem('1');
    expect(useTaskBoardStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useTaskBoardStore.getState().setLoading(true);
    expect(useTaskBoardStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useTaskBoardStore.getState().setError('Error');
    expect(useTaskBoardStore.getState().error).toBe('Error');
  });
});
