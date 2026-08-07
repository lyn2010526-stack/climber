import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../ui';

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      theme: 'dark',
      sidebarOpen: true,
      mobileMenuOpen: false,
      searchOverlayOpen: false,
      commandPaletteOpen: false,
      toasts: [],
    });
  });

  it('has initial state', () => {
    const state = useUIStore.getState();
    expect(state.theme).toBe('dark');
    expect(state.sidebarOpen).toBe(true);
    expect(state.mobileMenuOpen).toBe(false);
    expect(state.toasts).toEqual([]);
  });

  it('setTheme updates theme', () => {
    useUIStore.getState().setTheme('light');
    expect(useUIStore.getState().theme).toBe('light');
  });

  it('toggleTheme switches theme', () => {
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().theme).toBe('light');
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().theme).toBe('dark');
  });

  it('setSidebarOpen updates sidebar state', () => {
    useUIStore.getState().setSidebarOpen(false);
    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });

  it('toggleSidebar toggles sidebar', () => {
    const initial = useUIStore.getState().sidebarOpen;
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(!initial);
  });

  it('addToast adds a toast', () => {
    const id = useUIStore.getState().addToast({ type: 'success', title: 'Done' });
    expect(id).toBeTruthy();
    expect(useUIStore.getState().toasts).toHaveLength(1);
    expect(useUIStore.getState().toasts[0]?.title).toBe('Done');
  });

  it('removeToast removes a toast', () => {
    const id = useUIStore.getState().addToast({ type: 'info', title: 'Test' });
    useUIStore.getState().removeToast(id);
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('setMobileMenuOpen updates mobile menu state', () => {
    useUIStore.getState().setMobileMenuOpen(true);
    expect(useUIStore.getState().mobileMenuOpen).toBe(true);
  });

  it('setSearchOverlayOpen updates search overlay state', () => {
    useUIStore.getState().setSearchOverlayOpen(true);
    expect(useUIStore.getState().searchOverlayOpen).toBe(true);
  });

  it('setCommandPaletteOpen updates command palette state', () => {
    useUIStore.getState().setCommandPaletteOpen(true);
    expect(useUIStore.getState().commandPaletteOpen).toBe(true);
  });
});
