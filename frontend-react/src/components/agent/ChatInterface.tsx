import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Send, Square, ArrowDown, CircleAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import { MessageActions, MessageContent } from '../chat/MessageContent';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { ChatEmptyState } from './ChatEmptyState';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { StreamingCursor } from '../chat/StreamingCursor';
import { ThinkingIndicator } from './ThinkingIndicator';
import { FloatingPermissionDialog } from './FloatingPermissionDialog';
import type { PermissionRequest } from './FloatingPermissionDialog';
import { useI18n } from '../../i18n';
import { getReadingWidthClass, hasParallelToolContent, useMaximizeChatSpace } from './readingWidth';
import { ToolCallVisualization, type ToolCall as VisualToolCall } from './ToolCallVisualization';

/** Same gutter on both sides of the column. */
const GUTTER = 'px-4 md:px-6';

/**
 * The one line a textarea is allowed to grow to, as a spacing-scale multiple:
 * `calc(var(--space-16) * 3.125)` is 12.5rem, which is the same 200px ceiling
 * `autoGrow` enforces in pixels. Both numbers come from the token scale now, and
 * the comment on {@link autoGrow} keeps them together.
 */
const COMPOSER_MAX_HEIGHT = 'max-h-[calc(var(--space-16)*3.125)]';
const COMPOSER_MAX_HEIGHT_PX = 200;

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
  requiresApproval?: boolean;
  action?: PermissionRequest['action'];
  description?: string;
  details?: string;
  severity?: PermissionRequest['severity'];
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  reasoning?: string;
  timestamp?: Date;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSend: (message: string) => void;
  onStop?: () => void;
  isLoading?: boolean;
  /** A failure the caller actually observed. Renders an error row, nothing else. */
  error?: string;
  /** Only rendered alongside `error`; without a handler there is no retry button. */
  onRetry?: () => void;
  className?: string;
  placeholder?: string;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  suggestions?: string[];
  permissionRequests?: PermissionRequest[];
}

type EditState = { mode: 'view' | 'edit'; messageId: string } | null;

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSend,
  onStop,
  isLoading,
  error,
  onRetry,
  className,
  placeholder,
  emptyStateTitle,
  emptyStateDescription,
  suggestions,
  permissionRequests: providedPermissionRequests,
}) => {
  const { t } = useI18n();
  const resolvedPlaceholder = placeholder ?? t('chat.input_placeholder');
  const resolvedEmptyStateTitle = emptyStateTitle ?? t('chat.empty_state_title', { defaultValue: '开始对话' });
  const resolvedSuggestions = suggestions ?? [
    t('chat.suggestion_1'),
    t('chat.suggestion_2'),
    t('chat.suggestion_3'),
  ];
  const [input, setInput] = useState('');
  const [editState, setEditState] = useState<EditState>(null);
  /**
   * One reading column for the transcript and the composer, decided by
   * {@link getReadingWidthClass}: a turn carrying parallel tool output needs
   * more room than prose, and the composer follows the widest turn in view.
   */
  const [fullWidth, toggleFullWidth] = useMaximizeChatSpace();
  const [editContent, setEditContent] = useState('');
  const [resolvedPermissionIds, setResolvedPermissionIds] = useState<Set<string>>(() => new Set());
  const [feedbacks, setFeedbacks] = useState<Record<string, 'up' | 'down'>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const editInputRef = useRef<HTMLTextAreaElement>(null);
  /**
   * Safari reports `isComposing` inconsistently, so the flag is also tracked
   * from the composition events and cross-checked against keyCode 229.
   */
  const composing = useRef(false);
  const followOutput = useRef(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const lastMessage = messages.at(-1);
  const activeMessageId = isLoading && lastMessage?.role === 'assistant' ? lastMessage.id : undefined;
  const isEmpty = messages.length === 0;
  const isHistoryLoading = isEmpty && !!isLoading;
  const showEmptyState = isEmpty && !isLoading && !error;
  const conversationIsWide = messages.some(message => hasParallelToolContent(message.toolCalls?.length));
  const composerWidth = getReadingWidthClass({ fullWidth, hasParallelContent: conversationIsWide });

  const permissionRequests = (providedPermissionRequests ?? messages.flatMap(message =>
    (message.toolCalls ?? []).flatMap(toolCall => {
      if (!toolCall.requiresApproval) return [];
      return [{
        id: toolCall.id,
        action: toolCall.action ?? 'mcp_tool',
        description: toolCall.description ?? `${toolCall.name} requires approval`,
        details: toolCall.details,
        severity: toolCall.severity ?? 'medium',
        timestamp: Date.now(),
      } satisfies PermissionRequest];
    }),
  )).filter(request => !resolvedPermissionIds.has(request.id));

  const handleApprovePermission = useCallback(async (id: string) => {
    await api.resolvePermission(id, 'allow');
    setResolvedPermissionIds(prev => new Set(prev).add(id));
  }, []);

  const handleDenyPermission = useCallback(async (id: string) => {
    await api.resolvePermission(id, 'deny');
    setResolvedPermissionIds(prev => new Set(prev).add(id));
  }, []);

  const handleApproveAllPermissions = useCallback(async () => {
    await Promise.all(permissionRequests.map(request => api.resolvePermission(request.id, 'allow' as Parameters<typeof api.resolvePermission>[1])));
    setResolvedPermissionIds(prev => new Set([...prev, ...permissionRequests.map(request => request.id)]));
  }, [permissionRequests]);

  const submitFeedback = useCallback(async (messageId: string, type: 'up' | 'down') => {
    if (feedbacks[messageId]) return;
    try {
      await api.submitFeedback(messageId, type);
      setFeedbacks(prev => ({ ...prev, [messageId]: type }));
    } catch (e) {
      console.error('feedback failed', e);
    }
  }, [feedbacks]);

  useEffect(() => {
    if (scrollRef.current && followOutput.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (editState?.mode !== 'edit') return;
    editInputRef.current?.focus();
  }, [editState]);

  const startEditing = useCallback((messageId: string, content: string) => {
    setEditContent(content);
    setEditState({ mode: 'edit', messageId });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditState(null);
    setEditContent('');
  }, []);

  const saveEdit = useCallback(() => {
    if (!isLoading && editContent.trim() && editState?.mode === 'edit') {
      followOutput.current = true;
      onSend(editContent.trim());
      setEditState(null);
      setEditContent('');
    }
  }, [editState, editContent, onSend, isLoading]);

  const canSubmit = !!input.trim() && !isLoading;

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (canSubmit) {
      followOutput.current = true;
      onSend(input.trim());
      setInput('');
      if (inputRef.current) inputRef.current.style.height = 'auto';
    }
  }, [canSubmit, input, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // A candidate Enter that belongs to an IME candidate window has to reach the
    // input: it neither submits nor gets swallowed.
    if (composing.current || e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229) return;
    // The confirming key of a composition arrives as "Process" on some engines.
    if (e.nativeEvent.key === 'Process') return;
    if (e.key !== 'Enter' || e.shiftKey) return;
    e.preventDefault();
    handleSubmit(e);
  }, [handleSubmit]);

  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    // The ceiling is the same one COMPOSER_MAX_HEIGHT expresses in rem, so the
    // box the user can scroll stops where the scripted growth stops.
    el.style.height = Math.min(el.scrollHeight, COMPOSER_MAX_HEIGHT_PX) + 'px';
  }, []);

  const fillFromSuggestion = useCallback((suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  }, []);

  const renderEditControls = (alignEnd: boolean) => (
    <div className={cn('flex items-center gap-2', alignEnd && 'justify-end')}>
      <Button size="sm" onClick={saveEdit} disabled={isLoading || !editContent.trim()}>
        {t('common.save')}
      </Button>
      <Button size="sm" variant="ghost" onClick={cancelEdit}>
        {t('common.cancel')}
      </Button>
    </div>
  );

  const renderMessageBody = (msg: Message) => {
    const isUser = msg.role === 'user';
    const isActive = msg.id === activeMessageId;
    const isAwaitingFirstToken = isActive && !msg.content && !msg.reasoning && !msg.toolCalls?.length;
    return (
      <>
        {isAwaitingFirstToken && <ThinkingIndicator compact />}
        {msg.reasoning && (
          <ThinkingDetails isComplete={!isActive} defaultOpen={!msg.content}>
            {msg.reasoning}
          </ThinkingDetails>
        )}
        {msg.toolCalls?.length ? (
          <div className={cn(isUser ? 'my-1' : 'mb-2', 'w-full')}>
            <ToolCallVisualization
              calls={msg.toolCalls.map(toolCall => ({
                ...toolCall,
                status: isActive && toolCall.status === 'running' ? 'running' : toolCall.status,
              })) as VisualToolCall[]}
              defaultExpanded={isActive}
              hideRunningStatus={!isActive}
            />
          </div>
        ) : null}
        {msg.content && (
          <div className="min-w-0">
            {isUser ? <p className="whitespace-pre-wrap">{msg.content}</p> : <MarkdownRenderer content={msg.content} />}
            {isActive && (
              <span data-streaming-cursor>
                <StreamingCursor />
              </span>
            )}
          </div>
        )}
      </>
    );
  };

  const renderMessage = (msg: Message) => {
    const rowWidth = getReadingWidthClass({
      fullWidth,
      hasParallelContent: hasParallelToolContent(msg.toolCalls?.length),
    });
    if (editState?.messageId === msg.id) {
      const alignEnd = msg.role === 'user';
      return (
        <div className={cn('flex w-full min-w-0', alignEnd ? 'justify-end' : 'justify-start', rowWidth)}>
          {/* Editing takes the whole column: the composer this replaces is
              full width, and a fit-to-content box would clip what is typed. */}
          <div className="flex w-full min-w-0 flex-col gap-2">
            <div
              className={cn(
                'rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-3 py-2 transition-colors duration-150 focus-within:border-[var(--color-border-accent)]',
                alignEnd && 'rounded-br-[var(--radius-sm)]',
              )}
            >
              <textarea
                ref={editInputRef}
                value={editContent}
                 aria-label={t('chat.edit_message', { defaultValue: '编辑消息' })}
                onChange={e => { setEditContent(e.target.value); autoGrow(e); }}
                onKeyDown={handleKeyDown}
                onCompositionStart={() => { composing.current = true; }}
                onCompositionEnd={() => { composing.current = false; }}
                className="block min-h-[var(--space-6)] w-full resize-none bg-transparent text-[length:var(--text-sm)] leading-relaxed text-[var(--color-text-primary)] focus:outline-none"
                rows={3}
                autoFocus
              />
            </div>
            {renderEditControls(alignEnd)}
          </div>
        </div>
      );
    }

    return (
      <MessageContent
        className={rowWidth}
        role={msg.role}
        content={msg.content}
        timestamp={msg.timestamp}
        body={renderMessageBody(msg)}
        actions={
          msg.role === 'assistant' && msg.content ? (
            <MessageActions
              onCopy={() => navigator.clipboard.writeText(msg.content)}
              onFeedback={type => submitFeedback(msg.id, type)}
              onEdit={() => startEditing(msg.id, msg.content)}
            />
          ) : null
        }
      />
    );
  };

  return (
    <div className={cn('relative flex h-full min-h-0 min-w-0 flex-col', className)}>
      <div
        ref={scrollRef}
        onScroll={() => {
          const el = scrollRef.current;
          if (!el) return;
          followOutput.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
          setShowScrollButton(!followOutput.current);
        }}
        className={cn('min-h-0 flex-1 overflow-y-auto overscroll-contain py-4', GUTTER)}
      >
        <div className="flex flex-col gap-5">
          {isHistoryLoading && (
            <div role="status" aria-label={t('common.loading')} className="flex flex-col gap-4">
              <div className="h-4 w-2/3 rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] motion-safe:animate-pulse" />
              <div className="h-4 w-1/2 rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] motion-safe:animate-pulse" />
            </div>
          )}
          {showEmptyState && (
            <ChatEmptyState
              title={resolvedEmptyStateTitle}
              description={emptyStateDescription}
              className="min-h-full"
              actions={
                <div className="flex w-full flex-col items-start gap-0.5">
                  {resolvedSuggestions.map((suggestion, idx) => (
                    <button
                      type="button"
                      key={idx}
                      onClick={() => fillFromSuggestion(suggestion)}
                      className="flex w-full items-baseline gap-2 rounded-[var(--radius-md)] px-2 py-2 text-start text-sm text-[var(--color-text-secondary)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]"
                    >
                      <span aria-hidden="true" className="font-mono text-xs text-[var(--color-text-muted)]">&gt;</span>
                      <span className="min-w-0 flex-1 truncate">{suggestion}</span>
                    </button>
                  ))}
                </div>
              }
            />
          )}
          {!isEmpty && (
            <div data-transcript className="flex flex-col gap-5">
              {messages.map(msg => (
                <React.Fragment key={msg.id}>{renderMessage(msg)}</React.Fragment>
              ))}
            </div>
          )}
          {/* The failure is the newest event, so it follows the turns it ended. */}
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-3 py-2 text-sm text-[var(--color-error)]"
            >
              <CircleAlert size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
              <span className="min-w-0 flex-1 break-words">
                <span className="font-medium">{t('common.error')}</span>
                <span className="ms-1 text-[var(--color-text-secondary)]">{error}</span>
              </span>
              {onRetry && (
                <Button size="xs" variant="ghost" onClick={onRetry} className="shrink-0">
                  {t('common.retry')}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
      {showScrollButton && (
        <Button
          variant="secondary"
          size="icon-sm"
          aria-label="滚动到底部"
          onClick={() => {
            if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
            followOutput.current = true;
            setShowScrollButton(false);
          }}
          className="mx-auto my-2 shrink-0"
        >
          <ArrowDown size={14} aria-hidden="true" />
        </Button>
      )}
      <form
        onSubmit={handleSubmit}
        aria-busy={!!isLoading}
        className={cn('border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] py-3', GUTTER)}
      >
        <div className={composerWidth}>
          <div
            className="rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] transition-colors duration-150 focus-within:border-[var(--color-border-accent)] motion-reduce:transition-none"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => { setInput(e.target.value); autoGrow(e); }}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => { composing.current = true; }}
              onCompositionEnd={() => { composing.current = false; }}
              placeholder={resolvedPlaceholder}
              aria-label={resolvedPlaceholder}
              className={cn('block min-h-[var(--space-6)] w-full resize-none bg-transparent px-3 py-2.5 text-[length:var(--text-sm)] leading-6 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none', COMPOSER_MAX_HEIGHT)}
              rows={1}
            />
            <div className="flex items-center justify-between gap-3 px-2 pb-2">
              <p className="min-w-0 truncate text-xs text-[var(--color-text-muted)]">
                {isLoading ? t('common.loading') : `Enter ${t('chat.send')} · Shift + Enter`}
              </p>
              {/* One slot, one control: stopping and sending are the same button
                  in two states, so a run in flight can never be answered by a
                  second, competing action. */}
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  aria-pressed={fullWidth}
                  onClick={toggleFullWidth}
                  className="rounded-[var(--radius-sm)] px-[var(--space-1-5)] py-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
                >
                   {t('chat.wide_column', { defaultValue: '宽列' })}
                </button>
                {isLoading ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="icon"
                     aria-label={t('chat.stop_generation', { defaultValue: '停止生成' })}
                    onClick={onStop}
                    disabled={!onStop}
                    className="shrink-0"
                  >
                    <Square size={14} aria-hidden="true" />
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    size="icon"
                    aria-label={t('chat.send')}
                    disabled={!canSubmit}
                    className="shrink-0"
                  >
                    <Send size={14} aria-hidden="true" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </form>

      <FloatingPermissionDialog
        requests={permissionRequests}
        onApprove={handleApprovePermission}
        onDeny={handleDenyPermission}
        onApproveAll={handleApproveAllPermissions}
      />
    </div>
  );
};

export default ChatInterface;
