import { useRef, useEffect, useCallback, useState } from 'react';
import { cn } from '../../lib/utils';
import { MessageBubble, type Message } from './MessageBubble';
import { ToolCallCard } from './ToolCallCard';
import { ThinkingBlock } from './ThinkingBlock';
import { EmptyState } from './EmptyState';
import { ChatInput } from './ChatInput';
import { ErrorMessage } from './ErrorMessage';
import { ThinkingIndicator } from '../agent/ThinkingIndicator';

interface ChatMessagesProps {
  messages: Message[];
  isStreaming?: boolean;
  error?: string | null;
  onSend: (message: string) => void;
  onStop?: () => void;
  onCopy?: (content: string) => void;
  onEdit?: (id: string, content: string) => void;
  onRegenerate?: (id: string) => void;
  onQuote?: (content: string) => void;
  onDelete?: (id: string) => void;
  onFeedback?: (id: string, type: 'up' | 'down') => void;
  onRetry?: () => void;
  onDismissError?: () => void;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  className?: string;
}

export function ChatMessages({
  messages,
  isStreaming,
  error,
  onSend,
  onStop,
  onCopy,
  onEdit,
  onRegenerate,
  onQuote,
  onDelete,
  onFeedback,
  onRetry,
  onDismissError,
  emptyStateTitle = '开始新的对话',
  emptyStateDescription = '输入任何问题或任务，AI 助手将为你自主执行。',
  className,
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [quotedMessage, setQuotedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleQuote = useCallback((content: string) => {
    setQuotedMessage(content.length > 100 ? content.slice(0, 100) + '...' : content);
  }, []);

  const lastMessage = messages[messages.length - 1];
  const showThinkingIndicator = isStreaming && (!lastMessage || lastMessage.role !== 'assistant');

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Messages scroll area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-8 py-6 chat-container"
      >
        {messages.length === 0 && !isStreaming ? (
          <EmptyState
            title={emptyStateTitle}
            description={emptyStateDescription}
            onSelectSuggestion={onSend}
          />
        ) : (
          <div className="space-y-5">
            {messages.map((msg, idx) => {
              const isLast = idx === messages.length - 1;
              const isLastAssistant = isLast && msg.role === 'assistant';

              return (
                <div key={msg.id} className="space-y-2">
                  {/* Reasoning / Thinking */}
                  {msg.reasoning && !msg.content && (
                    <ThinkingBlock content={msg.reasoning} isComplete={!isStreaming || !isLast} />
                  )}

                  {/* Tool calls without content */}
                  {!msg.content && msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="space-y-2">
                      {msg.toolCalls.map((tc) => (
                        <ToolCallCard
                          key={tc.id}
                          name={tc.name}
                          arguments={tc.arguments}
                          result={tc.result}
                          error={tc.error}
                          isRunning={tc.status === 'running'}
                          duration={tc.duration}
                        />
                      ))}
                    </div>
                  )}

                  {/* Text content */}
                  {msg.content && (
                    <MessageBubble
                      message={{
                        ...msg,
                        isStreaming: isLastAssistant && isStreaming,
                      }}
                      onCopy={onCopy}
                      onEdit={onEdit ? (id, content) => onEdit(id, content) : undefined}
                      onRegenerate={onRegenerate ? () => onRegenerate(msg.id) : undefined}
                      onQuote={handleQuote}
                      onDelete={onDelete ? () => onDelete(msg.id) : undefined}
                      onFeedback={onFeedback ? (id, type) => onFeedback(id, type) : undefined}
                    />
                  )}

                  {/* Tool calls with content */}
                  {msg.content && msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="space-y-2 ml-11">
                      {msg.toolCalls.map((tc) => (
                        <ToolCallCard
                          key={tc.id}
                          name={tc.name}
                          arguments={tc.arguments}
                          result={tc.result}
                          error={tc.error}
                          isRunning={tc.status === 'running'}
                          duration={tc.duration}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Streaming: show thinking indicator */}
            {showThinkingIndicator && (
              <div className="flex gap-3" style={{ maxWidth: '85%' }}>
                <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-[#5E6AD2]/50 to-[#8B5CF6]/50 shrink-0">
                  <span className="text-white/70 text-xs font-bold">AI</span>
                </div>
                <ThinkingIndicator sparkle />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 pb-2">
          <ErrorMessage
            error={error}
            onRetry={onRetry}
            onDismiss={onDismissError}
            retryCount={0}
            maxRetries={3}
          />
        </div>
      )}

      {/* Input area */}
      <ChatInput
        onSend={(msg) => onSend(msg)}
        onStop={onStop}
        isLoading={isStreaming}
        quotedMessage={quotedMessage}
        onCancelQuote={() => setQuotedMessage(null)}
      />
    </div>
  );
}
