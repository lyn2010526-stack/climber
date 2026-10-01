import { useCallback } from 'react';
import { MobileChatInterface } from '../components/mobile/MobileChatInterface';
import { useChat } from '../useChat';
import { useDefaultSession } from '../hooks/useDefaultSession';
import { cacheManager } from '../components/mobile/LazyImage';

export function MobileChatPage() {
  const { sessionId, creationError } = useDefaultSession();
  const { messages, isStreaming, error, sendMessage, stopStreaming, refresh } = useChat(sessionId);

  const handleSend = useCallback(async (message: string, attachments?: string[]) => {
    if (!sessionId) throw new Error(creationError || '会话尚未就绪，请稍后重试');
    if (attachments?.length) {
      await sendMessage(message, attachments);
    } else {
      await sendMessage(message);
    }
    void cacheManager.set(`last_message_${sessionId}`, {
      text: message,
      timestamp: Date.now(),
      sessionId,
    }).catch(() => undefined);
  }, [sessionId, creationError, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  // The mobile shell owns keyboard clamping and the navigation reserve, so the
  // page only fills the content box. Nothing here measures the viewport, which
  // keeps the composer mounted and the draft intact across resize events.
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      <MobileChatInterface
        messages={messages}
        onSend={handleSend}
        onStop={handleStop}
        isLoading={isStreaming}
        disabled={!sessionId}
        error={error || creationError}
        sessionId={sessionId}
        onRefresh={refresh}
      />
    </div>
  );
}
