import { describe, it, expect, beforeEach } from 'vitest';
import { useActionStore } from '../actionStore';

describe('useActionStore', () => {
  beforeEach(() => {
    useActionStore.setState(useActionStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useActionStore).toBeDefined();
    expect(typeof useActionStore.getState).toBe('function');
    expect(typeof useActionStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useActionStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} }];
    useActionStore.getState().setItems(testItems);
    expect(useActionStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useActionStore.getState().selectItem(1);
    expect(useActionStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useActionStore.getState().selectItem(1);
    useActionStore.getState().selectItem(null);
    expect(useActionStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useActionStore.getState().setLoading(true);
    expect(useActionStore.getState().loading).toBe(true);
    useActionStore.getState().setLoading(false);
    expect(useActionStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useActionStore.getState().setError('test error');
    expect(useActionStore.getState().error).toBe('test error');
    useActionStore.getState().setError(null);
    expect(useActionStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useActionStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useActionStore.getState().addItem(newItem);
    expect(useActionStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useActionStore.getState().addItem(newItem);
    const lengthBefore = useActionStore.getState().items.length;
    useActionStore.getState().removeItem(999);
    expect(useActionStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
