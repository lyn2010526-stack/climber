import { useCallback } from 'react';
import { MobileChatInterface } from '../components/mobile/MobileChatInterface';
import { useChat } from '../useChat';
import { useDefaultSession } from '../hooks/useDefaultSession';
import { useI18n } from '../i18n';
import { cacheManager } from '../components/mobile/LazyImage';
import type { ChatAttachmentPayload } from '../useChat';

export function MobileChatPage() {
  const { t } = useI18n();
  const { sessionId, creationError } = useDefaultSession();
  const { messages, isStreaming, error, sendMessage, stopStreaming, refresh } = useChat(sessionId);

  const handleSend = useCallback(async (message: string, attachments?: string[], files?: ChatAttachmentPayload[]) => {
    if (!sessionId) throw new Error(creationError || t('mobile_chat.session_not_ready'));
    if (attachments?.length) {
      await sendMessage(message, attachments, files);
    } else {
      await sendMessage(message);
    }
    void cacheManager.set(`last_message_${sessionId}`, {
      text: message,
      timestamp: Date.now(),
      sessionId,
    }).catch(() => undefined);
  }, [sessionId, creationError, t, sendMessage]);

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
