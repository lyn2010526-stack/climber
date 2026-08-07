import { describe, it, expect, beforeEach } from 'vitest';
import { usePluginMarketplaceStore } from '../plugin_marketplaceStore';

describe('usePluginMarketplaceStore', () => {
  beforeEach(() => {
    usePluginMarketplaceStore.setState({
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
    const state = usePluginMarketplaceStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    usePluginMarketplaceStore.getState().setItems(items);
    expect(usePluginMarketplaceStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePluginMarketplaceStore.getState().addItem(item);
    expect(usePluginMarketplaceStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePluginMarketplaceStore.getState().addItem(item);
    usePluginMarketplaceStore.getState().updateItem('1', { name: 'Updated' });
    expect(usePluginMarketplaceStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePluginMarketplaceStore.getState().addItem(item);
    usePluginMarketplaceStore.getState().removeItem('1');
    expect(usePluginMarketplaceStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    usePluginMarketplaceStore.getState().selectItem('1');
    expect(usePluginMarketplaceStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    usePluginMarketplaceStore.getState().setLoading(true);
    expect(usePluginMarketplaceStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    usePluginMarketplaceStore.getState().setError('Error');
    expect(usePluginMarketplaceStore.getState().error).toBe('Error');
  });
});
