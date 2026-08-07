import { describe, it, expect, beforeEach } from 'vitest';
import { useGoalStore } from '../goalStore';

describe('useGoalStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useGoalStore.setState(useGoalStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useGoalStore).toBeDefined();
    expect(typeof useGoalStore.getState).toBe('function');
    expect(typeof useGoalStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useGoalStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useGoalStore.getState().setItems(testItems);
    expect(useGoalStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useGoalStore.getState().selectItem(1);
    expect(useGoalStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useGoalStore.getState().selectItem(1);
    useGoalStore.getState().selectItem(null);
    expect(useGoalStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useGoalStore.getState().setLoading(true);
    expect(useGoalStore.getState().loading).toBe(true);
    useGoalStore.getState().setLoading(false);
    expect(useGoalStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useGoalStore.getState().setError('test error');
    expect(useGoalStore.getState().error).toBe('test error');
    useGoalStore.getState().setError(null);
    expect(useGoalStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useGoalStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useGoalStore.getState().addItem(newItem);
    expect(useGoalStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useGoalStore.getState().addItem(newItem);
    const lengthBefore = useGoalStore.getState().items.length;
    useGoalStore.getState().removeItem(999);
    expect(useGoalStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
