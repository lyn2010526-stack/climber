import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  setAuthenticated: (isAuthenticated: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: Boolean(localStorage.getItem('auth_token')),
  setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
}));
