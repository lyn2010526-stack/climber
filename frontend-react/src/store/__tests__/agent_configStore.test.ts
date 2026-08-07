import { describe, it, expect, beforeEach } from 'vitest';
import { useAgentConfigStore } from '../agent_configStore';

describe('useAgentConfigStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useAgentConfigStore.setState(useAgentConfigStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useAgentConfigStore).toBeDefined();
    expect(typeof useAgentConfigStore.getState).toBe('function');
    expect(typeof useAgentConfigStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useAgentConfigStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useAgentConfigStore.getState().setItems(testItems);
    expect(useAgentConfigStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useAgentConfigStore.getState().selectItem(1);
    expect(useAgentConfigStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useAgentConfigStore.getState().selectItem(1);
    useAgentConfigStore.getState().selectItem(null);
    expect(useAgentConfigStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useAgentConfigStore.getState().setLoading(true);
    expect(useAgentConfigStore.getState().loading).toBe(true);
    useAgentConfigStore.getState().setLoading(false);
    expect(useAgentConfigStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useAgentConfigStore.getState().setError('test error');
    expect(useAgentConfigStore.getState().error).toBe('test error');
    useAgentConfigStore.getState().setError(null);
    expect(useAgentConfigStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useAgentConfigStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useAgentConfigStore.getState().addItem(newItem);
    expect(useAgentConfigStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useAgentConfigStore.getState().addItem(newItem);
    const lengthBefore = useAgentConfigStore.getState().items.length;
    useAgentConfigStore.getState().removeItem(999);
    expect(useAgentConfigStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
