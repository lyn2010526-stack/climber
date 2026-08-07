import { describe, it, expect, beforeEach } from 'vitest';
import { useInitiativeStore } from '../initiativeStore';

describe('useInitiativeStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useInitiativeStore.setState(useInitiativeStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useInitiativeStore).toBeDefined();
    expect(typeof useInitiativeStore.getState).toBe('function');
    expect(typeof useInitiativeStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useInitiativeStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useInitiativeStore.getState().setItems(testItems);
    expect(useInitiativeStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useInitiativeStore.getState().selectItem(1);
    expect(useInitiativeStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useInitiativeStore.getState().selectItem(1);
    useInitiativeStore.getState().selectItem(null);
    expect(useInitiativeStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useInitiativeStore.getState().setLoading(true);
    expect(useInitiativeStore.getState().loading).toBe(true);
    useInitiativeStore.getState().setLoading(false);
    expect(useInitiativeStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useInitiativeStore.getState().setError('test error');
    expect(useInitiativeStore.getState().error).toBe('test error');
    useInitiativeStore.getState().setError(null);
    expect(useInitiativeStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useInitiativeStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useInitiativeStore.getState().addItem(newItem);
    expect(useInitiativeStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useInitiativeStore.getState().addItem(newItem);
    const lengthBefore = useInitiativeStore.getState().items.length;
    useInitiativeStore.getState().removeItem(999);
    expect(useInitiativeStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
