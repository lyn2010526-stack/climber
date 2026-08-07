import { describe, it, expect, beforeEach } from 'vitest';
import { useDecisionStore } from '../decisionStore';

describe('useDecisionStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useDecisionStore.setState(useDecisionStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useDecisionStore).toBeDefined();
    expect(typeof useDecisionStore.getState).toBe('function');
    expect(typeof useDecisionStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useDecisionStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useDecisionStore.getState().setItems(testItems);
    expect(useDecisionStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useDecisionStore.getState().selectItem(1);
    expect(useDecisionStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useDecisionStore.getState().selectItem(1);
    useDecisionStore.getState().selectItem(null);
    expect(useDecisionStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useDecisionStore.getState().setLoading(true);
    expect(useDecisionStore.getState().loading).toBe(true);
    useDecisionStore.getState().setLoading(false);
    expect(useDecisionStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useDecisionStore.getState().setError('test error');
    expect(useDecisionStore.getState().error).toBe('test error');
    useDecisionStore.getState().setError(null);
    expect(useDecisionStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useDecisionStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useDecisionStore.getState().addItem(newItem);
    expect(useDecisionStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useDecisionStore.getState().addItem(newItem);
    const lengthBefore = useDecisionStore.getState().items.length;
    useDecisionStore.getState().removeItem(999);
    expect(useDecisionStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
