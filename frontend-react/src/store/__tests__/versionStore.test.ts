import { describe, it, expect, beforeEach } from 'vitest';
import { useVersionStore } from '../versionStore';

describe('useVersionStore', () => {
  beforeEach(() => {
    useVersionStore.setState(useVersionStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useVersionStore).toBeDefined();
    expect(typeof useVersionStore.getState).toBe('function');
    expect(typeof useVersionStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useVersionStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} }];
    useVersionStore.getState().setItems(testItems);
    expect(useVersionStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useVersionStore.getState().selectItem(1);
    expect(useVersionStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useVersionStore.getState().selectItem(1);
    useVersionStore.getState().selectItem(null);
    expect(useVersionStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useVersionStore.getState().setLoading(true);
    expect(useVersionStore.getState().loading).toBe(true);
    useVersionStore.getState().setLoading(false);
    expect(useVersionStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useVersionStore.getState().setError('test error');
    expect(useVersionStore.getState().error).toBe('test error');
    useVersionStore.getState().setError(null);
    expect(useVersionStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useVersionStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useVersionStore.getState().addItem(newItem);
    expect(useVersionStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useVersionStore.getState().addItem(newItem);
    const lengthBefore = useVersionStore.getState().items.length;
    useVersionStore.getState().removeItem(999);
    expect(useVersionStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
