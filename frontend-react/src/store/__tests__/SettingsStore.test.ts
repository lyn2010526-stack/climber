import { describe, it, expect, beforeEach } from 'vitest';
import { useSettingsStore } from '../SettingsStore';

describe('useSettingsStore', () => {
  beforeEach(() => {
    useSettingsStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
      sortBy: 'createdAt',
      sortOrder: 'desc',
      pagination: { page: 1, pageSize: 20, total: 0 },
    });
  });

  it('has initial state', () => {
    const state = useSettingsStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useSettingsStore.getState().setItems(items);
    expect(useSettingsStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsStore.getState().addItem(item);
    expect(useSettingsStore.getState().items).toHaveLength(1);
    expect(useSettingsStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsStore.getState().addItem(item);
    useSettingsStore.getState().updateItem('1', { name: 'Updated' });
    expect(useSettingsStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useSettingsStore.getState().addItem(item);
    useSettingsStore.getState().removeItem('1');
    expect(useSettingsStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useSettingsStore.getState().selectItem('1');
    expect(useSettingsStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useSettingsStore.getState().selectItem('1');
    useSettingsStore.getState().selectItem(null);
    expect(useSettingsStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useSettingsStore.getState().setLoading(true);
    expect(useSettingsStore.getState().loading).toBe(true);
    useSettingsStore.getState().setLoading(false);
    expect(useSettingsStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useSettingsStore.getState().setError('Something went wrong');
    expect(useSettingsStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useSettingsStore.getState().setError('Error');
    useSettingsStore.getState().setError(null);
    expect(useSettingsStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useSettingsStore.getState().setFilters(filters);
    expect(useSettingsStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useSettingsStore.getState().setPagination({ page: 3 });
    expect(useSettingsStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useSettingsStore.getState().setPagination({ pageSize: 50 });
    expect(useSettingsStore.getState().pagination.pageSize).toBe(50);
    expect(useSettingsStore.getState().pagination.page).toBe(1);
  });
});
