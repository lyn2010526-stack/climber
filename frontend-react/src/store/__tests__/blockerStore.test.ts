import { describe, it, expect, beforeEach } from 'vitest';
import { useBlockerStore } from '../blockerStore';

describe('useBlockerStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useBlockerStore.setState(useBlockerStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useBlockerStore).toBeDefined();
    expect(typeof useBlockerStore.getState).toBe('function');
    expect(typeof useBlockerStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useBlockerStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useBlockerStore.getState().setItems(testItems);
    expect(useBlockerStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useBlockerStore.getState().selectItem(1);
    expect(useBlockerStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useBlockerStore.getState().selectItem(1);
    useBlockerStore.getState().selectItem(null);
    expect(useBlockerStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useBlockerStore.getState().setLoading(true);
    expect(useBlockerStore.getState().loading).toBe(true);
    useBlockerStore.getState().setLoading(false);
    expect(useBlockerStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useBlockerStore.getState().setError('test error');
    expect(useBlockerStore.getState().error).toBe('test error');
    useBlockerStore.getState().setError(null);
    expect(useBlockerStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useBlockerStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useBlockerStore.getState().addItem(newItem);
    expect(useBlockerStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useBlockerStore.getState().addItem(newItem);
    const lengthBefore = useBlockerStore.getState().items.length;
    useBlockerStore.getState().removeItem(999);
    expect(useBlockerStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
