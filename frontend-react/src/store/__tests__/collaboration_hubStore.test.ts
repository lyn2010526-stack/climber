import { describe, it, expect, beforeEach } from 'vitest';
import { useCollaborationHubStore } from '../collaboration_hubStore';

describe('useCollaborationHubStore', () => {
  beforeEach(() => {
    useCollaborationHubStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useCollaborationHubStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useCollaborationHubStore.getState().setItems(items);
    expect(useCollaborationHubStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useCollaborationHubStore.getState().addItem(item);
    expect(useCollaborationHubStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useCollaborationHubStore.getState().addItem(item);
    useCollaborationHubStore.getState().updateItem('1', { name: 'Updated' });
    expect(useCollaborationHubStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useCollaborationHubStore.getState().addItem(item);
    useCollaborationHubStore.getState().removeItem('1');
    expect(useCollaborationHubStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useCollaborationHubStore.getState().selectItem('1');
    expect(useCollaborationHubStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useCollaborationHubStore.getState().setLoading(true);
    expect(useCollaborationHubStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useCollaborationHubStore.getState().setError('Error');
    expect(useCollaborationHubStore.getState().error).toBe('Error');
  });
});
