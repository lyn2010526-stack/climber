import { describe, it, expect, beforeEach } from 'vitest';
import { useDeploymentCenterStore } from '../deployment_centerStore';

describe('useDeploymentCenterStore', () => {
  beforeEach(() => {
    useDeploymentCenterStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useDeploymentCenterStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useDeploymentCenterStore.getState().setItems(items);
    expect(useDeploymentCenterStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useDeploymentCenterStore.getState().addItem(item);
    expect(useDeploymentCenterStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useDeploymentCenterStore.getState().addItem(item);
    useDeploymentCenterStore.getState().updateItem('1', { name: 'Updated' });
    expect(useDeploymentCenterStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useDeploymentCenterStore.getState().addItem(item);
    useDeploymentCenterStore.getState().removeItem('1');
    expect(useDeploymentCenterStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useDeploymentCenterStore.getState().selectItem('1');
    expect(useDeploymentCenterStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useDeploymentCenterStore.getState().setLoading(true);
    expect(useDeploymentCenterStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useDeploymentCenterStore.getState().setError('Error');
    expect(useDeploymentCenterStore.getState().error).toBe('Error');
  });
});
