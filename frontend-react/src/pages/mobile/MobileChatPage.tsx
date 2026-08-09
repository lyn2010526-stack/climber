import { useState, useEffect, useCallback, useRef } from 'react';
import { ChevronUp, ArrowDown } from 'lucide-react';
import { ChatInterface } from '../../components/agent/ChatInterface';
import { useWorkspaceStore } from '../../store';
import { useChat } from '../../useChat';
import { cn } from '../../lib/utils';
import type { ChatMessage } from '../../store';

export function MobileChatPage() {
  const { activeSessionId } = useWorkspaceStore();
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(activeSessionId);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setShowScrollTop(scrollTop > 300);
      setShowScrollBottom(scrollHeight - scrollTop - clientHeight > 200);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const scrollToBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
  }, []);

  return (
    <div className="mobile-chat flex flex-col h-full relative">
      {/* Error Toast */}
      {error && (
        <div
          className="absolute top-2 left-3 right-3 z-50 rounded-2xl px-4 py-2.5 text-xs backdrop-blur-xl"
          style={{
            backgroundColor: 'var(--color-error-subtle)',
            border: '1px solid rgba(248, 113, 113, 0.3)',
            color: 'var(--color-error)',
          }}
        >
          {error}
        </div>
      )}

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden" ref={scrollContainerRef}>
        <ChatInterface
          messages={messages as ChatMessage[]}
          onSend={handleSend}
          onStop={handleStop}
          isLoading={isStreaming}
          emptyStateTitle="开始新的对话"
          emptyStateDescription="输入任何问题或任务，Climber 将为你自主执行。"
          suggestions={['帮我分析代码', '写一个 Python 脚本', '解释这个错误']}
          className="h-full"
        />
      </div>

      {/* Scroll Controls */}
      <div
        className="fixed right-4 z-50 flex flex-col gap-2"
        style={{ bottom: 'calc(env(safe-area-inset-bottom, 0px) + 80px)' }}
      >
        <button
          onClick={scrollToTop}
          className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center',
            'shadow-lg shadow-black/20 backdrop-blur-xl transition-all duration-300',
            'active:scale-90',
            showScrollTop ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
          )}
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            border: '1px solid var(--color-border-subtle)',
          }}
          aria-label="返回顶部"
        >
          <ChevronUp size={18} style={{ color: 'var(--color-text-secondary)' }} />
        </button>

        <button
          onClick={scrollToBottom}
          className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center',
            'shadow-lg shadow-black/20 backdrop-blur-xl transition-all duration-300',
            'active:scale-90',
            showScrollBottom ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
          )}
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            border: '1px solid var(--color-border-subtle)',
          }}
          aria-label="滚动到底部"
        >
          <ArrowDown size={18} style={{ color: 'var(--color-text-secondary)' }} />
        </button>
      </div>
    </div>
  );
}
