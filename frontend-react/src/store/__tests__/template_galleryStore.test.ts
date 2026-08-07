import { describe, it, expect, beforeEach } from 'vitest';
import { useTemplateGalleryStore } from '../template_galleryStore';

describe('useTemplateGalleryStore', () => {
  beforeEach(() => {
    useTemplateGalleryStore.setState({
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
    const state = useTemplateGalleryStore.getState();
    expect(state.items).toEqual([]);
    expect(state.selectedId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setItems sets items', () => {
    const items = [{ id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' }];
    useTemplateGalleryStore.getState().setItems(items);
    expect(useTemplateGalleryStore.getState().items).toEqual(items);
  });

  it('addItem adds an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTemplateGalleryStore.getState().addItem(item);
    expect(useTemplateGalleryStore.getState().items).toHaveLength(1);
  });

  it('updateItem updates an existing item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTemplateGalleryStore.getState().addItem(item);
    useTemplateGalleryStore.getState().updateItem('1', { name: 'Updated' });
    expect(useTemplateGalleryStore.getState().items[0]?.name).toBe('Updated');
  });

  it('removeItem removes an item', () => {
    const item = { id: '1', name: 'Test', description: 'Desc', status: 'active', createdAt: '2024-01-01', updatedAt: '2024-01-01' };
    useTemplateGalleryStore.getState().addItem(item);
    useTemplateGalleryStore.getState().removeItem('1');
    expect(useTemplateGalleryStore.getState().items).toHaveLength(0);
  });

  it('selectItem sets selectedId', () => {
    useTemplateGalleryStore.getState().selectItem('1');
    expect(useTemplateGalleryStore.getState().selectedId).toBe('1');
  });

  it('setLoading sets loading', () => {
    useTemplateGalleryStore.getState().setLoading(true);
    expect(useTemplateGalleryStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useTemplateGalleryStore.getState().setError('Error');
    expect(useTemplateGalleryStore.getState().error).toBe('Error');
  });
});
