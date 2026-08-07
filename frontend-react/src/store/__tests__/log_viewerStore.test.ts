import { describe, it, expect, beforeEach } from 'vitest';
import { useLogViewerStore } from '../log_viewerStore';

describe('useLogViewerStore', () => {
  beforeEach(() => {
    useLogViewerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useLogViewerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useLogViewerStore.getState().setItems(items);
    expect(useLogViewerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useLogViewerStore.getState().addItem(item);
    expect(useLogViewerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useLogViewerStore.getState().addItem(item);
    useLogViewerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useLogViewerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useLogViewerStore.getState().addItem(item);
    useLogViewerStore.getState().removeItem('1');
    expect(useLogViewerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useLogViewerStore.getState().selectItem('1');
    expect(useLogViewerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useLogViewerStore.getState().setLoading(true);
    expect(useLogViewerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useLogViewerStore.getState().setError('Error');
    expect(useLogViewerStore.getState().error).toBe('Error');
  });
});
