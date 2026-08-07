import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Square, Loader2, Bot } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp?: Date;
}

interface MobileChatInterfaceProps {
  messages: Message[];
  onSend: (message: string) => Promise<void>;
  onStop?: () => void;
  isLoading?: boolean;
  isRefreshing?: boolean;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  suggestions?: string[];
}

export function MobileChatInterface({
  messages,
  onSend,
  onStop,
  isLoading,
  isRefreshing,
  emptyStateTitle = '开始新的对话',
  emptyStateDescription = '输入任何问题或任务，Climber 将为你自主执行。',
  suggestions = ['帮我分析代码', '写一个 Python 脚本', '解释这个错误'],
}: MobileChatInterfaceProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isScrolling = useRef(false);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (scrollRef.current) {
      const smoothScroll = () => {
        if (!scrollRef.current) return;
        isScrolling.current = true;
        const el = scrollRef.current;
        el.scrollTo({
          top: el.scrollHeight,
          behavior: 'smooth'
        });
        
        clearTimeout(scrollTimeout.current);
        scrollTimeout.current = setTimeout(() => {
          isScrolling.current = false;
        }, 100);
      };
      
      // Use setTimeout to ensure DOM is updated
      setTimeout(smoothScroll, 50);
    }
  }, [messages, isLoading]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!input.trim() || isLoading) return;
    
    const message = input.trim();
    setInput('');
    
    try {
      await onSend(message);
    } catch (error) {
      console.error('发送消息失败:', error);
    }
    
    // Focus back on input
    inputRef.current?.focus();
  };

  const handleSuggestionClick = async (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-full bg-page">
      {/* Messages Container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto mobile-scroll-optimized"
        style={{
          padding: '16px',
          paddingBottom: '80px',
        }}
        onTouchStart={() => { isScrolling.current = true; }}
        onTouchEnd={(e) => {
          // Auto-scroll if user released at bottom
          const scrollTop = e.currentTarget.scrollTop;
          const scrollHeight = e.currentTarget.scrollHeight;
          const clientHeight = e.currentTarget.clientHeight;
          
          if (scrollHeight - scrollTop - clientHeight < 100) {
            setTimeout(() => {
              if (!isScrolling.current) {
                e.currentTarget.scrollTo({
                  top: e.currentTarget.scrollHeight,
                  behavior: 'smooth'
                });
              }
            }, 100);
          }
        }}
      >
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[60vh] px-4 text-center">
              <div className="w-16 h-16 rounded-3xl mb-4 flex items-center justify-center" style={{
                background: 'linear-gradient(135deg, var(--color-accent), #8B5CF6)',
                boxShadow: '0 0 30px var(--color-accent-glow)'
              }}>
                <Bot size={32} className="text-white" />
              </div>
              <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                {emptyStateTitle}
              </h2>
              <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
                {emptyStateDescription}
              </p>
              
              {suggestions && suggestions.length > 0 && (
                <div className="grid grid-cols-1 gap-2 w-full max-w-md">
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="mobile-touch-target flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 active:scale-[0.98]"
                      style={{
                        backgroundColor: 'var(--color-bg-surface-1)',
                        border: '1px solid var(--color-border-subtle)',
                        color: 'var(--color-text-secondary)'
                      }}
                    >
                      <span className="text-xs" style={{ opacity: 0.6 }}>{'>'}</span>
                      <span className="text-sm font-medium">{suggestion}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-4 py-3 rounded-2xl transition-all duration-200 ${
                    message.role === 'user' 
                      ? 'mobile-icon-button' 
                      : ''
                  }`}
                  style={{
                    backgroundColor: message.role === 'user' 
                      ? 'var(--color-accent)' 
                      : 'var(--color-bg-surface-1)',
                    color: message.role === 'user'
                      ? 'var(--color-accent-text)'
                      : 'var(--color-text-primary)',
                    border: message.role === 'assistant'
                      ? '1px solid var(--color-border-subtle)'
                      : 'none',
                  }}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {message.content}
                  </p>
                  {message.timestamp && (
                    <p className="text-[10px] mt-1 opacity-70">
                      {message.timestamp.toLocaleTimeString('zh-CN', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 px-4 py-3 rounded-2xl" style={{
                backgroundColor: 'var(--color-bg-surface-1)',
                border: '1px solid var(--color-border-subtle)',
              }}>
                <Loader2 size={16} className="animate-spin" style={{ color: 'var(--color-accent)' }} />
                <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>正在思考...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <form
        onSubmit={handleSubmit}
        className="fixed bottom-0 left-0 right-0 z-40 safe-area-bottom mobile-content-shift-fix"
        style={{
          padding: `12px 16px calc(12px + env(safe-area-inset-bottom, 0px))`,
          backgroundColor: 'rgba(10,10,15,0.95)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderTop: '1px solid var(--color-border-subtle)',
        }}
      >
        <div className="flex items-end gap-2 max-w-none">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            rows={1}
            className="flex-1 mobile-chat-input resize-none mobile-touch-target"
            style={{ fontSize: '16px' }}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="mobile-icon-button rounded-full transition-all duration-200 active:scale-[0.92]"
            style={{
              backgroundColor: !input.trim() || isLoading
                ? 'var(--color-bg-surface-2)'
                : 'var(--color-accent)',
              color: !input.trim() || isLoading
                ? 'var(--color-text-muted)'
                : 'var(--color-accent-text)',
            }}
            aria-label="发送消息"
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
          
          {onStop && !isLoading && messages.some(m => m.role === 'assistant') && (
            <button
              type="button"
              onClick={onStop}
              className="mobile-icon-button rounded-full transition-all duration-200 active:scale-[0.92]"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                color: 'var(--color-error)',
              }}
              aria-label="停止生成"
            >
              <Square size={20} />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
