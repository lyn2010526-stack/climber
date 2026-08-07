import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { devtools } from 'zustand/middleware';
import type { AuthUser } from './types';
import { authService } from '../services/authService';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;

  setToken: (token: string | null) => void;
  setUser: (user: AuthUser | null) => void;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearError: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        token: null,
        refreshToken: null,
        user: null,
        isAuthenticated: false,
        loading: false,
        error: null,

        setToken: (token) => set({ token, isAuthenticated: Boolean(token) }),

        setUser: (user) => set({ user }),

        login: async (username, password) => {
          set({ loading: true, error: null });
          try {
            const res = await authService.login({ username, password });
            set({
              token: res.access_token,
              refreshToken: res.refresh_token,
              user: {
                id: res.user.id,
                name: res.user.username,
                email: res.user.email,
                role: res.user.role,
              },
              isAuthenticated: true,
              loading: false,
            });
          } catch (err) {
            const msg = err instanceof Error ? err.message : 'Login failed';
            set({ error: msg, loading: false });
            throw err;
          }
        },

        register: async (username, email, password) => {
          set({ loading: true, error: null });
          try {
            const res = await authService.register({ username, email, password });
            set({
              token: res.access_token,
              refreshToken: res.refresh_token,
              user: {
                id: res.user.id,
                name: res.user.username,
                email: res.user.email,
                role: res.user.role,
              },
              isAuthenticated: true,
              loading: false,
            });
          } catch (err) {
            const msg = err instanceof Error ? err.message : 'Registration failed';
            set({ error: msg, loading: false });
            throw err;
          }
        },

        logout: async () => {
          try {
            const token = get().refreshToken;
            if (token) {
              await authService.logout();
            }
          } catch {
          } finally {
            set({
              token: null,
              refreshToken: null,
              user: null,
              isAuthenticated: false,
              loading: false,
              error: null,
            });
          }
        },

        refreshSession: async () => {
          const refreshToken = get().refreshToken;
          if (!refreshToken) return;
          try {
            const res = await authService.refreshToken(refreshToken);
            set({
              token: res.access_token,
              refreshToken: res.refresh_token,
              isAuthenticated: true,
            });
          } catch {
            set({ token: null, refreshToken: null, isAuthenticated: false, user: null });
          }
        },

        clearError: () => set({ error: null }),

        hasPermission: (_permission: string) => {
          const user = get().user;
          if (!user) return false;
          if (user.role === 'admin') return true;
          return false;
        },

        hasRole: (role: string) => {
          return get().user?.role === role;
        },
      }),
      {
        name: 'climber-auth',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          token: state.token,
          refreshToken: state.refreshToken,
          user: state.user,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    ),
    { name: 'AuthStore' }
  )
);
