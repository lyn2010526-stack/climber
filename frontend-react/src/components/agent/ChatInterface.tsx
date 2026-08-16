import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Drawer } from 'vaul';
import { ArrowDown, Bot, Edit3, Check, X, Maximize2, Sparkles } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import { MessageContent, MessageActions, ToolCallCard } from '../chat/MessageContent';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { ThinkingIndicator } from './ThinkingIndicator';
import { FloatingPermissionDialog } from './FloatingPermissionDialog';
import type { PermissionRequest } from './FloatingPermissionDialog';
import { ChatComposer } from './ChatComposer';

  const StreamingCursor = () => (
    <span className="inline-block w-[2px] h-4 ml-0.5 rounded-full animate-pulse" style={{ backgroundColor: 'var(--color-accent)' }} />
  );

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
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

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
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

  const handleApprovePermission = useCallback(async (id: string) => {
    try {
      await api.resolvePermission(id, 'allow');
    } catch { /* skip */ }
    setPermissionRequests(prev => prev.filter(r => r.id !== id));
  }, []);

  const handleDenyPermission = useCallback(async (id: string) => {
    try {
      await api.resolvePermission(id, 'deny');
    } catch { /* skip */ }
    setPermissionRequests(prev => prev.filter(r => r.id !== id));
  }, []);

  const handleApproveAllPermissions = useCallback(async () => {
    const ids = permissionRequests.map(r => r.id);
    await Promise.all(ids.map(id => api.resolvePermission(id, 'allow').catch(() => undefined)));
    setPermissionRequests([]);
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

  const renderMessageContent = (msg: Message, index: number) => {
    const isEditing = editState?.messageId === msg.id;
    const isLatestMessage = index === messages.length - 1;
    const isMessageStreaming = Boolean(isLoading && isLatestMessage && msg.role === 'assistant');

    if (isEditing && (editState.mode === 'edit' || editState.mode === 'modal')) {
      return (
        <div className={cn('flex gap-3 max-w-[85%]', msg.role === 'user' ? 'flex-row-reverse ml-auto' : '')}>
          <div className="flex items-center justify-center rounded-xl w-9 h-9 shrink-0" style={{
            background: 'linear-gradient(135deg, var(--color-accent), #8b5cf6)',
            color: '#ffffff',
          }}>
            <Edit3 size={16} />
          </div>
          <div className={cn('flex flex-col gap-2 min-w-0 flex-1')}>
            <div className="px-4 py-3 rounded-xl" style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              border: '1px solid var(--color-border-default)',
            }}>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full bg-transparent text-sm resize-none focus:outline-none"
                style={{ color: 'var(--color-text-primary)' }}
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
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase" style={{ color: 'var(--color-text-muted)' }}>
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
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-lg">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5" style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15))',
                boxShadow: '0 0 30px rgba(99,102,241,0.12)',
              }}>
                <Bot size={28} style={{ color: 'var(--color-accent)' }} />
              </div>
              <h3 className="text-xl font-semibold mb-2 tracking-tight" style={{ color: 'var(--color-text-primary)' }}>{emptyStateTitle}</h3>
              <p className="text-sm mb-6 leading-relaxed max-w-sm mx-auto" style={{ color: 'var(--color-text-secondary)' }}>{emptyStateDescription}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-md mx-auto">
                {suggestions.map((suggestion, idx) => (
                  <motion.button
                    key={idx}
                    onClick={() => onSend(suggestion)}
                    whileTap={{ scale: 0.96 }}
                    whileHover={{ scale: 1.02 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    className="px-3.5 py-2.5 rounded-lg text-sm text-left flex items-center gap-2.5 transition-all duration-200"
                    style={{
                      backgroundColor: 'var(--color-bg-surface-2)',
                      border: '1px solid var(--color-border-subtle)',
                      color: 'var(--color-text-secondary)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-border-accent)';
                      e.currentTarget.style.color = 'var(--color-text-primary)';
                      e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-3)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                      e.currentTarget.style.color = 'var(--color-text-secondary)';
                      e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
                    }}
                  >
                    <span className="w-5 h-5 rounded-lg flex items-center justify-center shrink-0 text-[10px] font-bold"
                      style={{ backgroundColor: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}
                    >
                      {idx + 1}
                    </span>
                    {suggestion}
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
              <div className="flex items-center justify-center rounded-xl w-9 h-9 shrink-0"
                style={{ backgroundColor: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}
              >
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
            className="sticky bottom-2 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full shadow-md transition-colors hover:bg-[var(--color-bg-surface-2)]"
            style={{ backgroundColor: 'var(--color-bg-surface-1)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-secondary)' }}
            aria-label="滚动到最新消息"
            title="滚动到最新消息"
          >
            <ArrowDown size={15} />
          </button>
        )}
      </div>

      <div style={{ borderTop: '1px solid var(--color-border-subtle)', backgroundColor: 'var(--color-bg-canvas)' }}>
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
            className="fixed inset-x-0 bottom-0 z-[60] mx-auto flex max-h-[85vh] w-full max-w-xl flex-col rounded-t-2xl outline-none"
            style={{
              backgroundColor: 'var(--color-bg-surface-1)',
              borderTop: '1px solid var(--color-border-subtle)',
              paddingBottom: 'env(safe-area-inset-bottom, 0px)',
            }}
          >
            <div className="mx-auto mt-3 h-1.5 w-12 shrink-0 rounded-full" style={{ backgroundColor: 'var(--color-bg-surface-3)' }} />
            <div className="flex items-center justify-between px-5 pt-3 pb-2" style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <h3 className="text-lg font-semibold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>编辑消息</h3>
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
                className="w-full h-48 rounded-xl p-4 text-sm leading-relaxed resize-none focus:outline-none"
                style={{
                  backgroundColor: 'var(--color-bg-surface-2)',
                  border: '1px solid var(--color-border-subtle)',
                  color: 'var(--color-text-primary)',
                }}
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
