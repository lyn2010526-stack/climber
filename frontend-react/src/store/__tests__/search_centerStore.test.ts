import { describe, it, expect, beforeEach } from 'vitest';
import { useSearchCenterStore } from '../search_centerStore';

describe('useSearchCenterStore', () => {
  beforeEach(() => {
    useSearchCenterStore.setState({
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
    const state = useSearchCenterStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSearchCenterStore.getState().setItems(items);
    expect(useSearchCenterStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchCenterStore.getState().addItem(item);
    expect(useSearchCenterStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchCenterStore.getState().addItem(item);
    useSearchCenterStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSearchCenterStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSearchCenterStore.getState().addItem(item);
    useSearchCenterStore.getState().removeItem('1');
    expect(useSearchCenterStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSearchCenterStore.getState().selectItem('1');
    expect(useSearchCenterStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useSearchCenterStore.getState().setLoading(true);
    expect(useSearchCenterStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useSearchCenterStore.getState().setError('Error');
    expect(useSearchCenterStore.getState().error).toBe('Error');
  });
});
