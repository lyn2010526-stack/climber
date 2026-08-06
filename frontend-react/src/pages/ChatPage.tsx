import { useCallback } from 'react';
import { ChatInterface } from '../components/agent/ChatInterface';
import { useChat, type Message } from '../useChat';
import { useWorkspaceStore } from '../store/workspace';

export function ChatPage() {
  const { activeSessionId } = useWorkspaceStore();
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);

  const handleSend = useCallback(async (message: string) => {
    if (!activeSessionId) {
      alert('请先创建或选择一个会话');
      return;
    }
    await sendMessage(message);
  }, [activeSessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  return (
    <section className="relative flex h-full min-w-0 bg-[var(--color-bg-page)]" aria-label="对话内容" aria-busy={isStreaming}>
      <ChatInterface
        messages={messages as Message[]}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        emptyStateTitle="开始新的对话"
        emptyStateDescription="输入任何问题或任务，Climber 将为你自主执行。"
      />
      {error && (
        <div role="alert" className="absolute bottom-24 left-1/2 z-20 flex max-w-[calc(100%-2rem)] -translate-x-1/2 items-center gap-3 rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-bg-surface-1)] px-4 py-3 text-sm text-[var(--color-error)] shadow-lg">
          <span className="min-w-0">{error}</span>
          <button type="button" onClick={() => window.location.reload()} className="min-h-11 shrink-0 px-3 font-medium">重试</button>
        </div>
      )}
    </section>
  );
}
