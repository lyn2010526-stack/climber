import { useState, useRef, useLayoutEffect, useEffect } from 'react';
import { ArrowDown, Loader2, RefreshCw, Send, Square } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { Message } from '../../useChat';
import { ChatComposerTools } from '../chat/ChatComposerTools';
import { ImageAttachmentBar } from '../multimodal/ImageAttachmentBar';
import type { ImageAttachment } from '../multimodal/attachments';
import { useChatVisuals } from '../../hooks/useChatVisuals';
import { MobileMessageBubble } from './MobileMessageBubble';

interface MobileChatInterfaceProps {
  messages: Message[];
  onSend: (message: string, attachments?: string[]) => Promise<void>;
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
  disabled, error, sessionId, emptyStateTitle,
}: MobileChatInterfaceProps) {
  const { t } = useI18n();
  const emptyTitle = emptyStateTitle ?? t('mobile_chat.new_conversation', { defaultValue: '新对话' });
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<ImageAttachment[]>([]);
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
    const images = attachments.filter(a => a.status === 'ready' && a.url).map(a => a.url);
    sendingRef.current = true;
    setSendError(null);
    setInput('');
    setAttachments([]);
    scrollToLatest();
    inputRef.current?.focus({ preventScroll: true });
    try {
      if (images.length) {
        await onSend(message, images);
      } else {
        await onSend(message);
      }
    } catch (cause) {
      setInput(current => current || message);
      setSendError(cause instanceof Error ? cause.message : t('mobile_chat.send_failed'));
    } finally {
      sendingRef.current = false;
    }
  };

  // The latest assistant turn is the one carrying the stream; earlier turns
  // render settled, so the thinking pulse and cursor do not light up history.
  const lastAssistantId = [...messages].reverse().find(message => message.role === 'assistant')?.id;

  return (
    <section aria-label={t('chat.aria_label')} data-keyboard-open={keyboardOpen || undefined} className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[var(--color-bg-page)] text-[var(--color-text-primary)]">
      <div className="flex shrink-0 items-center justify-end gap-2 border-b border-[var(--color-border-subtle)] px-2">
        {isLoading && <span role="status" className="flex min-h-[44px] items-center gap-1.5 pl-2 text-xs text-[var(--color-text-muted)]">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-[var(--color-accent-foreground)] motion-safe:animate-pulse" />
          {t('mobile_chat.generating')}
        </span>}
        {onRefresh && <button type="button" aria-label={t('mobile_chat.refresh_messages')} disabled={isLoading || isRefreshing} onClick={async () => {
          try { await onRefresh(); } catch { setSendError(t('mobile_chat.refresh_failed')); }
        }} className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-secondary)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] disabled:opacity-40 motion-reduce:transition-none">
          <RefreshCw size={16} aria-hidden="true" className={isRefreshing ? 'animate-spin' : ''} />
        </button>}
      </div>
      <div ref={scrollRef} role="region" aria-label={t('mobile_chat.message_list_aria')} tabIndex={0}
        className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 [overflow-wrap:anywhere]"
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
              <h2 className="text-lg font-medium">{emptyTitle}</h2>
            </div>
          ) : <div className="space-y-4">
            {messages.map((message, index) => (
              <MobileMessageBubble
                key={message.id}
                message={message}
                isStreaming={Boolean(isLoading) && message.id === lastAssistantId && index === messages.length - 1}
                showThinking={visuals.showThinking}
                showToolCalls={visuals.showToolCalls}
              />
            ))}
          </div>}
        </div>
      </div>
      {awayFromBottom && <button type="button" onClick={scrollToLatest} className="mx-auto flex min-h-[44px] shrink-0 items-center gap-2 rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3.5 text-sm shadow-[var(--shadow-md)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] motion-reduce:transition-none">
        <ArrowDown size={16} aria-hidden="true" />
        {t('mobile_chat.back_to_latest')}
        {missedCount > 0 && <span aria-hidden="true" className="rounded-full bg-[var(--color-accent)] px-1.5 text-xs text-[var(--color-accent-text)]">{missedCount > 99 ? '99+' : missedCount}</span>}
      </button>}
      {/* The shell already reserves the navigation strip and the bottom inset, so
          the composer only keeps the horizontal safe area. The iOS-style glass
          reads through a translucent surface; `--color-glass-bg` is opaque per
          theme, so it is washed to 88% and the blur carries the depth. */}
      <form onSubmit={handleSubmit} className="mobile-composer shrink-0 border-t border-[var(--color-border-subtle)] p-3"
        style={{
          paddingBottom: `${COMPOSER_PADDING}px`,
          paddingLeft: 'max(12px, env(safe-area-inset-left, 0px))',
          paddingRight: 'max(12px, env(safe-area-inset-right, 0px))',
          backgroundColor: 'color-mix(in srgb, var(--color-glass-bg) 88%, transparent)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        }}>
        {(error || sendError) && <p role="alert" className="mb-2 max-h-20 overflow-auto text-sm text-[var(--color-error)] [overflow-wrap:anywhere]">{error || sendError}</p>}
        <ChatComposerTools
          sessionId={sessionId ?? null}
          compact
          visuals={visuals}
          setShowToolCalls={setShowToolCalls}
          setShowThinking={setShowThinking}
          className="mb-2"
        />
        <ImageAttachmentBar
          attachments={attachments}
          onChange={setAttachments}
          disabled={!!isLoading}
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
            aria-label={t('mobile_chat.input_placeholder')} placeholder={t('mobile_chat.input_placeholder')} rows={1}
            className="min-h-11 min-w-0 flex-1 resize-none overflow-y-auto rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-bg-page)] px-4 py-2.5 text-base leading-6 transition-colors duration-150 focus-visible:outline-none focus-visible:border-[var(--color-border-accent)] motion-reduce:transition-none" style={{ maxHeight: 'min(128px, 30dvh)' }} />
          {isLoading && onStop ? <button type="button" onClick={onStop} aria-label={t('mobile_chat.stop')} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)] transition-colors duration-150 active:bg-[var(--color-bg-surface-4)] motion-reduce:transition-none"><Square size={18} aria-hidden="true" /></button> :
            <button type="submit" disabled={!input.trim() || isLoading || disabled} aria-label={t('mobile_chat.send')} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)] text-[var(--color-accent-text)] transition-colors duration-150 active:bg-[var(--color-accent-active)] disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)] motion-reduce:transition-none">
              {isLoading ? <Loader2 size={18} aria-hidden="true" className="animate-spin" /> : <Send size={18} aria-hidden="true" />}
            </button>}
        </div>
      </form>
    </section>
  );
}
