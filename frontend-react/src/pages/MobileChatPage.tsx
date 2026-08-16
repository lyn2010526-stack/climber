import { useCallback, useState } from 'react';
import { toast } from 'sonner';
import { MessageSquare, PanelLeft } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { ChatInterface } from '../components/agent/ChatInterface';
import { MobileSessionDrawer } from '../components/mobile/MobileSessionDrawer';
import { useChat, type Message } from '../useChat';
import { useWorkspaceStore } from '../store/workspace';

export function MobileChatPage() {
  const { activeSessionId, sessions } = useWorkspaceStore(useShallow(s => ({
    activeSessionId: s.activeSessionId,
    sessions: s.sessions,
  })));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  const handleSend = useCallback(async (message: string, model?: { provider?: string; modelId?: string }) => {
    if (!activeSessionId) {
      toast.error('请先创建或选择一个会话');
      return;
    }
    await sendMessage(message, model);
  }, [activeSessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-white/[0.04]"
        style={{
          backgroundColor: 'var(--color-glass-bg)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquare size={15} className="shrink-0 text-[var(--color-accent)]" />
          <span
            className="text-sm font-medium truncate"
            style={{ color: activeSession ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}
          >
            {activeSession?.title || '新建或选择会话'}
          </span>
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl text-xs font-semibold shrink-0 transition-all duration-200 active:scale-[0.95]"
          style={{
            backgroundColor: 'var(--color-accent-subtle)',
            color: 'var(--color-accent)',
          }}
        >
          <PanelLeft size={15} strokeWidth={2.5} />
          会话
        </button>
      </div>

      <div className="flex-1 min-h-0">
        <ChatInterface
          className="h-full"
          messages={messages as Message[]}
          onSend={handleSend}
          onStop={handleStop}
          isLoading={isStreaming}
          emptyStateTitle="开始新的对话"
          emptyStateDescription="输入任何问题或任务，Climber 将为你自主执行。"
          suggestions={['帮我分析代码', '写一个 Python 脚本', '解释这个错误']}
        />
      </div>

      {drawerOpen && (
        <MobileSessionDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
      )}

      {error && (
        <div className="absolute bottom-20 left-4 right-4 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-3 text-sm text-red-400 backdrop-blur-xl">
          {error}
        </div>
      )}
    </div>
  );
}
