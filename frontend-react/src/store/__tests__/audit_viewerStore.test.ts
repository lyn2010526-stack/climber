import { describe, it, expect, beforeEach } from 'vitest';
import { useAuditViewerStore } from '../audit_viewerStore';

describe('useAuditViewerStore', () => {
  beforeEach(() => {
    useAuditViewerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useAuditViewerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useAuditViewerStore.getState().setItems(items);
    expect(useAuditViewerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useAuditViewerStore.getState().addItem(item);
    expect(useAuditViewerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useAuditViewerStore.getState().addItem(item);
    useAuditViewerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAuditViewerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useAuditViewerStore.getState().addItem(item);
    useAuditViewerStore.getState().removeItem('1');
    expect(useAuditViewerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAuditViewerStore.getState().selectItem('1');
    expect(useAuditViewerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useAuditViewerStore.getState().setLoading(true);
    expect(useAuditViewerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useAuditViewerStore.getState().setError('Error');
    expect(useAuditViewerStore.getState().error).toBe('Error');
  });
});
