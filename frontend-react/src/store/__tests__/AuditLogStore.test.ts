import { describe, it, expect, beforeEach } from 'vitest';
import { useAuditLogStore } from '../AuditLogStore';

describe('useAuditLogStore', () => {
  beforeEach(() => {
    useAuditLogStore.setState({
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
    const state = useAuditLogStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useAuditLogStore.getState().setItems(items);
    expect(useAuditLogStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditLogStore.getState().addItem(item);
    expect(useAuditLogStore.getState().items).toHaveLength(1);
    expect(useAuditLogStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditLogStore.getState().addItem(item);
    useAuditLogStore.getState().updateItem('1', { name: 'Updated' });
    expect(useAuditLogStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useAuditLogStore.getState().addItem(item);
    useAuditLogStore.getState().removeItem('1');
    expect(useAuditLogStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useAuditLogStore.getState().selectItem('1');
    expect(useAuditLogStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useAuditLogStore.getState().selectItem('1');
    useAuditLogStore.getState().selectItem(null);
    expect(useAuditLogStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useAuditLogStore.getState().setLoading(true);
    expect(useAuditLogStore.getState().loading).toBe(true);
    useAuditLogStore.getState().setLoading(false);
    expect(useAuditLogStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useAuditLogStore.getState().setError('Something went wrong');
    expect(useAuditLogStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useAuditLogStore.getState().setError('Error');
    useAuditLogStore.getState().setError(null);
    expect(useAuditLogStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useAuditLogStore.getState().setFilters(filters);
    expect(useAuditLogStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useAuditLogStore.getState().setPagination({ page: 3 });
    expect(useAuditLogStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useAuditLogStore.getState().setPagination({ pageSize: 50 });
    expect(useAuditLogStore.getState().pagination.pageSize).toBe(50);
    expect(useAuditLogStore.getState().pagination.page).toBe(1);
  });
});
