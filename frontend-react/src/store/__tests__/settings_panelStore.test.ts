import { describe, it, expect, beforeEach } from 'vitest';
import { useSettingsPanelStore } from '../settings_panelStore';

describe('useSettingsPanelStore', () => {
  beforeEach(() => {
    useSettingsPanelStore.setState({
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
    const state = useSettingsPanelStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSettingsPanelStore.getState().setItems(items);
    expect(useSettingsPanelStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsPanelStore.getState().addItem(item);
    expect(useSettingsPanelStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsPanelStore.getState().addItem(item);
    useSettingsPanelStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSettingsPanelStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsPanelStore.getState().addItem(item);
    useSettingsPanelStore.getState().removeItem('1');
    expect(useSettingsPanelStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSettingsPanelStore.getState().selectItem('1');
    expect(useSettingsPanelStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useSettingsPanelStore.getState().setLoading(true);
    expect(useSettingsPanelStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useSettingsPanelStore.getState().setError('Error');
    expect(useSettingsPanelStore.getState().error).toBe('Error');
  });
});
