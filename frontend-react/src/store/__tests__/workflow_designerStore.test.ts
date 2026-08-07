import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkflowDesignerStore } from '../workflow_designerStore';

describe('useWorkflowDesignerStore', () => {
  beforeEach(() => {
    useWorkflowDesignerStore.setState({
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
    const state = useWorkflowDesignerStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useWorkflowDesignerStore.getState().setItems(items);
    expect(useWorkflowDesignerStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkflowDesignerStore.getState().addItem(item);
    expect(useWorkflowDesignerStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkflowDesignerStore.getState().addItem(item);
    useWorkflowDesignerStore.getState().updateItem('1', { name: 'Updated' });
    expect(useWorkflowDesignerStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useWorkflowDesignerStore.getState().addItem(item);
    useWorkflowDesignerStore.getState().removeItem('1');
    expect(useWorkflowDesignerStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useWorkflowDesignerStore.getState().selectItem('1');
    expect(useWorkflowDesignerStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useWorkflowDesignerStore.getState().setLoading(true);
    expect(useWorkflowDesignerStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useWorkflowDesignerStore.getState().setError('Error');
    expect(useWorkflowDesignerStore.getState().error).toBe('Error');
  });
});
