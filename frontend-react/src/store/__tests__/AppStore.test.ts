import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '../AppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      items: [],
      selectedId: null,
      loading: false,
      error: null,
      filters: {},
      pagination: { page: 1, pageSize: 20, total: 0 },
    });
  });

  it('has initial state', () => {
    const state = useAppStore.getState();
    expect(state.items).toEqual([]);
    expect(state.loading).toBe(false);
  });

  it('setLoading sets loading', () => {
    useAppStore.getState().setLoading(true);
    expect(useAppStore.getState().loading).toBe(true);
  });

  it('setError sets error', () => {
    useAppStore.getState().setError('test error');
    expect(useAppStore.getState().error).toBe('test error');
  });
});
