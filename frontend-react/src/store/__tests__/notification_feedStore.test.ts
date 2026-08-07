import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationFeedStore } from '../notification_feedStore';

describe('useNotificationFeedStore', () => {
  beforeEach(() => {
    useNotificationFeedStore.setState({
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
    const state = useNotificationFeedStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useNotificationFeedStore.getState().setItems(items);
    expect(useNotificationFeedStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationFeedStore.getState().addItem(item);
    expect(useNotificationFeedStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationFeedStore.getState().addItem(item);
    useNotificationFeedStore.getState().updateItem('1', { name: 'Updated' });
    expect(useNotificationFeedStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useNotificationFeedStore.getState().addItem(item);
    useNotificationFeedStore.getState().removeItem('1');
    expect(useNotificationFeedStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useNotificationFeedStore.getState().selectItem('1');
    expect(useNotificationFeedStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useNotificationFeedStore.getState().setLoading(true);
    expect(useNotificationFeedStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useNotificationFeedStore.getState().setError('Error');
    expect(useNotificationFeedStore.getState().error).toBe('Error');
  });
});
