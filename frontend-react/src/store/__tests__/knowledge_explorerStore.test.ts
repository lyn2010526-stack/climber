import { describe, it, expect, beforeEach } from 'vitest';
import { useKnowledgeExplorerStore } from '../knowledge_explorerStore';

describe('useKnowledgeExplorerStore', () => {
  beforeEach(() => {
    useKnowledgeExplorerStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useKnowledgeExplorerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useKnowledgeExplorerStore.getState().setItems(items);
    expect(useKnowledgeExplorerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useKnowledgeExplorerStore.getState().addItem(item);
    expect(useKnowledgeExplorerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useKnowledgeExplorerStore.getState().addItem(item);
    useKnowledgeExplorerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useKnowledgeExplorerStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useKnowledgeExplorerStore.getState().addItem(item);
    useKnowledgeExplorerStore.getState().removeItem('1');
    expect(useKnowledgeExplorerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useKnowledgeExplorerStore.getState().selectItem('1');
    expect(useKnowledgeExplorerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useKnowledgeExplorerStore.getState().setLoading(true);
    expect(useKnowledgeExplorerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useKnowledgeExplorerStore.getState().setError('Error');
    expect(useKnowledgeExplorerStore.getState().error).toBe('Error');
  });
});
