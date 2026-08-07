import { describe, it, expect, beforeEach } from 'vitest';
import { useModelCatalogStore } from '../model_catalogStore';

describe('useModelCatalogStore', () => {
  beforeEach(() => {
    useModelCatalogStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useModelCatalogStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useModelCatalogStore.getState().setItems(items);
    expect(useModelCatalogStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useModelCatalogStore.getState().addItem(item);
    expect(useModelCatalogStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useModelCatalogStore.getState().addItem(item);
    useModelCatalogStore.getState().updateItem('1', { name: 'Updated' });
    expect(useModelCatalogStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useModelCatalogStore.getState().addItem(item);
    useModelCatalogStore.getState().removeItem('1');
    expect(useModelCatalogStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useModelCatalogStore.getState().selectItem('1');
    expect(useModelCatalogStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useModelCatalogStore.getState().setLoading(true);
    expect(useModelCatalogStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useModelCatalogStore.getState().setError('Error');
    expect(useModelCatalogStore.getState().error).toBe('Error');
  });
});
