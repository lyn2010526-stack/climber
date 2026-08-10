import { useCallback } from 'react';
import { toast } from 'sonner';
import { ChatInterface } from '../components/agent/ChatInterface';
import { useChat, type Message } from '../useChat';
import { useWorkspaceStore } from '../store/workspace';

export function ChatPage() {
  const { activeSessionId } = useWorkspaceStore();
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);

  const handleSend = useCallback(async (message: string) => {
    if (!activeSessionId) {
      toast.error('请先创建或选择一个会话');
      return;
    }
    await sendMessage(message);
  }, [activeSessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  return (
    <div className="flex h-full">
      <ChatInterface
        messages={messages as Message[]}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        emptyStateTitle="开始新的对话"
        emptyStateDescription="输入任何问题或任务，Climber 将为你自主执行。"
      />
      {error && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-3 text-sm text-red-400 backdrop-blur-xl">
          {error}
        </div>
      )}
    </div>
  );
}
