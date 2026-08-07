import { describe, it, expect, beforeEach } from 'vitest';
import { useBranchStore } from '../branchStore';

describe('useBranchStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useBranchStore.setState(useBranchStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useBranchStore).toBeDefined();
    expect(typeof useBranchStore.getState).toBe('function');
    expect(typeof useBranchStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useBranchStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useBranchStore.getState().setItems(testItems);
    expect(useBranchStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useBranchStore.getState().selectItem(1);
    expect(useBranchStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useBranchStore.getState().selectItem(1);
    useBranchStore.getState().selectItem(null);
    expect(useBranchStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useBranchStore.getState().setLoading(true);
    expect(useBranchStore.getState().loading).toBe(true);
    useBranchStore.getState().setLoading(false);
    expect(useBranchStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useBranchStore.getState().setError('test error');
    expect(useBranchStore.getState().error).toBe('test error');
    useBranchStore.getState().setError(null);
    expect(useBranchStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useBranchStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useBranchStore.getState().addItem(newItem);
    expect(useBranchStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useBranchStore.getState().addItem(newItem);
    const lengthBefore = useBranchStore.getState().items.length;
    useBranchStore.getState().removeItem(999);
    expect(useBranchStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
