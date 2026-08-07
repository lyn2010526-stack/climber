import { describe, it, expect, beforeEach } from 'vitest';
import { useReportStore } from '../ReportStore';

describe('useReportStore', () => {
  beforeEach(() => {
    useReportStore.setState({
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
    const state = useReportStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useReportStore.getState().setItems(items);
    expect(useReportStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useReportStore.getState().addItem(item);
    expect(useReportStore.getState().items).toHaveLength(1);
    expect(useReportStore.getState().items[0]).toEqual(item);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useReportStore.getState().addItem(item);
    useReportStore.getState().updateItem('1', { name: 'Updated' });
    expect(useReportStore.getState().items[0].name).toBe('Updated');
  });

  it('removeItem removes an item by id', () => {
    const item = { id: '1', name: 'Test', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useReportStore.getState().addItem(item);
    useReportStore.getState().removeItem('1');
    expect(useReportStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useReportStore.getState().selectItem('1');
    expect(useReportStore.getState().selectedId).toBe('1');
  });

  it('selectItem can set null', () => {
    useReportStore.getState().selectItem('1');
    useReportStore.getState().selectItem(null);
    expect(useReportStore.getState().selectedId).toBeNull();
  });

  it('setLoading sets loading state', () => {
    useReportStore.getState().setLoading(true);
    expect(useReportStore.getState().loading).toBe(true);
    useReportStore.getState().setLoading(false);
    expect(useReportStore.getState().loading).toBe(false);
  });

  it('setError sets error message', () => {
    useReportStore.getState().setError('Something went wrong');
    expect(useReportStore.getState().error).toBe('Something went wrong');
  });

  it('setError can clear error', () => {
    useReportStore.getState().setError('Error');
    useReportStore.getState().setError(null);
    expect(useReportStore.getState().error).toBeNull();
  });

  it('setFilters sets filters', () => {
    const filters = { status: 'active', type: 'warning' };
    useReportStore.getState().setFilters(filters);
    expect(useReportStore.getState().filters).toEqual(filters);
  });

  it('setPagination updates pagination', () => {
    useReportStore.getState().setPagination({ page: 3 });
    expect(useReportStore.getState().pagination.page).toBe(3);
  });

  it('setPagination merges with existing pagination', () => {
    useReportStore.getState().setPagination({ pageSize: 50 });
    expect(useReportStore.getState().pagination.pageSize).toBe(50);
    expect(useReportStore.getState().pagination.page).toBe(1);
  });
});
