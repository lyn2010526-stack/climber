import { describe, it, expect, beforeEach } from 'vitest';
import { useDependencyStore } from '../dependencyStore';

describe('useDependencyStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useDependencyStore.setState(useDependencyStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useDependencyStore).toBeDefined();
    expect(typeof useDependencyStore.getState).toBe('function');
    expect(typeof useDependencyStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useDependencyStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useDependencyStore.getState().setItems(testItems);
    expect(useDependencyStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useDependencyStore.getState().selectItem(1);
    expect(useDependencyStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useDependencyStore.getState().selectItem(1);
    useDependencyStore.getState().selectItem(null);
    expect(useDependencyStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useDependencyStore.getState().setLoading(true);
    expect(useDependencyStore.getState().loading).toBe(true);
    useDependencyStore.getState().setLoading(false);
    expect(useDependencyStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useDependencyStore.getState().setError('test error');
    expect(useDependencyStore.getState().error).toBe('test error');
    useDependencyStore.getState().setError(null);
    expect(useDependencyStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useDependencyStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useDependencyStore.getState().addItem(newItem);
    expect(useDependencyStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useDependencyStore.getState().addItem(newItem);
    const lengthBefore = useDependencyStore.getState().items.length;
    useDependencyStore.getState().removeItem(999);
    expect(useDependencyStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
