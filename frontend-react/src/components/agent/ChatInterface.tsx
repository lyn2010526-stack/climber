import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Drawer } from 'vaul';
import { ArrowDown, ArrowUpRight, Bot, Edit3, Check, X, Maximize2, Sparkles, TerminalSquare } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import type { ApprovalRequest } from '../../api';
import { MessageContent, MessageActions, ToolCallCard } from '../chat/MessageContent';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { ThinkingIndicator } from './ThinkingIndicator';
import { FloatingPermissionDialog } from './FloatingPermissionDialog';
import type { PermissionRequest } from './FloatingPermissionDialog';
import { ChatComposer } from './ChatComposer';
import type { ChatMessage } from '../../types/message';

  const StreamingCursor = () => (
    <span className="inline-block w-[2px] h-4 ml-0.5 rounded-full animate-pulse bg-[var(--color-accent)]" />
  );

interface ChatInterfaceProps {
  sessionId?: string | null;
  messages: ChatMessage[];
  onSend: (message: string, model?: { provider?: string; modelId?: string }) => void;
  onStop?: () => void;
  isLoading?: boolean;
  className?: string;
  placeholder?: string;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  suggestions?: string[];
}

type EditState = { mode: 'view'; messageId: string } | { mode: 'edit'; messageId: string } | { mode: 'modal'; messageId: string } | null;

function toPermissionRequest(request: ApprovalRequest): PermissionRequest {
  const actions: Record<string, PermissionRequest['action']> = {
    read_file: 'file_read',
    write_file: 'file_write',
    edit_file: 'file_write',
    delete_file: 'file_delete',
    run_command: 'command',
    execute_code: 'command',
    network_request: 'network',
  };
  const action = actions[request.tool_name] ?? 'mcp_tool';
  const severity: PermissionRequest['severity'] = action === 'file_delete'
    ? 'high'
    : action === 'file_read'
      ? 'low'
      : 'medium';

  return {
    id: request.id,
    action,
    description: `工具 ${request.tool_name} 请求执行`,
    details: JSON.stringify(request.arguments, null, 2),
    severity,
    timestamp: Date.parse(request.created_at),
  };
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  messages,
  onSend,
  onStop,
  isLoading,
  className,
  placeholder = '输入消息...（Enter 发送）',
  emptyStateTitle = '开始新的对话',
  emptyStateDescription = '输入任何问题或任务，Climber 将为你自主执行。',
  suggestions = ['帮我分析代码', '写一个 Python 脚本', '解释这个错误'],
}) => {
  const [editState, setEditState] = useState<EditState>(null);
  const [editContent, setEditContent] = useState('');
  const [permissionRequests, setPermissionRequests] = useState<PermissionRequest[]>([]);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const permissionVersionRef = useRef(0);

  useEffect(() => {
    const version = ++permissionVersionRef.current;
    if (!sessionId) {
      setPermissionRequests([]);
      return;
    }
    let active = true;
    let timeoutId: number | undefined;
    let controller: AbortController | undefined;

    const poll = async () => {
      controller = new AbortController();
      const requestVersion = permissionVersionRef.current;
      try {
        const response = await api.listPendingApprovals(sessionId, controller.signal);
        if (active && requestVersion === permissionVersionRef.current) {
          setPermissionRequests(response.requests.map(toPermissionRequest));
        }
      } catch { /* retain the last successful approval state */ }
      if (active) timeoutId = window.setTimeout(poll, 1500);
    };

    void poll();
    return () => {
      active = false;
      permissionVersionRef.current = Math.max(permissionVersionRef.current, version + 1);
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      controller?.abort();
    };
  }, [sessionId]);

  const handleApprovePermission = useCallback(async (id: string) => {
    permissionVersionRef.current += 1;
    try {
      await api.resolvePermission(id, 'allow');
      permissionVersionRef.current += 1;
      setPermissionRequests(prev => prev.filter(r => r.id !== id));
    } catch { /* keep the request visible for retry */ }
  }, []);

  const handleDenyPermission = useCallback(async (id: string) => {
    permissionVersionRef.current += 1;
    try {
      await api.resolvePermission(id, 'deny');
      permissionVersionRef.current += 1;
      setPermissionRequests(prev => prev.filter(r => r.id !== id));
    } catch { /* keep the request visible for retry */ }
  }, []);

  const handleApproveAllPermissions = useCallback(async () => {
    permissionVersionRef.current += 1;
    const ids = permissionRequests.map(r => r.id);
    const results = await Promise.allSettled(ids.map(id => api.resolvePermission(id, 'allow')));
    permissionVersionRef.current += 1;
    const resolvedIds = new Set(ids.filter((_, index) => results[index]?.status === 'fulfilled'));
    setPermissionRequests(prev => prev.filter(request => !resolvedIds.has(request.id)));
  }, [permissionRequests]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const element = scrollRef.current;
    if (!element) return;
    if (typeof element.scrollTo === 'function') {
      element.scrollTo({ top: element.scrollHeight, behavior });
      return;
    }
    element.scrollTop = element.scrollHeight;
  }, []);

  useEffect(() => {
    if (isNearBottom) scrollToBottom(messages.length < 2 ? 'auto' : 'smooth');
  }, [messages, isLoading, isNearBottom, scrollToBottom]);

  const startEditing = useCallback((messageId: string, content: string) => {
    setEditContent(content);
    setEditState({ mode: 'edit', messageId });
  }, []);

  const openModal = useCallback(() => {
    setEditState(prev => prev ? { ...prev, mode: 'modal' } : null);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditState(null);
    setEditContent('');
  }, []);

  const saveEdit = useCallback(() => {
    if (editState?.mode === 'edit' || editState?.mode === 'modal') {
      onSend(editContent);
      setEditState(null);
      setEditContent('');
    }
  }, [editState, editContent, onSend]);

  const renderMessageContent = (msg: ChatMessage, index: number) => {
    const isEditing = editState?.messageId === msg.id;
    const isLatestMessage = index === messages.length - 1;
    const isMessageStreaming = Boolean(isLoading && isLatestMessage && msg.role === 'assistant');

    if (isEditing && (editState.mode === 'edit' || editState.mode === 'modal')) {
      return (
        <div className={cn('flex gap-3 max-w-[85%]', msg.role === 'user' ? 'flex-row-reverse ml-auto' : '')}>
          <div className="flex items-center justify-center rounded-xl w-9 h-9 shrink-0 bg-[linear-gradient(135deg,var(--color-accent),#8b5cf6)] text-white">
            <Edit3 size={16} />
          </div>
          <div className={cn('flex flex-col gap-2 min-w-0 flex-1')}>
            <div className="px-4 py-3 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-default)]">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full bg-transparent text-sm resize-none focus:outline-none text-[var(--color-text-primary)]"
                rows={3}
                autoFocus
              />
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={saveEdit} className="rounded-lg">
                <Check size={12} /> 保存
              </Button>
              <Button size="sm" variant="ghost" onClick={cancelEdit} className="rounded-lg">
                <X size={12} /> 取消
              </Button>
              <Button size="sm" variant="ghost" onClick={openModal} className="rounded-lg">
                <Maximize2 size={12} />
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <motion.div
        key={msg.id}
        layout
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, transition: { duration: 0.12 } }}
        transition={{ duration: 0.22 }}
        className="w-full"
      >
        {msg.reasoning && (
          <div className="mb-2 ml-11">
            <ThinkingDetails defaultOpen={!msg.content} isComplete={!isMessageStreaming}>{msg.reasoning}</ThinkingDetails>
          </div>
        )}
        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="mb-3 ml-11 space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-[var(--color-text-muted)]">
              <Sparkles size={11} /> 执行记录 · {msg.toolCalls.length} 项
            </div>
            {msg.toolCalls.map(tc => (
              <ToolCallCard
                key={tc.id}
                name={tc.name}
                arguments={tc.arguments}
                result={tc.result ?? ''}
                error={tc.error ?? ''}
                isRunning={tc.status === 'running'}
                {...(tc.status ? { status: tc.status } : {})}
              />
            ))}
          </div>
        )}
        {(msg.content || (!msg.toolCalls?.length && !msg.reasoning)) && (
          <MessageContent
            content={msg.content}
            role={msg.role}
            timestamp={msg.timestamp}
            actions={
              msg.role === 'assistant' ? (
                <MessageActions
                  onCopy={() => navigator.clipboard.writeText(msg.content)}
                  onFeedback={(type) => api.submitFeedback(msg.id, type).catch(() => undefined)}
                  onEdit={() => startEditing(msg.id, msg.content)}
                />
              ) : undefined
            }
          />
        )}
        {isMessageStreaming && <span className="ml-11"><StreamingCursor /></span>}
      </motion.div>
    );
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      <div
        ref={scrollRef}
        onScroll={(event) => {
          const element = event.currentTarget;
          setIsNearBottom(element.scrollHeight - element.scrollTop - element.clientHeight < 120);
        }}
        className="relative flex-1 overflow-y-auto px-4 py-6 md:px-8 chat-container"
      >
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center py-8">
            <div className="w-full max-w-xl text-left">
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-accent-subtle)] border border-[var(--color-border-accent)]">
                <TerminalSquare size={22} className="text-[var(--color-accent)]" />
              </div>
              <p className="mb-2 text-[11px] font-semibold uppercase text-[var(--color-accent)]">Climber Agent</p>
              <h1 className="mb-2 text-xl font-semibold tracking-tight text-[var(--color-text-primary)]">{emptyStateTitle}</h1>
              <p className="mb-6 max-w-md text-sm leading-relaxed text-[var(--color-text-secondary)]">{emptyStateDescription}</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {suggestions.map((suggestion, idx) => (
                  <motion.button
                    key={idx}
                    onClick={() => onSend(suggestion)}
                    whileTap={{ scale: 0.96 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    className="group flex min-h-11 items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-left text-sm transition-colors duration-200 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-accent)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-3)]"
                  >
                    <span className="min-w-0 flex-1">{suggestion}</span>
                    <ArrowUpRight size={14} className="shrink-0 opacity-50 transition-opacity group-hover:opacity-100" />
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="mx-auto max-w-4xl space-y-5">
          <AnimatePresence initial={false}>
            {messages.map(renderMessageContent)}
          </AnimatePresence>
          {isLoading && !messages.some((message, index) => index === messages.length - 1 && message.role === 'assistant') && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="flex gap-3"
            >
              <div className="flex items-center justify-center rounded-xl w-9 h-9 shrink-0 bg-[var(--color-accent-subtle)] text-[var(--color-accent)]">
                <Bot size={16} />
              </div>
              <div className="flex-1">
                <ThinkingIndicator sparkle />
              </div>
            </motion.div>
          )}
        </div>
        {!isNearBottom && (
          <button
            type="button"
            onClick={() => scrollToBottom()}
            className="sticky bottom-2 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full shadow-md transition-colors bg-[var(--color-bg-surface-1)] border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]"
            aria-label="滚动到最新消息"
            title="滚动到最新消息"
          >
            <ArrowDown size={15} />
          </button>
        )}
      </div>

      <div className="border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-canvas)]">
        <ChatComposer
          onSend={onSend}
          placeholder={placeholder}
          {...(onStop ? { onStop } : {})}
          {...(isLoading !== undefined ? { isLoading } : {})}
        />
      </div>

      {/* Edit Drawer */}
      <Drawer.Root
        open={editState?.mode === 'modal'}
        onOpenChange={(open) => {
          if (!open) cancelEdit();
        }}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-md" />
          <Drawer.Content
            className="fixed inset-x-0 bottom-0 z-[60] mx-auto flex max-h-[85vh] w-full max-w-xl flex-col rounded-t-2xl outline-none bg-[var(--color-bg-surface-1)] border-t border-[var(--color-border-subtle)] pb-[env(safe-area-inset-bottom,0px)]"
          >
            <div className="mx-auto mt-3 h-1.5 w-12 shrink-0 rounded-full bg-[var(--color-bg-surface-3)]" />
            <div className="flex items-center justify-between px-5 pt-3 pb-2 border-b border-[var(--color-border-subtle)]">
              <h3 className="text-lg font-semibold tracking-tight text-[var(--color-text-primary)]">编辑消息</h3>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={saveEdit} className="rounded-lg">
                  <Check size={14} /> 保存
                </Button>
                <Button size="sm" variant="ghost" onClick={cancelEdit} className="rounded-lg">
                  <X size={14} />
                </Button>
              </div>
            </div>
            <div className="flex-1 p-6 overflow-y-auto">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-48 rounded-xl p-4 text-sm leading-relaxed resize-none focus:outline-none bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
                autoFocus
              />
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>

      {/* Floating Permission Dialog */}
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
