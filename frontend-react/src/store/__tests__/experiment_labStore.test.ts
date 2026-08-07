import { describe, it, expect, beforeEach } from 'vitest';
import { useExperimentLabStore } from '../experiment_labStore';

describe('useExperimentLabStore', () => {
  beforeEach(() => {
    useExperimentLabStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
    });
  });

  it('has initial state', () => {
    const state = useExperimentLabStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test' }];
    useExperimentLabStore.getState().setItems(items);
    expect(useExperimentLabStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test' };
    useExperimentLabStore.getState().addItem(item);
    expect(useExperimentLabStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test' };
    useExperimentLabStore.getState().addItem(item);
    useExperimentLabStore.getState().updateItem('1', { name: 'Updated' });
    expect(useExperimentLabStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test' };
    useExperimentLabStore.getState().addItem(item);
    useExperimentLabStore.getState().removeItem('1');
    expect(useExperimentLabStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useExperimentLabStore.getState().selectItem('1');
    expect(useExperimentLabStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useExperimentLabStore.getState().setLoading(true);
    expect(useExperimentLabStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useExperimentLabStore.getState().setError('Error');
    expect(useExperimentLabStore.getState().error).toBe('Error');
  });
});
