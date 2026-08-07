import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { chatService, type ChatSession, type ChatMessage, type StreamEvent } from '../services/chatService';

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  abortFn: (() => void) | null;

  fetchSessions: () => Promise<void>;
  createSession: (data?: { title?: string; agent_id?: string }) => Promise<ChatSession>;
  deleteSession: (id: string) => Promise<void>;
  setActiveSession: (sessionId: string | null) => void;
  sendMessage: (content: string, options?: { agent_id?: string }) => Promise<void>;
  stopStreaming: () => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,
      messages: [],
      isStreaming: false,
      error: null,
      abortFn: null,

      fetchSessions: async () => {
        try {
          const sessions = await chatService.listSessions();
          set({ sessions });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch sessions',
          });
        }
      },

      createSession: async (data) => {
        const session = await chatService.createSession(data);
        set((s) => ({ sessions: [session, ...s.sessions], activeSessionId: session.id }));
        return session;
      },

      deleteSession: async (id) => {
        await chatService.deleteSession(id);
        set((s) => ({
          sessions: s.sessions.filter((sess) => sess.id !== id),
          activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
          messages: s.activeSessionId === id ? [] : s.messages,
        }));
      },

      setActiveSession: (sessionId) => {
        set({ activeSessionId: sessionId, messages: [], error: null });
        if (sessionId) {
          chatService.getMessages(sessionId).then((msgs) => {
            set({ messages: msgs });
          }).catch(() => {
            set({ messages: [] });
          });
        }
      },

      sendMessage: async (content, options) => {
        const { activeSessionId, isStreaming } = get();
        if (isStreaming) return;

        let sessionId = activeSessionId;
        if (!sessionId) {
          const session = await get().createSession(options);
          sessionId = session.id;
        }

        const userMsg: ChatMessage = {
          id: `user-${Date.now()}`,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
        };

        const assistantId = `assistant-${Date.now()}`;
        const assistantMsg: ChatMessage = {
          id: assistantId,
          role: 'assistant',
          content: '',
          tool_calls: [],
          created_at: new Date().toISOString(),
        };

        set((s) => ({
          messages: [...s.messages, userMsg, assistantMsg],
          isStreaming: true,
          error: null,
        }));

        const abortFn = chatService.chatStream(
          sessionId,
          content,
          (event: StreamEvent) => {
            const eventType = event.event;
            const data = event.data as Record<string, unknown>;

            if (eventType === 'text') {
              const delta = typeof data === 'string' ? data : ((data?.content as string) || '');
              set((s) => ({
                messages: s.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: msg.content + delta }
                    : msg
                ),
              }));
            } else if (eventType === 'thinking') {
              set((s) => ({
                messages: s.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, reasoning: ((msg as any).reasoning || '') + ((data?.content as string) || '') }
                    : msg
                ),
              }));
            } else if (eventType === 'tool_call') {
              const tc = {
                id: (data?.id as string) || `tc-${Date.now()}`,
                name: (data?.name as string) || 'unknown',
                arguments: (data?.arguments as Record<string, unknown>) || {},
                status: 'running' as const,
              };
              set((s) => ({
                messages: s.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, tool_calls: [...(msg.tool_calls || []), tc] }
                    : msg
                ),
              }));
            } else if (eventType === 'tool_result') {
              const toolId = data?.id as string;
              set((s) => ({
                messages: s.messages.map((msg) => {
                  if (msg.id !== assistantId) return msg;
                  const updatedToolCalls = msg.tool_calls?.map((tc) =>
                    tc.id === toolId
                      ? { ...tc, result: (data?.result as string) ?? '', error: (data?.error as string) ?? '', status: data?.error ? 'error' as const : 'success' as const }
                      : tc
                  );
                  return { ...msg, tool_calls: updatedToolCalls };
                }),
              }));
            } else if (eventType === 'done') {
              set({ isStreaming: false, abortFn: null });
            } else if (eventType === 'error') {
              const errMsg = typeof data === 'string' ? data : ((data?.detail as string) || (data?.error as string) || 'Unknown error');
              set((s) => ({
                error: errMsg,
                isStreaming: false,
                abortFn: null,
              }));
            }
          },
          options
        );

        set({ abortFn });

        const checkDone = setInterval(() => {
          if (!get().isStreaming) {
            clearInterval(checkDone);
            set({ abortFn: null });
          }
        }, 500);
      },

      stopStreaming: () => {
        const { abortFn } = get();
        if (abortFn) abortFn();
        set({ isStreaming: false, abortFn: null });
      },

      clearMessages: () => set({ messages: [], error: null }),
    }),
    { name: 'ChatStore' }
  )
);
