import { describe, it, expect, beforeEach } from 'vitest';
import { useKpiStore } from '../kpiStore';

describe('useKpiStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useKpiStore.setState(useKpiStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useKpiStore).toBeDefined();
    expect(typeof useKpiStore.getState).toBe('function');
    expect(typeof useKpiStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useKpiStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useKpiStore.getState().setItems(testItems);
    expect(useKpiStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useKpiStore.getState().selectItem(1);
    expect(useKpiStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useKpiStore.getState().selectItem(1);
    useKpiStore.getState().selectItem(null);
    expect(useKpiStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useKpiStore.getState().setLoading(true);
    expect(useKpiStore.getState().loading).toBe(true);
    useKpiStore.getState().setLoading(false);
    expect(useKpiStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useKpiStore.getState().setError('test error');
    expect(useKpiStore.getState().error).toBe('test error');
    useKpiStore.getState().setError(null);
    expect(useKpiStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useKpiStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useKpiStore.getState().addItem(newItem);
    expect(useKpiStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useKpiStore.getState().addItem(newItem);
    const lengthBefore = useKpiStore.getState().items.length;
    useKpiStore.getState().removeItem(999);
    expect(useKpiStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
