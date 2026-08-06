import { create } from 'zustand';

export type Page =
  | 'chat'
  | 'agents'
  | 'workflows'
  | 'crews'
  | 'apikeys'
  | 'skills'
  | 'notifications'
  | 'doctor'
  | 'mcp'
  | 'stats'
  | 'factory'
  | 'plugins'
  | 'plugin-manage'
  | 'scheduler'
  | 'cluster'
  | 'traces'
  | 'eval'
  | 'cost'
  | 'plugin-manage'
  | 'settings'
  | 'tasks'
  | 'task-history'
  | 'reasoning'
  | 'reasoning-history'
  | 'terminal'
  | 'approvals'
  | 'memory';

interface PageState {
  page: Page;
  setPage: (page: Page) => void;
}

export const PROTECTED_PAGES: Page[] = ['chat', 'agents', 'workflows', 'settings'];

export const useCurrentPage = create<PageState>((set) => ({
  page: 'chat',
  setPage: (page) => set({ page }),
}));
