import { describe, it, expect, beforeEach } from 'vitest';
import { useModelPlaygroundStore } from '../model_playgroundStore';

describe('useModelPlaygroundStore', () => {
  beforeEach(() => {
    useModelPlaygroundStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useModelPlaygroundStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useModelPlaygroundStore.getState().setItems(items);
    expect(useModelPlaygroundStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useModelPlaygroundStore.getState().addItem(item);
    expect(useModelPlaygroundStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useModelPlaygroundStore.getState().addItem(item);
    useModelPlaygroundStore.getState().updateItem('1', { name: 'Updated' });
    expect(useModelPlaygroundStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useModelPlaygroundStore.getState().addItem(item);
    useModelPlaygroundStore.getState().removeItem('1');
    expect(useModelPlaygroundStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useModelPlaygroundStore.getState().selectItem('1');
    expect(useModelPlaygroundStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useModelPlaygroundStore.getState().setLoading(true);
    expect(useModelPlaygroundStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useModelPlaygroundStore.getState().setError('Error');
    expect(useModelPlaygroundStore.getState().error).toBe('Error');
  });
});
