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

/**
 * Every status the backend can report for a session. `idle` and `pending` are
 * both written by the sessions API (creation stores `idle`, the column default
 * is `pending`) and `app/core/__init__.py:SessionStatus` owns the rest.
 * `unknown` is the only state the frontend may invent, and it exists so an
 * unrecognised backend value stays visibly unreported instead of being
 * rewritten into a state the backend never produced.
 */
export type SessionStatus =
  | 'pending'
  | 'idle'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'stopped'
  | 'unknown';

export interface SessionModelConfig {
  provider?: string;
  modelId?: string;
  temperature?: number;
  maxTokens?: number;
}

export interface SessionTokenUsage {
  used?: number;
  limit?: number;
}

export interface Session {
  id: string;
  title: string | null;
  status: SessionStatus;
  messages: Message[];
  activeSkills: string[];
  activeTools: string[];
  /** Model identity as reported by the backend. Every field is optional because
   *  `SessionOut` carries provider/model_id only, and reports nothing at all
   *  about temperature or max tokens. */
  modelConfig?: SessionModelConfig;
  /** Token accounting. Absent until a backend payload actually reports it; a
   *  fabricated `{ used: 0, limit: 200000 }` would read as a real budget. */
  tokenUsage?: SessionTokenUsage;
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

export const SESSION_STATUSES: readonly SessionStatus[] = [
  'pending',
  'idle',
  'running',
  'paused',
  'completed',
  'failed',
  'stopped',
];

/**
 * Map any backend status string onto the canonical lifecycle. A recognised
 * value is passed through untouched; everything else — including `null`, an
 * empty string and any state a newer backend may add — resolves to
 * `unknown`, which every surface renders as "not reported".
 */
export function normalizeSessionStatus(status: string | null | undefined): SessionStatus {
  const candidate = typeof status === 'string' ? status.trim().toLowerCase() : '';
  return SESSION_STATUSES.includes(candidate as SessionStatus)
    ? (candidate as SessionStatus)
    : 'unknown';
}

function backendModelOverrides(backend: ApiSession): SessionModelConfig {
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
  const overrides: SessionModelConfig = {};
  if (provider) overrides.provider = provider;
  if (modelId) overrides.modelId = modelId;
  return overrides;
}

/** Merge backend model identity over locally known values, or nothing at all. */
function mergeModelConfig(
  existing: SessionModelConfig | undefined,
  overrides: SessionModelConfig,
): SessionModelConfig | undefined {
  const merged = { ...existing, ...overrides };
  return Object.values(merged).some((value) => value !== undefined) ? merged : undefined;
}

/**
 * Build runtime fields for a session that only exists on the backend. Only what
 * the payload carries is filled in: model identity comes from provider /
 * model_id, and token usage stays absent because `SessionOut` reports none.
 */
export function sessionFromBackend(backend: ApiSession): Session {
  const parsed = backend.created_at ? Date.parse(backend.created_at) : NaN;
  return {
    id: backend.id,
    title: backend.title ?? null,
    status: normalizeSessionStatus(backend.status),
    messages: [],
    activeSkills: [],
    activeTools: [],
    modelConfig: mergeModelConfig(undefined, backendModelOverrides(backend)),
    createdAt: Number.isNaN(parsed) ? Date.now() : parsed,
  };
}

export interface TaskItem {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

/**
 * A point the session can be brought back to. The captured transcript is what
 * makes a snapshot restorable, so a snapshot without one is recorded honestly as
 * a marker and never offered as a rollback target.
 */
export interface SessionSnapshot {
  id: string;
  sessionId: string;
  timestamp: number;
  label: string;
  messages?: Message[];
}

/**
 * Permission mode exactly as `app/core/permission_rules.py:PermissionMode`
 * spells it, because that is the vocabulary `GET/PUT /permissions/config`
 * accepts and returns. `null` in the store means the backend has not reported
 * one, which every control renders as "not reported".
 */
export type PermissionMode =
  | 'default'
  | 'acceptEdits'
  | 'plan'
  | 'auto'
  | 'bypass'
  | 'strict';

/** Lifecycle of the permission-config request that fills {@link permissionMode}. */
export type PermissionConfigStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface WorkspaceState {
  sessions: Session[];
  sessionsLoaded: boolean;
  loadingSessions: boolean;
  activeSessionId: string | null;
  rightPanelTab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files';
  /**
   * Bumped on every tab request. A repeated request for the tab already in view
   * is a fresh instruction, so consumers that react to a tab need a counter to
   * tell it apart from a re-render or from a panel that simply reopened.
   */
  rightPanelTabNonce: number;
  rightPanelOpen: boolean;
  focusMode: boolean;
  expertMode: boolean;
  /** Mirrors GET /permissions/config. `null` until the backend answers. */
  permissionMode: PermissionMode | null;
  permissionConfigStatus: PermissionConfigStatus;
  /** Last reason the permission config could not be read or written. */
  permissionConfigError: string | null;
  tasks: TaskItem[];
  snapshots: SessionSnapshot[];

  setActiveSession: (id: string | null) => void;
  setRightPanelTab: (tab: 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files') => void;
  toggleRightPanel: () => void;
  toggleFocusMode: () => void;
  toggleExpertMode: () => void;
  setPermissionMode: (mode: PermissionMode | null) => void;
  setPermissionConfigStatus: (status: PermissionConfigStatus) => void;
  setPermissionConfigError: (message: string | null) => void;
  setTasks: (tasks: TaskItem[]) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  addSnapshot: (snapshot: SessionSnapshot) => void;
  /**
   * Put a session's transcript back to a snapshot. Async so the caller can await
   * the outcome and keep a failure on screen; the store's own work is immediate.
   * Rejects when the snapshot or its session is gone, or when the snapshot
   * carries no transcript, because a rollback that cannot restore anything would
   * report a success it did not perform.
   */
  restoreSnapshot: (snapshotId: string) => Promise<void>;
  createSessionLocal: (session: Session) => void;
  createSession: (session: Session) => void;
  deleteSession: (id: string) => void;
  loadSessions: (backendSessions: ApiSession[]) => void;
  setSessionsLoading: (loading: boolean) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  sessions: [],
  sessionsLoaded: false,
  loadingSessions: false,
  activeSessionId: null,
  rightPanelTab: 'config',
  rightPanelTabNonce: 0,
  rightPanelOpen: true,
  focusMode: false,
  expertMode: false,
  permissionMode: null,
  permissionConfigStatus: 'idle',
  permissionConfigError: null,
  tasks: [],
  snapshots: [],

  setActiveSession: (id) => set({ activeSessionId: id }),
  setRightPanelTab: (tab) =>
    set((s) => ({
      rightPanelTab: tab,
      rightPanelOpen: true,
      rightPanelTabNonce: s.rightPanelTabNonce + 1,
    })),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  toggleFocusMode: () => set((s) => ({ focusMode: !s.focusMode })),
  toggleExpertMode: () => set((s) => ({ expertMode: !s.expertMode })),
  setPermissionMode: (mode) => set({ permissionMode: mode }),
  setPermissionConfigStatus: (status) => set({ permissionConfigStatus: status }),
  setPermissionConfigError: (message) => set({ permissionConfigError: message }),
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

  restoreSnapshot: async (snapshotId) => {
    const { snapshots, sessions } = get();
    const snapshot = snapshots.find(entry => entry.id === snapshotId);
    if (!snapshot) throw new Error('Snapshot not found');
    const captured = snapshot.messages;
    if (!captured) throw new Error('Snapshot carries no transcript to restore');
    if (!sessions.some(session => session.id === snapshot.sessionId)) {
      throw new Error('Snapshot session no longer exists');
    }
    set(state => ({
      sessions: state.sessions.map(session =>
        session.id === snapshot.sessionId ? { ...session, messages: [...captured] } : session
      ),
    }));
  },

  createSessionLocal: (session) =>
    set((state) => ({
      sessions: state.sessions.some((s) => s.id === session.id)
        ? state.sessions.map((s) => (s.id === session.id ? { ...s, ...session } : s))
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
   * - Existing sessions keep local runtime fields (messages, skills, tools).
   * - Status and model identity always come from the backend; anything it does
   *   not report stays absent instead of being filled in with a placeholder.
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
          modelConfig: mergeModelConfig(existing.modelConfig, backendModelOverrides(backend)),
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
