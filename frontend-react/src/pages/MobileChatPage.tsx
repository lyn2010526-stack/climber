import { useCallback, useState } from 'react';
import { MobileChatInterface } from '../components/mobile/MobileChatInterface';
import { useChat, type Message } from '../useChat';
import { useDefaultSession } from '../hooks/useDefaultSession';
import { cacheManager } from '../components/mobile/LazyImage';

export function MobileChatPage() {
  const { sessionId } = useDefaultSession();
  const { messages, isStreaming, error, sendMessage, stopStreaming, refresh } = useChat(sessionId);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleSend = useCallback(async (message: string) => {
    if (!sessionId) return;
    await sendMessage(message);
    await cacheManager.set(`last_message_${sessionId}`, {
      text: message,
      timestamp: Date.now(),
      sessionId,
    });
  }, [sessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      refresh();
      // Give the refreshed message list time to settle before hiding the spinner.
      await new Promise((resolve) => setTimeout(resolve, 400));
    } finally {
      setIsRefreshing(false);
    }
  }, [refresh]);

  return (
    <div className="flex flex-col h-full mobile-touch-feedback">
      <MobileChatInterface
        messages={messages as Message[]}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
      />
      {error && (
        <div className="absolute bottom-20 left-4 right-4 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-3 text-sm text-red-400 backdrop-blur-xl animate-fadeIn">
          {error}
        </div>
      )}
    </div>
  );
}
