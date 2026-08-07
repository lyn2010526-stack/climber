import { describe, it, expect, beforeEach } from 'vitest';
import { useAlertCenterStore } from '../alert_centerStore';

describe('useAlertCenterStore', () => {
  beforeEach(() => {
    useAlertCenterStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useAlertCenterStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useAlertCenterStore.getState().setItems(items);
    expect(useAlertCenterStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useAlertCenterStore.getState().addItem(item);
    expect(useAlertCenterStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useAlertCenterStore.getState().addItem(item);
    useAlertCenterStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAlertCenterStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useAlertCenterStore.getState().addItem(item);
    useAlertCenterStore.getState().removeItem('1');
    expect(useAlertCenterStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAlertCenterStore.getState().selectItem('1');
    expect(useAlertCenterStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useAlertCenterStore.getState().setLoading(true);
    expect(useAlertCenterStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useAlertCenterStore.getState().setError('Error');
    expect(useAlertCenterStore.getState().error).toBe('Error');
  });
});
