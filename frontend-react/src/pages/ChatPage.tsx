import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { ChatInterface } from '../components/agent/ChatInterface';
import { useChat } from '../hooks/useChat';
import { useWorkspaceStore } from '../store/workspace';
import { Alert } from '../components/ui';

export function ChatPage({ onRequestSession }: { onRequestSession?: () => void }) {
  const { activeSessionId } = useWorkspaceStore();
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);
  const [errorVisible, setErrorVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (error) {
      setErrorVisible(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        setErrorVisible(false);
        timerRef.current = null;
      }, 5000);
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [error]);

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
    <div className="flex h-full">
      <ChatInterface
        sessionId={activeSessionId}
        messages={messages}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        emptyStateTitle={activeSessionId ? "开始新的对话" : "需要先创建会话"}
        emptyStateDescription={activeSessionId ? "输入任何问题或任务，Climber 将为你自主执行。" : "创建会话并选择智能体后，即可开始执行任务。"}
        {...(onRequestSession ? { onRequestSession } : {})}
      />
      {error && errorVisible && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 cursor-pointer" onClick={() => setErrorVisible(false)}>
          <Alert variant="destructive" className="backdrop-blur-xl">{error}</Alert>
        </div>
      )}
    </div>
  );
}
