import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { devtools } from 'zustand/middleware';
import type { Theme } from './types';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

interface Modal {
  id: string;
  isOpen: boolean;
  data?: unknown;
}

interface UIState {
  theme: Theme;
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  mobileMenuOpen: boolean;
  searchOverlayOpen: boolean;
  commandPaletteOpen: boolean;
  rightPanelOpen: boolean;
  focusMode: boolean;
  toasts: Toast[];
  modals: Modal[];

  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setMobileMenuOpen: (open: boolean) => void;
  setSearchOverlayOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setRightPanelOpen: (open: boolean) => void;
  toggleRightPanel: () => void;
  setFocusMode: (focus: boolean) => void;
  toggleFocusMode: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  openModal: (id: string, data?: unknown) => void;
  closeModal: (id: string) => void;
  closeAllModals: () => void;
  isModalOpen: (id: string) => boolean;
}

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  try {
    const stored = localStorage.getItem('climber-theme') as Theme;
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        theme: getInitialTheme(),
        sidebarOpen: true,
        sidebarCollapsed: false,
        mobileMenuOpen: false,
        searchOverlayOpen: false,
        commandPaletteOpen: false,
        rightPanelOpen: true,
        focusMode: false,
        toasts: [],
        modals: [],

        setTheme: (theme) => set({ theme }),
        toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),

        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
        setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

        setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
        setSearchOverlayOpen: (open) => set({ searchOverlayOpen: open }),
        setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

        setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
        toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),

        setFocusMode: (focus) => set({ focusMode: focus }),
        toggleFocusMode: () => set((s) => ({ focusMode: !s.focusMode })),

        addToast: (toast) => {
          const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
          set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));

          if (toast.duration !== 0) {
            setTimeout(() => {
              get().removeToast(id);
            }, toast.duration || 5000);
          }

          return id;
        },

        removeToast: (id) =>
          set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

        clearToasts: () => set({ toasts: [] }),

        openModal: (id, data) =>
          set((s) => ({
            modals: s.modals.some((m) => m.id === id)
              ? s.modals.map((m) => (m.id === id ? { ...m, isOpen: true, data } : m))
              : [...s.modals, { id, isOpen: true, data }],
          })),

        closeModal: (id) =>
          set((s) => ({
            modals: s.modals.map((m) => (m.id === id ? { ...m, isOpen: false } : m)),
          })),

        closeAllModals: () =>
          set((s) => ({ modals: s.modals.map((m) => ({ ...m, isOpen: false })) })),

        isModalOpen: (id) => get().modals.some((m) => m.id === id && m.isOpen),
      }),
      {
        name: 'climber-ui',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
          sidebarCollapsed: state.sidebarCollapsed,
        }),
      }
    ),
    { name: 'UIStore' }
  )
);
