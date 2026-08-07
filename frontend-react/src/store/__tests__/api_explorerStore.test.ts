import { describe, it, expect, beforeEach } from 'vitest';
import { useApiExplorerStore } from '../api_explorerStore';

describe('useApiExplorerStore', () => {
  beforeEach(() => {
    useApiExplorerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useApiExplorerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useApiExplorerStore.getState().setItems(items);
    expect(useApiExplorerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useApiExplorerStore.getState().addItem(item);
    expect(useApiExplorerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useApiExplorerStore.getState().addItem(item);
    useApiExplorerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useApiExplorerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useApiExplorerStore.getState().addItem(item);
    useApiExplorerStore.getState().removeItem('1');
    expect(useApiExplorerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useApiExplorerStore.getState().selectItem('1');
    expect(useApiExplorerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useApiExplorerStore.getState().setLoading(true);
    expect(useApiExplorerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useApiExplorerStore.getState().setError('Error');
    expect(useApiExplorerStore.getState().error).toBe('Error');
  });
});
