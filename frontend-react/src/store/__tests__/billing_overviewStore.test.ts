import { describe, it, expect, beforeEach } from 'vitest';
import { useBillingOverviewStore } from '../billing_overviewStore';

describe('useBillingOverviewStore', () => {
  beforeEach(() => {
    useBillingOverviewStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useBillingOverviewStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useBillingOverviewStore.getState().setItems(items);
    expect(useBillingOverviewStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useBillingOverviewStore.getState().addItem(item);
    expect(useBillingOverviewStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useBillingOverviewStore.getState().addItem(item);
    useBillingOverviewStore.getState().updateItem('1', { name: 'Updated' });
    expect(useBillingOverviewStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useBillingOverviewStore.getState().addItem(item);
    useBillingOverviewStore.getState().removeItem('1');
    expect(useBillingOverviewStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useBillingOverviewStore.getState().selectItem('1');
    expect(useBillingOverviewStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useBillingOverviewStore.getState().setLoading(true);
    expect(useBillingOverviewStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useBillingOverviewStore.getState().setError('Error');
    expect(useBillingOverviewStore.getState().error).toBe('Error');
  });
});
