import { describe, it, expect, beforeEach } from 'vitest';
import { useAuditStore } from '../AuditStore';

describe('useAuditStore', () => {
  beforeEach(() => {
    useAuditStore.setState({
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
    const state = useAuditStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useAuditStore.getState().setItems(items);
    expect(useAuditStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditStore.getState().addItem(item);
    expect(useAuditStore.getState().items).toHaveLength(1);
    expect(useAuditStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditStore.getState().addItem(item);
    useAuditStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAuditStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditStore.getState().addItem(item);
    useAuditStore.getState().removeItem('1');
    expect(useAuditStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAuditStore.getState().selectItem('1');
    expect(useAuditStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useAuditStore.getState().selectItem('1');
    useAuditStore.getState().selectItem(null);
    expect(useAuditStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useAuditStore.getState().setLoading(true);
    expect(useAuditStore.getState().loading).toBe(true);
    useAuditStore.getState().setLoading(false);
    expect(useAuditStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useAuditStore.getState().setError('Something went wrong');
    expect(useAuditStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useAuditStore.getState().setError('Error');
    useAuditStore.getState().setError(null);
    expect(useAuditStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useAuditStore.getState().setFilters(filters);
    expect(useAuditStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useAuditStore.getState().setPagination({ page: 3 });
    expect(useAuditStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useAuditStore.getState().setPagination({ pageSize: 50 });
    expect(useAuditStore.getState().pagination.pageSize).toBe(50);
    expect(useAuditStore.getState().pagination.page).toBe(1);
  });
});
