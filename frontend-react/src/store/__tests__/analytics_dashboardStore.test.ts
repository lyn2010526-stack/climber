import { describe, it, expect, beforeEach } from 'vitest';
import { useAnalyticsDashboardStore } from '../analytics_dashboardStore';

describe('useAnalyticsDashboardStore', () => {
  beforeEach(() => {
    useAnalyticsDashboardStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useAnalyticsDashboardStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useAnalyticsDashboardStore.getState().setItems(items);
    expect(useAnalyticsDashboardStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useAnalyticsDashboardStore.getState().addItem(item);
    expect(useAnalyticsDashboardStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useAnalyticsDashboardStore.getState().addItem(item);
    useAnalyticsDashboardStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAnalyticsDashboardStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useAnalyticsDashboardStore.getState().addItem(item);
    useAnalyticsDashboardStore.getState().removeItem('1');
    expect(useAnalyticsDashboardStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAnalyticsDashboardStore.getState().selectItem('1');
    expect(useAnalyticsDashboardStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useAnalyticsDashboardStore.getState().setLoading(true);
    expect(useAnalyticsDashboardStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useAnalyticsDashboardStore.getState().setError('Error');
    expect(useAnalyticsDashboardStore.getState().error).toBe('Error');
  });
});
