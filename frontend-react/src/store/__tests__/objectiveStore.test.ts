import { describe, it, expect, beforeEach } from 'vitest';
import { useObjectiveStore } from '../objectiveStore';

describe('useObjectiveStore', () => {
  beforeEach(() => {
    useObjectiveStore.setState(useObjectiveStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useObjectiveStore).toBeDefined();
    expect(typeof useObjectiveStore.getState).toBe('function');
    expect(typeof useObjectiveStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useObjectiveStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} }];
    useObjectiveStore.getState().setItems(testItems);
    expect(useObjectiveStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useObjectiveStore.getState().selectItem(1);
    expect(useObjectiveStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useObjectiveStore.getState().selectItem(1);
    useObjectiveStore.getState().selectItem(null);
    expect(useObjectiveStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useObjectiveStore.getState().setLoading(true);
    expect(useObjectiveStore.getState().loading).toBe(true);
    useObjectiveStore.getState().setLoading(false);
    expect(useObjectiveStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useObjectiveStore.getState().setError('test error');
    expect(useObjectiveStore.getState().error).toBe('test error');
    useObjectiveStore.getState().setError(null);
    expect(useObjectiveStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useObjectiveStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useObjectiveStore.getState().addItem(newItem);
    expect(useObjectiveStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useObjectiveStore.getState().addItem(newItem);
    const lengthBefore = useObjectiveStore.getState().items.length;
    useObjectiveStore.getState().removeItem(999);
    expect(useObjectiveStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
