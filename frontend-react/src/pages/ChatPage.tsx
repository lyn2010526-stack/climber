import { useCallback } from 'react';
import { ChatInterface } from '../components/agent/ChatInterface';
import { useChat } from '../useChat';
import { useDefaultSession } from '../hooks/useDefaultSession';
import { useI18n } from '../i18n';

export function ChatPage() {
  const { t } = useI18n();
  const { sessionId, creationError } = useDefaultSession();
  const { messages, isStreaming, error, sendMessage, stopStreaming, refresh } = useChat(sessionId);

  const handleSend = useCallback(async (message: string) => {
    if (!sessionId) return;
    await sendMessage(message);
  }, [sessionId, sendMessage]);

  const handleStop = useCallback(() => {
    stopStreaming();
  }, [stopStreaming]);

  const failure = error || creationError;

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[var(--color-bg-page)]" aria-label={t('chat.aria_label')} aria-busy={isStreaming}>
      {/* The composer is a fixed-height flex child, so a floating banner would
          cover it. Keeping the alert in flow places it above the transcript. */}
      {failure && (
        <div role="alert" className="flex shrink-0 flex-wrap items-center gap-3 border-b border-[var(--color-error)]/30 px-4 py-2 text-sm text-[var(--color-error)] md:px-6">
          <span className="min-w-0 [overflow-wrap:anywhere]">{failure}</span>
          {error && (
            <button type="button" onClick={refresh} className="min-h-11 shrink-0 px-3 font-medium">
              {t('common.retry')}
            </button>
          )}
        </div>
      )}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatInterface
          messages={messages}
          onSend={handleSend}
          onStop={handleStop}
          isLoading={isStreaming}
          emptyStateTitle={t('chat.empty_state_title')}
          emptyStateDescription=""
        />
      </div>
    </section>
  );
}
