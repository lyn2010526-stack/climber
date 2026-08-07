import { describe, it, expect, beforeEach } from 'vitest';
import { useTenantAdminStore } from '../tenant_adminStore';

describe('useTenantAdminStore', () => {
  beforeEach(() => {
    useTenantAdminStore.setState({
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
    const state = useTenantAdminStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTenantAdminStore.getState().setItems(items);
    expect(useTenantAdminStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTenantAdminStore.getState().addItem(item);
    expect(useTenantAdminStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTenantAdminStore.getState().addItem(item);
    useTenantAdminStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTenantAdminStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTenantAdminStore.getState().addItem(item);
    useTenantAdminStore.getState().removeItem('1');
    expect(useTenantAdminStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTenantAdminStore.getState().selectItem('1');
    expect(useTenantAdminStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useTenantAdminStore.getState().setLoading(true);
    expect(useTenantAdminStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useTenantAdminStore.getState().setError('Error');
    expect(useTenantAdminStore.getState().error).toBe('Error');
  });
});
