import { describe, it, expect, beforeEach } from 'vitest';
import { useCurrentPage } from '../page';

describe('useCurrentPage', () => {
  beforeEach(() => {
    useCurrentPage.setState({
      page: null,
      isValidRoute: true,
    });
  });

  it('has initial state', () => {
    const state = useCurrentPage.getState();
    expect(state.isValidRoute).toBe(true);
  });

  it('setPage updates page', () => {
    useCurrentPage.getState().setPage('chat');
    expect(useCurrentPage.getState().page).toBe('chat');
    expect(useCurrentPage.getState().isValidRoute).toBe(true);
  });

  it('setPage can set agents page', () => {
    useCurrentPage.getState().setPage('agents');
    expect(useCurrentPage.getState().page).toBe('agents');
  });

  it('setPage can set settings page', () => {
    useCurrentPage.getState().setPage('settings');
    expect(useCurrentPage.getState().page).toBe('settings');
  });
});
