import { describe, it, expect, beforeEach } from 'vitest';
import { useUserAdminStore } from '../user_adminStore';

describe('useUserAdminStore', () => {
  beforeEach(() => {
    useUserAdminStore.setState({
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
    const state = useUserAdminStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useUserAdminStore.getState().setItems(items);
    expect(useUserAdminStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserAdminStore.getState().addItem(item);
    expect(useUserAdminStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserAdminStore.getState().addItem(item);
    useUserAdminStore.getState().updateItem('1', { name: 'Updated' });
    expect(useUserAdminStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useUserAdminStore.getState().addItem(item);
    useUserAdminStore.getState().removeItem('1');
    expect(useUserAdminStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useUserAdminStore.getState().selectItem('1');
    expect(useUserAdminStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useUserAdminStore.getState().setLoading(true);
    expect(useUserAdminStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useUserAdminStore.getState().setError('Error');
    expect(useUserAdminStore.getState().error).toBe('Error');
  });
});
