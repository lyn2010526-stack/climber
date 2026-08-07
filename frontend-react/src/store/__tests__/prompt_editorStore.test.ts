import { describe, it, expect, beforeEach } from 'vitest';
import { usePromptEditorStore } from '../prompt_editorStore';

describe('usePromptEditorStore', () => {
  beforeEach(() => {
    usePromptEditorStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
            filter: {
        search: '',
        status: null,
        sortBy: 'createdAt',
        sortOrder: 'desc',
        page: 1,
        pageSize: 10,
      },
    });
  });

  it('has initial state', () => {
    const state = usePromptEditorStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    usePromptEditorStore.getState().setItems(items);
    expect(usePromptEditorStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePromptEditorStore.getState().addItem(item);
    expect(usePromptEditorStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePromptEditorStore.getState().addItem(item);
    usePromptEditorStore.getState().updateItem('1', { name: 'Updated' });
    expect(usePromptEditorStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    usePromptEditorStore.getState().addItem(item);
    usePromptEditorStore.getState().removeItem('1');
    expect(usePromptEditorStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    usePromptEditorStore.getState().selectItem('1');
    expect(usePromptEditorStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    usePromptEditorStore.getState().setLoading(true);
    expect(usePromptEditorStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    usePromptEditorStore.getState().setError('Error');
    expect(usePromptEditorStore.getState().error).toBe('Error');
  });
});
