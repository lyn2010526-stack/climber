import { create } from 'zustand';

export interface Message {
  id: string;
  type: 'user' | 'thinking' | 'tool-call' | 'tool-result' | 'reflection' | 'system';
  content: any;
  timestamp: number;
  metadata?: {
    tokens?: number;
    durationMs?: number;
    status?: 'pending' | 'running' | 'success' | 'error' | 'cancelled';
    retryCount?: number;
    blockReason?: string;
    toolName?: string;
    toolArgs?: any;
  };
}

export interface Session {
  id: string;
  title: string | null;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  messages: Message[];
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

/** Session row as returned by GET /api/v1/sessions (backend is the source of truth). */
export interface ApiSession {
  id: string;
  title: string | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  provider?: string | null;
  model_id?: string | null;
  agent_id?: string | null;
}

const SESSION_STATUSES: Session['status'][] = ['idle', 'running', 'paused', 'completed', 'error'];

export function normalizeSessionStatus(status: string | null | undefined): Session['status'] {
  return SESSION_STATUSES.includes(status as Session['status'])
    ? (status as Session['status'])
    : 'idle';
}

function backendModelOverrides(backend: ApiSession): Partial<Session['modelConfig']> {
  let provider = backend.provider ?? undefined;
  let modelId = backend.model_id ?? undefined;
  const rawModel = (backend as { model?: unknown }).model;
  if (!modelId && typeof rawModel === 'string') {
    const raw = rawModel;
    const slash = raw.indexOf('/');
    if (slash > 0 && !provider) {
      provider = raw.slice(0, slash);
      modelId = raw.slice(slash + 1);
    } else {
      modelId = raw;
    }
  }
  const overrides: Partial<Session['modelConfig']> = {};
  if (provider) overrides.provider = provider;
  if (modelId) overrides.modelId = modelId;
  return overrides;
}

/** Build runtime fields for a session that only exists on the backend. */
export function sessionFromBackend(backend: ApiSession): Session {
  const parsed = backend.created_at ? Date.parse(backend.created_at) : NaN;
  return {
    id: backend.id,
    title: backend.title ?? null,
    status: normalizeSessionStatus(backend.status),
    messages: [],
    activeSkills: [],
    activeTools: [],
    modelConfig: {
      provider: 'unknown',
      modelId: '',
      temperature: 0.7,
      maxTokens: 4096,
      ...backendModelOverrides(backend),
    },
    tokenUsage: { used: 0, limit: 200000 },
    createdAt: Number.isNaN(parsed) ? Date.now() : parsed,
  };
}

export interface TaskItem {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface WorkspaceState {
  sessions: Session[];
  sessionsLoaded: boolean;
  loadingSessions: boolean;
  activeSessionId: string | null;
  rightPanelTab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files';
  rightPanelOpen: boolean;
  focusMode: boolean;
  expertMode: boolean;
  permissionMode: 'sandbox' | 'native';
  autonomyLevel: number;
  tasks: TaskItem[];
  snapshots: Array<{ id: string; sessionId: string; timestamp: number; label: string }>;

  setActiveSession: (id: string | null) => void;
  setRightPanelTab: (tab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files') => void;
  toggleRightPanel: () => void;
  toggleFocusMode: () => void;
  toggleExpertMode: () => void;
  setPermissionMode: (mode: 'sandbox' | 'native') => void;
  setAutonomyLevel: (level: number) => void;
  setTasks: (tasks: TaskItem[]) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  addSnapshot: (snapshot: { id: string; sessionId: string; timestamp: number; label: string }) => void;
  createSessionLocal: (session: Session) => void;
  createSession: (session: Session) => void;
  deleteSession: (id: string) => void;
  loadSessions: (backendSessions: ApiSession[]) => void;
  setSessionsLoading: (loading: boolean) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  sessions: [],
  sessionsLoaded: false,
  loadingSessions: false,
  activeSessionId: null,
  rightPanelTab: 'config',
  rightPanelOpen: true,
  focusMode: false,
  expertMode: false,
  permissionMode: 'sandbox',
  autonomyLevel: 3,
  tasks: [],
  snapshots: [],

  setActiveSession: (id) => set({ activeSessionId: id }),
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

  createSessionLocal: (session) =>
    set((state) => ({
      sessions: state.sessions.some((s) => s.id === session.id)
        ? state.sessions.map((s) => (s.id === session.id ? { ...session, ...s } : s))
        : [session, ...state.sessions],
      activeSessionId: session.id,
    })),

  // Backwards-compatible alias; prefer createSessionLocal / loadSessions.
  createSession: (session) => set((state) => ({
    sessions: [session, ...state.sessions],
    activeSessionId: session.id,
  })),

  deleteSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      activeSessionId: state.activeSessionId === id ? null : state.activeSessionId,
    })),

  setSessionsLoading: (loading) => set({ loadingSessions: loading }),

  /**
   * Merge the authoritative backend session list into runtime state.
   * - Existing sessions keep local runtime fields (messages, tokenUsage, skills, tools).
   * - New backend sessions get default runtime fields.
   * - Sessions missing from the backend are removed.
   * - activeSessionId is cleared when it no longer points at an existing session.
   */
  loadSessions: (backendSessions) =>
    set((state) => {
      const existingById = new Map(state.sessions.map((s) => [s.id, s]));
      const merged = backendSessions.map((backend) => {
        const existing = existingById.get(backend.id);
        if (!existing) return sessionFromBackend(backend);
        return {
          ...existing,
          title: backend.title ?? null,
          status: normalizeSessionStatus(backend.status),
          modelConfig: {
            ...existing.modelConfig,
            ...backendModelOverrides(backend),
          },
        };
      });
      const stillExists = merged.some((s) => s.id === state.activeSessionId);
      return {
        sessions: merged,
        sessionsLoaded: true,
        loadingSessions: false,
        activeSessionId: stillExists ? state.activeSessionId : null,
      };
    }),
}));
