import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionHistoryStore } from '../session_historyStore';

describe('useSessionHistoryStore', () => {
  beforeEach(() => {
    useSessionHistoryStore.setState({
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
    const state = useSessionHistoryStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSessionHistoryStore.getState().setItems(items);
    expect(useSessionHistoryStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSessionHistoryStore.getState().addItem(item);
    expect(useSessionHistoryStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSessionHistoryStore.getState().addItem(item);
    useSessionHistoryStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSessionHistoryStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSessionHistoryStore.getState().addItem(item);
    useSessionHistoryStore.getState().removeItem('1');
    expect(useSessionHistoryStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSessionHistoryStore.getState().selectItem('1');
    expect(useSessionHistoryStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useSessionHistoryStore.getState().setLoading(true);
    expect(useSessionHistoryStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useSessionHistoryStore.getState().setError('Error');
    expect(useSessionHistoryStore.getState().error).toBe('Error');
  });
});
