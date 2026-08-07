import { describe, it, expect, beforeEach } from 'vitest';
import { useIntegrationManagerStore } from '../integration_managerStore';

describe('useIntegrationManagerStore', () => {
  beforeEach(() => {
    useIntegrationManagerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useIntegrationManagerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useIntegrationManagerStore.getState().setItems(items);
    expect(useIntegrationManagerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useIntegrationManagerStore.getState().addItem(item);
    expect(useIntegrationManagerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useIntegrationManagerStore.getState().addItem(item);
    useIntegrationManagerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useIntegrationManagerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useIntegrationManagerStore.getState().addItem(item);
    useIntegrationManagerStore.getState().removeItem('1');
    expect(useIntegrationManagerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useIntegrationManagerStore.getState().selectItem('1');
    expect(useIntegrationManagerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useIntegrationManagerStore.getState().setLoading(true);
    expect(useIntegrationManagerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useIntegrationManagerStore.getState().setError('Error');
    expect(useIntegrationManagerStore.getState().error).toBe('Error');
  });
});
