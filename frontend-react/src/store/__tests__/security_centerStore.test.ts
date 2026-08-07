import { describe, it, expect, beforeEach } from 'vitest';
import { useSecurityCenterStore } from '../security_centerStore';

describe('useSecurityCenterStore', () => {
  beforeEach(() => {
    useSecurityCenterStore.setState({
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
    const state = useSecurityCenterStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSecurityCenterStore.getState().setItems(items);
    expect(useSecurityCenterStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSecurityCenterStore.getState().addItem(item);
    expect(useSecurityCenterStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSecurityCenterStore.getState().addItem(item);
    useSecurityCenterStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSecurityCenterStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSecurityCenterStore.getState().addItem(item);
    useSecurityCenterStore.getState().removeItem('1');
    expect(useSecurityCenterStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSecurityCenterStore.getState().selectItem('1');
    expect(useSecurityCenterStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useSecurityCenterStore.getState().setLoading(true);
    expect(useSecurityCenterStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useSecurityCenterStore.getState().setError('Error');
    expect(useSecurityCenterStore.getState().error).toBe('Error');
  });
});
