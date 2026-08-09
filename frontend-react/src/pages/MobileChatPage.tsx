import { useCallback, useState } from 'react';
import { MobileChatInterface } from '../components/mobile/MobileChatInterface';
import { useChat, type Message } from '../useChat';
import { useWorkspaceStore } from '../store/workspace';

export function MobileChatPage() {
  const { activeSessionId } = useWorkspaceStore();
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleSend = useCallback(async (message: string) => {
    if (!activeSessionId) {
      alert('请先创建或选择一个会话');
      return;
    }
    
    await sendMessage(message);
    
    // Cache the last message for offline support
    localStorage.setItem(`last_message_${activeSessionId}`, JSON.stringify({
      text: message,
      timestamp: Date.now(),
      sessionId: activeSessionId
    }));
  }, [activeSessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Simulate refresh delay with smooth animation
      await new Promise(resolve => setTimeout(resolve, 800));
      // Refresh messages could be implemented here
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col h-full mobile-touch-feedback">
      <MobileChatInterface
        messages={messages as Message[]}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        isRefreshing={isRefreshing}
      />
      {error && (
        <div className="absolute bottom-20 left-4 right-4 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-3 text-sm text-red-400 backdrop-blur-xl animate-fadeIn">
          {error}
        </div>
      )}
    </div>
  );
}
