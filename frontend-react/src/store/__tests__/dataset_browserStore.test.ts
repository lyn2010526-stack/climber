import { describe, it, expect, beforeEach } from 'vitest';
import { useDatasetBrowserStore } from '../dataset_browserStore';

describe('useDatasetBrowserStore', () => {
  beforeEach(() => {
    useDatasetBrowserStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useDatasetBrowserStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useDatasetBrowserStore.getState().setItems(items);
    expect(useDatasetBrowserStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useDatasetBrowserStore.getState().addItem(item);
    expect(useDatasetBrowserStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useDatasetBrowserStore.getState().addItem(item);
    useDatasetBrowserStore.getState().updateItem('1', { name: 'Updated' });
    expect(useDatasetBrowserStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useDatasetBrowserStore.getState().addItem(item);
    useDatasetBrowserStore.getState().removeItem('1');
    expect(useDatasetBrowserStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useDatasetBrowserStore.getState().selectItem('1');
    expect(useDatasetBrowserStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useDatasetBrowserStore.getState().setLoading(true);
    expect(useDatasetBrowserStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useDatasetBrowserStore.getState().setError('Error');
    expect(useDatasetBrowserStore.getState().error).toBe('Error');
  });
});
