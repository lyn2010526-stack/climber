import { useState, useRef, useLayoutEffect, useEffect } from 'react';
import { ArrowDown, Send, Square, Loader2, RefreshCw } from 'lucide-react';
import { formatTime } from '../../i18n/utils';
import type { Message } from '../../useChat';
import { ChatComposerTools } from '../chat/ChatComposerTools';
import { useChatVisuals } from '../../hooks/useChatVisuals';

interface MobileChatInterfaceProps {
  messages: Message[];
  onSend: (message: string) => Promise<void>;
  onStop?: () => void;
  isLoading?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void | Promise<void>;
  disabled?: boolean;
  error?: string | null;
  /** Session id for the composer tools (model, thinking level, display switches). */
  sessionId?: string | null;
  emptyStateTitle?: string;
}

// Matches the `min-h-11` class on the composer so sending an empty draft does
// not shrink the input.
const MIN_INPUT_HEIGHT = 44;
const MAX_INPUT_HEIGHT = 128;
// Distance from the tail that still counts as "following the conversation".
const FOLLOW_THRESHOLD = 64;
// Safari emits the confirming Enter right after compositionend, so that single
// keystroke has to be swallowed. Other engines report composition through
// `isComposing` and `keyCode === 229` and need no time window.
const COMPOSITION_GUARD_MS = 500;
const COMPOSER_PADDING = 12;

function isSafariEngine(): boolean {
  return typeof navigator !== 'undefined' && /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
}

export function MobileChatInterface({
  messages, onSend, onStop, isLoading, isRefreshing, onRefresh,
  disabled, error, sessionId, emptyStateTitle = '新对话',
}: MobileChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [awayFromBottom, setAwayFromBottom] = useState(false);
  const [missedCount, setMissedCount] = useState(0);
  // Transcript display preferences. One hook instance here; the flags gate
  // reasoning and tool-call rendering and feed ChatComposerTools.
  const { visuals, setShowToolCalls, setShowThinking } = useChatVisuals();
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const followRef = useRef(true);
  const sendingRef = useRef(false);
  const composingRef = useRef(false);
  const compositionEndRef = useRef(-Infinity);
  const messageCountRef = useRef(messages.length);

  useEffect(() => {
    const inputEl = inputRef.current;
    const viewport = window.visualViewport;
    if (!inputEl) return;
    let frame = 0;
    const syncKeyboard = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const height = viewport?.height ?? window.innerHeight;
        const keyboardVisible = document.activeElement === inputEl && height < window.innerHeight - 80;
        setKeyboardOpen(current => current === keyboardVisible ? current : keyboardVisible);
      });
    };
    syncKeyboard();
    inputEl.addEventListener('focus', syncKeyboard);
    inputEl.addEventListener('blur', syncKeyboard);
    viewport?.addEventListener('resize', syncKeyboard);
    viewport?.addEventListener('scroll', syncKeyboard);
    window.addEventListener('resize', syncKeyboard);
    return () => {
      cancelAnimationFrame(frame);
      inputEl.removeEventListener('focus', syncKeyboard);
      inputEl.removeEventListener('blur', syncKeyboard);
      viewport?.removeEventListener('resize', syncKeyboard);
      viewport?.removeEventListener('scroll', syncKeyboard);
      window.removeEventListener('resize', syncKeyboard);
    };
  }, []);

  const scrollToLatest = () => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    followRef.current = true;
    setAwayFromBottom(false);
    setMissedCount(0);
  };

  useLayoutEffect(() => {
    const inputEl = inputRef.current;
    if (inputEl) {
      inputEl.style.height = 'auto';
      inputEl.style.height = `${Math.min(Math.max(inputEl.scrollHeight, MIN_INPUT_HEIGHT), MAX_INPUT_HEIGHT)}px`;
    }
    if (followRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setMissedCount(0);
    } else if (messages.length > messageCountRef.current) {
      setMissedCount(count => count + messages.length - messageCountRef.current);
    }
    messageCountRef.current = messages.length;
  }, [input, messages, isLoading, error, sendError]);

  useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content || typeof ResizeObserver === 'undefined') return;
    // Observing the growing content keeps the tail pinned while a response
    // streams in without stealing the position of a scrolled-up reader.
    const observer = new ResizeObserver(() => {
      if (followRef.current && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    });
    observer.observe(content);
    return () => observer.disconnect();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!input.trim() || isLoading || disabled || sendingRef.current || composingRef.current) return;
    const message = input.trim();
    sendingRef.current = true;
    setSendError(null);
    setInput('');
    scrollToLatest();
    inputRef.current?.focus({ preventScroll: true });
    try {
      await onSend(message);
    } catch (cause) {
      setInput(current => current || message);
      setSendError(cause instanceof Error ? cause.message : '发送失败，请重试');
    } finally {
      sendingRef.current = false;
    }
  };

  return (
    <section aria-label="聊天" data-keyboard-open={keyboardOpen || undefined} className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[var(--color-bg-page)] text-[var(--color-text-primary)]">
      <div className="flex shrink-0 items-center justify-end gap-2 border-b border-[var(--color-border-subtle)] px-2">
        {isLoading && <span role="status" className="pl-2 text-xs text-[var(--color-text-muted)]">正在生成</span>}
        {onRefresh && <button type="button" aria-label="刷新消息" disabled={isLoading || isRefreshing} onClick={async () => {
          try { await onRefresh(); } catch { setSendError('刷新失败，请重试'); }
        }} className="flex h-11 w-11 items-center justify-center rounded-lg disabled:opacity-40">
          <RefreshCw size={16} aria-hidden="true" className={isRefreshing ? 'animate-spin' : ''} />
        </button>}
      </div>
      <div ref={scrollRef} role="region" aria-label="消息列表" tabIndex={0}
        className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-4 [overflow-wrap:anywhere]"
        onScroll={event => {
          const el = event.currentTarget;
          // A list shorter than its own viewport always counts as the tail.
          if (el.scrollHeight <= el.clientHeight) {
            followRef.current = true;
            setAwayFromBottom(false);
            setMissedCount(0);
            return;
          }
          followRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < FOLLOW_THRESHOLD;
          setAwayFromBottom(!followRef.current);
        }}>
        <div ref={contentRef} className="flex min-h-full flex-col">
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center py-8 text-center">
              <h2 className="text-lg font-medium">{emptyStateTitle}</h2>
            </div>
          ) : <div className="space-y-5">
            {messages.map(message => <article key={message.id} className={`min-w-0 ${message.role === 'user' ? 'ml-auto max-w-[90%] rounded-xl bg-[var(--color-bg-surface-2)] px-3 py-2' : ''}`}>
              <p className="mb-1 text-xs text-[var(--color-text-muted)]">{{ user: '你', assistant: 'Climber', system: '系统', tool: message.tool_name || '工具' }[message.role]}</p>
              {message.content && <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>}
              {message.timestamp && <p className="mt-1 text-xs text-[var(--color-text-muted)]">{formatTime(message.timestamp)}</p>}
              {message.reasoning && visuals.showThinking && <details className="mt-2 text-sm"><summary className="min-h-11 cursor-pointer py-3 text-[var(--color-text-muted)]">思考过程</summary><p className="whitespace-pre-wrap">{message.reasoning}</p></details>}
              {visuals.showToolCalls && message.toolCalls?.map(tool => <details key={tool.id} className="mt-2 rounded-lg border border-[var(--color-border-subtle)] px-3 text-sm">
                <summary className="min-h-11 cursor-pointer py-3">{tool.name} · {tool.error ? '失败' : tool.status === 'running' ? '运行中' : tool.status === 'success' ? '完成' : tool.status === 'error' ? '失败' : '工具调用'}</summary>
                <pre className="max-h-48 overflow-auto pb-3 text-xs">{JSON.stringify(tool.arguments, null, 2)}</pre>
                {(tool.error || tool.result) && <pre className="max-h-64 overflow-auto whitespace-pre-wrap pb-3 text-xs">{tool.error || tool.result}</pre>}
              </details>)}
            </article>)}
          </div>}
        </div>
      </div>
      {awayFromBottom && <button type="button" onClick={scrollToLatest} className="mx-auto flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 text-sm">
        <ArrowDown size={16} aria-hidden="true" />
        回到最新
        {missedCount > 0 && <span aria-hidden="true" className="rounded-full bg-[var(--color-accent)] px-1.5 text-xs text-[var(--color-accent-text)]">{missedCount > 99 ? '99+' : missedCount}</span>}
      </button>}
      {/* The shell already reserves the navigation strip and the bottom inset, so
          the composer only keeps the horizontal safe area. */}
      <form onSubmit={handleSubmit} className="mobile-composer shrink-0 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-3"
        style={{ paddingBottom: `${COMPOSER_PADDING}px`, paddingLeft: 'max(12px, env(safe-area-inset-left, 0px))', paddingRight: 'max(12px, env(safe-area-inset-right, 0px))' }}>
        {(error || sendError) && <p role="alert" className="mb-2 max-h-20 overflow-auto text-sm text-[var(--color-error)] [overflow-wrap:anywhere]">{error || sendError}</p>}
        <ChatComposerTools
          sessionId={sessionId ?? null}
          compact
          visuals={visuals}
          setShowToolCalls={setShowToolCalls}
          setShowThinking={setShowThinking}
          className="mb-2"
        />
        <div className="flex items-end gap-2">
          <textarea ref={inputRef} value={input} onChange={event => setInput(event.target.value)}
            onCompositionStart={() => { composingRef.current = true; }}
            onCompositionEnd={event => { composingRef.current = false; compositionEndRef.current = event.timeStamp; }}
            onKeyDown={event => {
              if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing || composingRef.current || event.keyCode === 229) return;
              if (isSafariEngine() && event.timeStamp - compositionEndRef.current < COMPOSITION_GUARD_MS) {
                // Consume the one confirming keystroke; the next Enter sends.
                compositionEndRef.current = -Infinity;
                return;
              }
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }}
            aria-label="输入消息" placeholder="输入消息" rows={1}
            className="min-h-11 min-w-0 flex-1 resize-none overflow-y-auto rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-page)] px-3 py-2 text-base leading-6" style={{ maxHeight: 'min(128px, 30dvh)' }} />
          {isLoading && onStop ? <button type="button" onClick={onStop} aria-label="停止生成" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--color-bg-surface-2)]"><Square size={18} aria-hidden="true" /></button> :
            <button type="submit" disabled={!input.trim() || isLoading || disabled} aria-label="发送消息" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent)] text-[var(--color-accent-text)] disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]">
              {isLoading ? <Loader2 size={18} aria-hidden="true" className="animate-spin" /> : <Send size={18} aria-hidden="true" />}
            </button>}
        </div>
      </form>
    </section>
  );
}
