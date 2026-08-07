import { describe, it, expect, beforeEach } from 'vitest';
import { useRiskStore } from '../riskStore';

describe('useRiskStore', () => {
  beforeEach(() => {
    useRiskStore.setState(useRiskStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useRiskStore).toBeDefined();
    expect(typeof useRiskStore.getState).toBe('function');
    expect(typeof useRiskStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useRiskStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} }];
    useRiskStore.getState().setItems(testItems);
    expect(useRiskStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useRiskStore.getState().selectItem(1);
    expect(useRiskStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useRiskStore.getState().selectItem(1);
    useRiskStore.getState().selectItem(null);
    expect(useRiskStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useRiskStore.getState().setLoading(true);
    expect(useRiskStore.getState().loading).toBe(true);
    useRiskStore.getState().setLoading(false);
    expect(useRiskStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useRiskStore.getState().setError('test error');
    expect(useRiskStore.getState().error).toBe('test error');
    useRiskStore.getState().setError(null);
    expect(useRiskStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useRiskStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useRiskStore.getState().addItem(newItem);
    expect(useRiskStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', description: 'Desc', status: 'active' as const, priority: 'high' as const, createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useRiskStore.getState().addItem(newItem);
    const lengthBefore = useRiskStore.getState().items.length;
    useRiskStore.getState().removeItem(999);
    expect(useRiskStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
