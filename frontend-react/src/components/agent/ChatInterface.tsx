import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Drawer } from 'vaul';
import { Send, Square, Bot, Edit3, Check, X, Maximize2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import { MessageContent, MessageActions, ToolCallCard } from '../chat/MessageContent';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { ThinkingIndicator } from './ThinkingIndicator';
import { FloatingPermissionDialog } from './FloatingPermissionDialog';
import type { PermissionRequest } from './FloatingPermissionDialog';

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
  onSend: (message: string) => void;
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
  const [input, setInput] = useState('');
  const [editState, setEditState] = useState<EditState>(null);
  const [editContent, setEditContent] = useState('');
  const [permissionRequests, setPermissionRequests] = useState<PermissionRequest[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

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

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput('');
    }
  }, [input, isLoading, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }, [handleSubmit]);

  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, []);

  const renderMessageContent = (msg: Message) => {
    const isEditing = editState?.messageId === msg.id;

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

    if (msg.role === 'tool' && msg.toolCalls) {
      return msg.toolCalls.map(tc => (
        <ToolCallCard
          key={tc.id}
          name={tc.name}
          arguments={tc.arguments}
          result={tc.result ?? ''}
          error={tc.error ?? ''}
          isRunning={tc.status === 'running'}
        />
      ));
    }

    if (msg.toolCalls && msg.toolCalls.length > 0) {
      return (
        <motion.div
          layout
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, transition: { duration: 0.15 } }}
          transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.9 }}
          className="flex gap-3 max-w-[85%]"
        >
          <div className="flex items-center justify-center rounded-xl w-9 h-9 shrink-0" style={{
            background: 'linear-gradient(135deg, var(--color-accent), #8b5cf6)',
            color: '#ffffff',
          }}>
            <Bot size={16} />
          </div>
          <div className="flex flex-col gap-2 min-w-0 flex-1">
            {msg.toolCalls.map(tc => (
              <ToolCallCard
                key={tc.id}
                name={tc.name}
                arguments={tc.arguments}
                result={tc.result ?? ''}
                error={tc.error ?? ''}
                isRunning={tc.status === 'running'}
              />
            ))}
          </div>
        </motion.div>
      );
    }

    if (msg.reasoning && !msg.content) {
      return (
        <motion.div
          layout
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, transition: { duration: 0.15 } }}
          transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.9 }}
          className="max-w-[85%]"
        >
          <ThinkingDetails defaultOpen={true}>
            {msg.reasoning}
          </ThinkingDetails>
        </motion.div>
      );
    }

    return (
      <motion.div
        layout
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.15 } }}
        transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.9 }}
        className={cn('group flex gap-3 max-w-[85%]', msg.role === 'user' ? 'flex-row-reverse ml-auto' : '')}
      >
        <div>
          <MessageContent
            content={msg.content}
            role={msg.role}
            timestamp={msg.timestamp}
            actions={
              msg.role === 'assistant' ? (
                <MessageActions
                  onCopy={() => navigator.clipboard.writeText(msg.content)}
                  onFeedback={(type) => {
                    api.submitFeedback(msg.id, type).catch(() => undefined);
                  }}
                  onEdit={() => startEditing(msg.id, msg.content)}
                />
              ) : undefined
            }
          />
          {isLoading && msg.role === 'assistant' && !msg.toolCalls && <StreamingCursor />}
        </div>
      </motion.div>
    );
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-8 py-6 chat-container">
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
        <div className="space-y-4">
          <AnimatePresence initial={false}>
            {messages.map(renderMessageContent)}
          </AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="flex gap-3 max-w-[85%]"
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
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 md:p-4"
        style={{
          borderTop: '1px solid var(--color-border-subtle)',
          backgroundColor: 'rgba(17, 17, 19, 0.85)',
          backdropFilter: 'blur(20px)',
        }}
      >
        <div className="flex gap-2 max-w-4xl mx-auto">
          {isLoading ? (
            <Button type="button" variant="destructive" size="icon" onClick={onStop} className="rounded-lg">
              <Square size={14} />
            </Button>
          ) : (
            <>
              <div className="flex-1 flex items-end gap-2 rounded-lg px-3" style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-subtle)',
              }}>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => { setInput(e.target.value); autoGrow(e); }}
                  onKeyDown={handleKeyDown}
                  placeholder={placeholder}
                  disabled={isLoading}
                  className="flex-1 py-2.5 bg-transparent text-sm resize-none focus:outline-none min-h-[36px] max-h-[200px]"
                  style={{ color: 'var(--color-text-primary)' }}
                  rows={1}
                />
                <motion.button
                  type="submit"
                  disabled={!input.trim()}
                  whileTap={input.trim() ? { scale: 0.9 } : { scale: 1 }}
                  whileHover={input.trim() ? { scale: 1.05 } : { scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                  className="flex items-center justify-center w-8 h-8 rounded-lg mb-1.5 shrink-0 transition-all duration-200"
                  style={{
                    backgroundColor: input.trim() ? 'var(--color-accent)' : 'var(--color-bg-surface-3)',
                    color: input.trim() ? '#ffffff' : 'var(--color-text-muted)',
                  }}
                >
                  <Send size={14} />
                </motion.button>
              </div>
            </>
          )}
        </div>
      </form>

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