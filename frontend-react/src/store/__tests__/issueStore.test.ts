import { describe, it, expect, beforeEach } from 'vitest';
import { useIssueStore } from '../issueStore';

describe('useIssueStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useIssueStore.setState(useIssueStore.getInitialState?.() ?? {});
  });

  it('exists and is defined', () => {
    expect(useIssueStore).toBeDefined();
    expect(typeof useIssueStore.getState).toBe('function');
    expect(typeof useIssueStore.setState).toBe('function');
  });

  it('has initial state', () => {
    const state = useIssueStore.getState();
    expect(state).toBeDefined();
    expect(state.items).toBeDefined();
  });

  it('setItems updates items', () => {
    const testItems = [{ id: 1, name: 'Test' }];
    useIssueStore.getState().setItems(testItems);
    expect(useIssueStore.getState().items).toEqual(testItems);
  });

  it('selectItem sets selectedId', () => {
    useIssueStore.getState().selectItem(1);
    expect(useIssueStore.getState().selectedId).toBe(1);
  });

  it('selectItem accepts null', () => {
    useIssueStore.getState().selectItem(1);
    useIssueStore.getState().selectItem(null);
    expect(useIssueStore.getState().selectedId).toBeNull();
  });

  it('setLoading updates loading state', () => {
    useIssueStore.getState().setLoading(true);
    expect(useIssueStore.getState().loading).toBe(true);
    useIssueStore.getState().setLoading(false);
    expect(useIssueStore.getState().loading).toBe(false);
  });

  it('setError updates error state', () => {
    useIssueStore.getState().setError('test error');
    expect(useIssueStore.getState().error).toBe('test error');
    useIssueStore.getState().setError(null);
    expect(useIssueStore.getState().error).toBeNull();
  });

  it('addItem adds an item to items array', () => {
    const initialLength = useIssueStore.getState().items.length;
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useIssueStore.getState().addItem(newItem);
    expect(useIssueStore.getState().items.length).toBe(initialLength + 1);
  });

  it('removeItem removes an item by id', () => {
    const newItem = { id: 999, name: 'New Item', status: 'active', priority: 'high', createdAt: '2024-01-01', updatedAt: '2024-01-01', metadata: {} };
    useIssueStore.getState().addItem(newItem);
    const lengthBefore = useIssueStore.getState().items.length;
    useIssueStore.getState().removeItem(999);
    expect(useIssueStore.getState().items.length).toBe(lengthBefore - 1);
  });
});
