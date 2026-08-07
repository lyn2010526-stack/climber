import { describe, it, expect, beforeEach } from 'vitest';
import { useFileManagerStore } from '../file_managerStore';

describe('useFileManagerStore', () => {
  beforeEach(() => {
    useFileManagerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useFileManagerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useFileManagerStore.getState().setItems(items);
    expect(useFileManagerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useFileManagerStore.getState().addItem(item);
    expect(useFileManagerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useFileManagerStore.getState().addItem(item);
    useFileManagerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useFileManagerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useFileManagerStore.getState().addItem(item);
    useFileManagerStore.getState().removeItem('1');
    expect(useFileManagerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useFileManagerStore.getState().selectItem('1');
    expect(useFileManagerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useFileManagerStore.getState().setLoading(true);
    expect(useFileManagerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useFileManagerStore.getState().setError('Error');
    expect(useFileManagerStore.getState().error).toBe('Error');
  });
});
