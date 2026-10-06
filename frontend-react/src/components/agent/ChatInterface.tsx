import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { Send, Square, ArrowDown, CircleAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import { MessageActions } from '../chat/MessageContent';
import { MessageBubble } from '../chat/MessageBubble';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { ChatEmptyState } from './ChatEmptyState';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { StreamingCursor } from '../chat/StreamingCursor';
import { ThinkingIndicator } from './ThinkingIndicator';
import { FloatingPermissionDialog } from './FloatingPermissionDialog';
import type { PermissionRequest } from './FloatingPermissionDialog';
import { SlashCommandMenu } from '../chat/SlashCommandMenu';
import { ChatComposerTools } from '../chat/ChatComposerTools';
import { ImageAttachmentBar } from '../multimodal/ImageAttachmentBar';
import type { ImageAttachment } from '../multimodal/attachments';
import type { ChatAttachmentPayload } from '../../useChat';
import { useChatVisuals } from '../../hooks/useChatVisuals';
import {
  FALLBACK_COMMANDS,
  cancelSessionTurn,
  completionsFor,
  executeSlashCommand,
  extractCommandHead,
  findCommand,
  resolveCommand,
  type SlashCommandInfo,
} from '../chat/slashCommands';
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
  onSend: (message: string, attachments?: string[], files?: ChatAttachmentPayload[]) => void;
  onStop?: () => void;
  isLoading?: boolean;
  /** Session id used by slash-command execution and server-side interrupts. */
  sessionId?: string | null;
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
  sessionId,
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
  const [attachments, setAttachments] = useState<ImageAttachment[]>([]);
  const [editState, setEditState] = useState<EditState>(null);
  // Transcript display preferences. One hook instance per composer: the value
  // is passed down to ChatComposerTools so both composers read the same flags.
  const { visuals, setShowToolCalls, setShowThinking } = useChatVisuals();
  // Slash-command autocomplete state. The menu is visible while the input is
  // a "/"-prefixed token that still matches at least one registered command.
  const [slashCatalog, setSlashCatalog] = useState<SlashCommandInfo[]>(FALLBACK_COMMANDS);
  const [slashActiveIndex, setSlashActiveIndex] = useState(0);
  const [slashDismissed, setSlashDismissed] = useState(false);
  /**
   * Debounced instruction understanding shown above the composer only when the
   * deterministic pass flags a missing goal or an ambiguity. Mirrors the trace
   * `task_spec`: a plain-language summary plus clarification questions.
   */
  const [clarity, setClarity] = useState<{ summary: string; questions: string[] } | null>(null);

  useEffect(() => {
    const text = input.trim();
    if (text.length < 2 || text.startsWith('/') || isLoading) {
      setClarity(null);
      return;
    }
    const timer = setTimeout(() => {
      api.understandInstruction(text)
        .then(data => {
          const progress = data?.progress;
          if (progress !== 'needs_clarification') {
            setClarity(null);
            return;
          }
          const questions = Array.isArray(data?.clarification_questions)
            ? data.clarification_questions
            : [];
          setClarity({ summary: data?.plain_language_summary ?? '', questions });
        })
        .catch(() => setClarity(null));
    }, 600);
    return () => clearTimeout(timer);
  }, [input, isLoading]);
  /**
   * One reading column for the transcript and the composer, decided by
   * {@link getReadingWidthClass}: a turn carrying parallel tool output needs
   * more room than prose, and the composer follows the widest turn in view.
   */
  const [fullWidth, toggleFullWidth] = useMaximizeChatSpace();
  const [editContent, setEditContent] = useState('');
  const [resolvedPermissionIds, setResolvedPermissionIds] = useState<Set<string>>(() => new Set());
  const [feedbacks, setFeedbacks] = useState<Record<string, 'up' | 'down'>>({});
  /** A failed feedback submission is shown to the user, not just logged (R12-H57). */
  const [feedbackError, setFeedbackError] = useState<{ messageId: string; message: string } | null>(null);
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
  // Newest completed assistant turn. Announced through the polite live region
  // below so a screen-reader user hears streaming replies arrive instead of
  // only discovering them by re-reading the transcript (R12-H12).
  const liveAnnouncement = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message?.role === 'assistant' && message.id !== activeMessageId) {
        return message.content;
      }
    }
    return '';
  }, [messages, activeMessageId]);
  const isEmpty = messages.length === 0;
  const isHistoryLoading = isEmpty && !!isLoading;
  const showEmptyState = isEmpty && !isLoading && !error;
  const conversationIsWide = messages.some(message => hasParallelToolContent(message.toolCalls?.length));
  const composerWidth = getReadingWidthClass({ fullWidth, hasParallelContent: conversationIsWide });

  // ---- Slash commands: derived autocomplete state -------------------------
  const slashHead = extractCommandHead(input);
  const slashQuery = slashHead ?? '';
  const slashCompletions = useMemo(
    () => (slashHead === null ? [] : completionsFor(slashCatalog, slashQuery, !!isLoading)),
    [slashCatalog, slashHead, slashQuery, isLoading],
  );
  const slashMenuVisible =
    slashHead !== null && !slashDismissed && slashCompletions.length > 0;
  // Exact-match check used on submit: "/help" is a command, "/etc/hosts" is not.
  const isExactCommand = useCallback(
    (value: string) => resolveCommand(slashCatalog, value) !== null,
    [slashCatalog],
  );
  const activeSlashCommand = slashHead === null ? undefined : findCommand(slashCatalog, slashHead);
  const activeSlashError =
    activeSlashCommand && slashCompletions.length === 0 && !isLoading
      ? t('slash.unknown_command', { defaultValue: '未知命令' })
      : null;

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
    await Promise.all(permissionRequests.map(request => api.resolvePermission(request.id, 'allow')));
    setResolvedPermissionIds(prev => new Set([...prev, ...permissionRequests.map(request => request.id)]));
  }, [permissionRequests]);

  const submitFeedback = useCallback(async (messageId: string, type: 'up' | 'down') => {
    if (feedbacks[messageId]) return;
    try {
      await api.submitFeedback(messageId, type);
      setFeedbacks(prev => ({ ...prev, [messageId]: type }));
      setFeedbackError(null);
    } catch {
      setFeedbackError({ messageId, message: t('chat.feedback_failed') });
    }
  }, [feedbacks, t]);

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

  const canSubmit = !!input.trim() && (!isLoading || (activeSlashCommand?.allowed_while_streaming ?? false));

  // ---- Slash command execution -------------------------------------------
  // Command turns live in component state (not useChat) so the regular send
  // path stays untouched; replies are appended after the transcript.
  const [commandTurns, setCommandTurns] = useState<Message[]>([]);
  const [commandRunning, setCommandRunning] = useState(false);
  const commandAbortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let active = true;
    // The backend catalog is authoritative; silently keep the fallback on error.
    api.listChatCommands()
      .then(commands => {
        if (active && commands?.length) setSlashCatalog(commands as SlashCommandInfo[]);
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  const appendCommandMessage = useCallback((message: Message) => {
    setCommandTurns(prev => [...prev, message]);
  }, []);

  const runSlashCommand = useCallback((raw: string) => {
    const text = raw.trim();
    appendCommandMessage({
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    });
    const assistantId = `assistant-${Date.now()}`;
    appendCommandMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      timestamp: new Date(),
    });
    setCommandRunning(true);
    const upsert = (mutate: (msg: Message) => Message) => {
      setCommandTurns(prev => prev.map(msg => (msg.id === assistantId ? mutate(msg) : msg)));
    };
    commandAbortRef.current?.();
    commandAbortRef.current = executeSlashCommand(sessionId ?? '', text, event => {
      switch (event.type) {
        case 'text':
          upsert(msg => ({ ...msg, content: msg.content + event.delta }));
          break;
        case 'error':
          upsert(msg => ({ ...msg, content: msg.content + `\n[Error: ${event.message}]` }));
           setCommandRunning(false);
           commandAbortRef.current = null;
          break;
        case 'done':
           setCommandRunning(false);
           commandAbortRef.current = null;
          break;
        default:
          break;
      }
    });
  }, [appendCommandMessage, sessionId]);

  const stopCommand = useCallback(() => {
    commandAbortRef.current?.();
    commandAbortRef.current = null;
    setCommandRunning(false);
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    followOutput.current = true;
    const text = input.trim();
    // An exact command invocation goes to the slash endpoint; everything else
    // (including unknown "/..." text like "/etc/hosts") goes to the agent.
    if (isExactCommand(text)) {
      if (commandRunning) return;
      runSlashCommand(text);
    } else {
      const ready = attachments.filter(a => a.status === 'ready' && a.url);
      const images = ready.filter(a => (a.kind ?? 'image') === 'image').map(a => a.url);
      const files = ready.map((a): ChatAttachmentPayload => ({ kind: a.kind ?? 'image', data: a.url, name: a.name, mime_type: a.mimeType ?? 'image/png', size: a.size }));
      if (files.length) {
        onSend(text, images, files);
      } else {
        onSend(text);
      }
      setAttachments([]);
    }
    setInput('');
    setSlashDismissed(false);
    setSlashActiveIndex(0);
    setClarity(null);
    if (inputRef.current) inputRef.current.style.height = 'auto';
  }, [canSubmit, input, isExactCommand, onSend, runSlashCommand, commandRunning, attachments]);

  const acceptSlashCompletion = useCallback((command: SlashCommandInfo) => {
    const needsArg = command.args.some(arg => arg.required);
    const suffix = needsArg ? ' ' : '';
    setInput(`/${command.name}${suffix}`);
    setSlashDismissed(!needsArg);
    setSlashActiveIndex(0);
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // A candidate Enter that belongs to an IME candidate window has to reach the
    // input: it neither submits nor gets swallowed.
    if (composing.current || e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229) return;
    // The confirming key of a composition arrives as "Process" on some engines.
    if (e.nativeEvent.key === 'Process') return;
    if (slashMenuVisible) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSlashActiveIndex(i => (i + 1) % slashCompletions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSlashActiveIndex(i => (i - 1 + slashCompletions.length) % slashCompletions.length);
        return;
      }
      // Enter on the menu completes the command; it never sends mid-menu.
      const highlighted = slashCompletions[slashActiveIndex] ?? slashCompletions[0];
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (highlighted) acceptSlashCompletion(highlighted);
        return;
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        if (highlighted) acceptSlashCompletion(highlighted);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setSlashDismissed(true);
        return;
      }
    }
    if (e.key !== 'Enter' || e.shiftKey) return;
    e.preventDefault();
    handleSubmit(e);
  }, [handleSubmit, slashMenuVisible, slashCompletions, slashActiveIndex, acceptSlashCompletion]);

  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    // The ceiling is the same one COMPOSER_MAX_HEIGHT expresses in rem, so the
    // box the user can scroll stops where the scripted growth stops.
    el.style.height = Math.min(el.scrollHeight, COMPOSER_MAX_HEIGHT_PX) + 'px';
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    setSlashDismissed(false);
    setSlashActiveIndex(0);
    autoGrow(e);
  }, [autoGrow]);

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
        {msg.reasoning && visuals.showThinking && (
          <ThinkingDetails isComplete={!isActive} defaultOpen={!msg.content}>
            {msg.reasoning}
          </ThinkingDetails>
        )}
        {msg.toolCalls?.length && visuals.showToolCalls ? (
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

  const renderMessage = (msg: Message, previous?: Message) => {
    const rowWidth = getReadingWidthClass({
      fullWidth,
      hasParallelContent: hasParallelToolContent(msg.toolCalls?.length),
    });
    // 连续同角色消息合并视觉：行距收紧，读成一组。
    const merged = previous?.role === msg.role;
    const rhythm = merged ? 'pb-2' : 'pb-5';
    if (editState?.messageId === msg.id) {
      const alignEnd = msg.role === 'user';
      return (
        <div className={cn('flex w-full min-w-0', alignEnd ? 'justify-end' : 'justify-start', rowWidth, rhythm)}>
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
      <MessageBubble
        className={cn(rowWidth, rhythm)}
        message={msg}
        showAvatar={!merged}
        merged={merged}
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
            <div data-transcript className="flex flex-col">
              {messages.map((msg, idx) => (
                <React.Fragment key={msg.id}>{renderMessage(msg, idx > 0 ? messages[idx - 1] : undefined)}</React.Fragment>
              ))}
              {feedbackError && (
                <div
                  role="alert"
                  className="mt-2 flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-3 py-2 text-xs text-[var(--color-error)]"
                >
                  <CircleAlert size={12} aria-hidden="true" className="shrink-0" />
                  <span className="min-w-0 flex-1 break-words">{feedbackError.message}</span>
                </div>
              )}
            </div>
          )}
          {/* Slash-command turns render after the transcript: their replies are
              command receipts (help text, model switches), not model turns. */}
          {commandTurns.length > 0 && (
            <div data-slash-transcript className="flex flex-col">
              {commandTurns.map((msg, idx) => (
                <React.Fragment key={msg.id}>
                  {renderMessage({ ...msg, role: msg.role }, idx > 0 ? commandTurns[idx - 1] : undefined)}
                </React.Fragment>
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
          {/* Session-level composer controls: model, thinking level, transcript
              display switches. One row above the input, inside the same
              reading column as the composer. */}
          <ChatComposerTools
            sessionId={sessionId ?? null}
            disabled={!!isLoading}
            visuals={visuals}
            setShowToolCalls={setShowToolCalls}
            setShowThinking={setShowThinking}
            className="mb-1.5"
          />
          <ImageAttachmentBar
            attachments={attachments}
            onChange={setAttachments}
            disabled={!!isLoading}
            className="mb-1.5"
          />
          {clarity && clarity.questions.length > 0 && (
            <div
              role="status"
              className="mb-1.5 flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-warning)]/40 bg-[var(--color-warning-subtle)] px-3 py-2 text-sm"
            >
              <CircleAlert size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                {clarity.summary && (
                  <p className="text-xs text-[var(--color-text-secondary)]">{clarity.summary}</p>
                )}
                <p className="mt-0.5 text-xs font-medium text-[var(--color-text-primary)]">
                  {t('chat.clarify_hint')}
                </p>
                <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-[var(--color-text-secondary)]">
                  {clarity.questions.map((question, i) => (
                    <li key={i}>{question}</li>
                  ))}
                </ul>
              </div>
              <Button size="xs" variant="ghost" onClick={() => setClarity(null)} className="shrink-0">
                {t('common.dismiss', { defaultValue: '忽略' })}
              </Button>
            </div>
          )}
          <div
            className="relative rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] transition-colors duration-150 focus-within:border-[var(--color-border-accent)] motion-reduce:transition-none"
          >
            <SlashCommandMenu
              items={slashCompletions}
              activeIndex={Math.min(slashActiveIndex, Math.max(slashCompletions.length - 1, 0))}
              onSelect={acceptSlashCompletion}
              onHover={setSlashActiveIndex}
              visible={slashMenuVisible}
            />
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => { composing.current = true; }}
              onCompositionEnd={() => { composing.current = false; }}
              placeholder={resolvedPlaceholder}
              aria-label={resolvedPlaceholder}
              aria-autocomplete="list"
              aria-expanded={slashMenuVisible}
              aria-controls="slash-command-menu"
              className={cn('block min-h-[var(--space-6)] w-full resize-none bg-transparent px-3 py-2.5 text-[length:var(--text-sm)] leading-6 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none', COMPOSER_MAX_HEIGHT)}
              rows={1}
            />
            <div className="flex items-center justify-between gap-3 px-2 pb-2">
              <p className="min-w-0 truncate text-xs text-[var(--color-text-muted)]">
                {slashMenuVisible
                  ? t('slash.hint', { defaultValue: '↑↓ 选择 · Tab 补全 · Esc 关闭' })
                  : activeSlashError
                    ? activeSlashError
                    : isLoading
                      ? t('common.loading')
                      : `Enter ${t('chat.send')} · Shift + Enter`}
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
                    onClick={() => {
                      // Local abort plus a server-side interrupt request: the
                      // engine unwinds at its next cooperative stop checkpoint.
                      if (sessionId) cancelSessionTurn(sessionId);
                      onStop?.();
                      stopCommand();
                    }}
                    disabled={!onStop && !commandRunning}
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

      {/* Streaming replies arrive asynchronously; announce completed turns to
          assistive tech instead of requiring a manual re-read (R12-H12). */}
      <div aria-live="polite" className="sr-only" data-live-announcement>{liveAnnouncement}</div>
    </div>
  );
};

export default ChatInterface;
