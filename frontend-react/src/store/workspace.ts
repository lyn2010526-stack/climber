import { create } from 'zustand';
import type { DisplayMessage } from '../types/message';

export type { DisplayMessage } from '../types/message';

export interface Session {
  id: string;
  title: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  messages: DisplayMessage[];
  activeSkills: string[];
  activeTools: string[];
  modelConfig: {
    provider: string;
    modelId: string;
    temperature: number;
    maxTokens: number;
  };
  tokenUsage: {
    used: number;
    limit: number;
  };
  createdAt: number;
}

export interface TaskItem {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface WorkspaceState {
  sessions: Session[];
  activeSessionId: string | null;
  rightPanelTab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files' | 'tasks';
  rightPanelOpen: boolean;
  focusMode: boolean;
  expertMode: boolean;
  permissionMode: 'sandbox' | 'native';
  autonomyLevel: number;
  tasks: TaskItem[];
  snapshots: Array<{ id: string; sessionId: string; timestamp: number; label: string }>;

  setActiveSession: (id: string | null) => void;
  setSessions: (sessions: Session[]) => void;
  setRightPanelTab: (tab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files' | 'tasks') => void;
  toggleRightPanel: () => void;
  toggleFocusMode: () => void;
  toggleExpertMode: () => void;
  setPermissionMode: (mode: 'sandbox' | 'native') => void;
  setAutonomyLevel: (level: number) => void;
  setTasks: (tasks: TaskItem[]) => void;
  addMessage: (sessionId: string, message: DisplayMessage) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  addSnapshot: (snapshot: { id: string; sessionId: string; timestamp: number; label: string }) => void;
  createSession: (session: Session) => void;
  deleteSession: (id: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  sessions: [],
  activeSessionId: null,
  rightPanelTab: 'toolcalls',
  rightPanelOpen: false,
  focusMode: false,
  expertMode: false,
  permissionMode: 'sandbox',
  autonomyLevel: 3,
  tasks: [],
  snapshots: [],

  setActiveSession: (id) => set({ activeSessionId: id }),
  setSessions: (sessions) => set({ sessions }),
  setRightPanelTab: (tab) => set({ rightPanelTab: tab, rightPanelOpen: true }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  toggleFocusMode: () => set((s) => ({ focusMode: !s.focusMode })),
  toggleExpertMode: () => set((s) => ({ expertMode: !s.expertMode })),
  setPermissionMode: (mode) => set({ permissionMode: mode }),
  setAutonomyLevel: (level) => set({ autonomyLevel: level }),
  setTasks: (tasks) => set({ tasks }),

  addMessage: (sessionId, message) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages: s.messages.some((m) => m.id === message.id)
                ? s.messages.map((m) => (m.id === message.id ? message : m))
                : [...s.messages, message],
            }
          : s
      ),
    })),

  updateSession: (sessionId, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, ...updates } : s
      ),
    })),

  addSnapshot: (snapshot) => set((state) => ({ snapshots: [...state.snapshots, snapshot] })),

  createSession: (session) =>
    set((state) => ({
      sessions: [session, ...state.sessions],
      activeSessionId: session.id,
    })),

  deleteSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      activeSessionId: state.activeSessionId === id ? null : state.activeSessionId,
    })),
}));
