import { describe, it, expect, beforeEach } from 'vitest';
import { useReleaseStore } from '../releaseStore';

describe('useReleaseStore', () => {
  beforeEach(() => {
    useReleaseStore.setState(useReleaseStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useReleaseStore).toBeDefined();
    expect(typeof useReleaseStore.getState).toBe('function');
    expect(typeof useReleaseStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useReleaseStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} }];
    useReleaseStore.getState().setItems(testItems);
    expect(useReleaseStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useReleaseStore.getState().selectItem(1);
    expect(useReleaseStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useReleaseStore.getState().selectItem(1);
    useReleaseStore.getState().selectItem(null);
    expect(useReleaseStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useReleaseStore.getState().setLoading(true);
    expect(useReleaseStore.getState().loading).toBe(true);
    useReleaseStore.getState().setLoading(false);
    expect(useReleaseStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useReleaseStore.getState().setError('test error');
    expect(useReleaseStore.getState().error).toBe('test error');
    useReleaseStore.getState().setError(null);
    expect(useReleaseStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useReleaseStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useReleaseStore.getState().addItem(newItem);
    expect(useReleaseStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useReleaseStore.getState().addItem(newItem);
    const lengthBefore = useReleaseStore.getState().items.length;
    useReleaseStore.getState().removeItem(999);
    expect(useReleaseStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
