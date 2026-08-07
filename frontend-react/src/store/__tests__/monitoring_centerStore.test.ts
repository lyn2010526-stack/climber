import { describe, it, expect, beforeEach } from 'vitest';
import { useMonitoringCenterStore } from '../monitoring_centerStore';

describe('useMonitoringCenterStore', () => {
  beforeEach(() => {
    useMonitoringCenterStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useMonitoringCenterStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useMonitoringCenterStore.getState().setItems(items);
    expect(useMonitoringCenterStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useMonitoringCenterStore.getState().addItem(item);
    expect(useMonitoringCenterStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useMonitoringCenterStore.getState().addItem(item);
    useMonitoringCenterStore.getState().updateItem('1', { name: 'Updated' });
    expect(useMonitoringCenterStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useMonitoringCenterStore.getState().addItem(item);
    useMonitoringCenterStore.getState().removeItem('1');
    expect(useMonitoringCenterStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useMonitoringCenterStore.getState().selectItem('1');
    expect(useMonitoringCenterStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useMonitoringCenterStore.getState().setLoading(true);
    expect(useMonitoringCenterStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useMonitoringCenterStore.getState().setError('Error');
    expect(useMonitoringCenterStore.getState().error).toBe('Error');
  });
});
