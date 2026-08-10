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


  /* Streaming cursor - Reference: Claude / Vercel AI streaming */
  const StreamingCursor = () => (
    <span className="inline-block w-[2px] h-4 ml-0.5 rounded-full bg-gradient-to-b from-[#5E6AD2] to-[#8B5CF6] animate-pulse" />
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

  /* Reference: Lobe UI EditableMessage - mode switching */
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

  /* Auto-grow textarea - Reference: Linear / Raycast input */
  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, []);

  /* Reference: Lobe UI ChatItem - Actions hover + layout mode */
  const renderMessageContent = (msg: Message) => {
    const isEditing = editState?.messageId === msg.id;

    if (isEditing && (editState.mode === 'edit' || editState.mode === 'modal')) {
      return (
        <div className={cn('flex gap-3 max-w-[85%]', msg.role === 'user' ? 'flex-row-reverse ml-auto' : '')}>
          <div className="flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 text-white w-9 h-9 shrink-0">
            <Edit3 size={16} />
          </div>
          <div className={cn('flex flex-col gap-2 min-w-0 flex-1')}>
            <div className="px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-2xl focus-within:border-[#3B82F6]/40 transition-colors duration-200">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none resize-none"
                rows={3}
                autoFocus
              />
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={saveEdit} className="rounded-xl">
                <Check size={12} /> 保存
              </Button>
              <Button size="sm" variant="ghost" onClick={cancelEdit} className="rounded-xl">
                <X size={12} /> 取消
              </Button>
              <Button size="sm" variant="ghost" onClick={openModal} className="rounded-xl">
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
          <div className="flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 text-white w-9 h-9 shrink-0">
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
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[#5E6AD2]/20 to-[#8B5CF6]/20 flex items-center justify-center mx-auto mb-6 p-5" style={{ boxShadow: '0 0 40px rgba(94,106,210,0.15)' }}>
                <Bot size={36} className="text-[#8B5CF6]" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">{emptyStateTitle}</h3>
              <p className="text-[var(--color-text-secondary)] text-sm mb-8 leading-relaxed max-w-sm mx-auto">{emptyStateDescription}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
                {suggestions.map((suggestion, idx) => (
                  <motion.button
                    key={idx}
                    onClick={() => onSend(suggestion)}
                    whileTap={{ scale: 0.96 }}
                    whileHover={{ scale: 1.02 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    className="px-4 py-3 bg-white/[0.03] border border-white/[0.06] rounded-2xl text-sm text-[var(--color-text-secondary)] hover:border-[#5E6AD2]/40 hover:text-[var(--color-text-primary)] hover:bg-white/[0.06] transition-colors duration-200 text-left flex items-center gap-3"
                  >
                    <span className="w-6 h-6 rounded-lg bg-[#5E6AD2]/10 flex items-center justify-center shrink-0">
                      <span className="text-[10px] text-[#5E6AD2] font-bold">{idx + 1}</span>
                    </span>
                    {suggestion}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="space-y-5">
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
              <div className="flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/50 to-blue-500/50 text-white/70 w-9 h-9 shrink-0">
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
       <form onSubmit={handleSubmit} className="border-t border-white/[0.04] p-4 md:p-5 bg-[#0F0F14]/90 backdrop-blur-xl">
         <div className="flex gap-2.5 max-w-4xl mx-auto">
           {isLoading ? (
             <Button type="button" variant="destructive" size="icon" onClick={onStop} className="rounded-2xl">
               <Square size={16} />
             </Button>
           ) : (
             <>
               <Button type="button" variant="ghost" size="icon" className="rounded-2xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]">
                 <span className="text-base leading-none">+</span>
               </Button>
               <div className="flex-1 flex flex-col">
                 <div className="flex items-center gap-2">
                   <textarea
                     ref={inputRef}
                     value={input}
                     onChange={(e) => { setInput(e.target.value); autoGrow(e); }}
                     onKeyDown={handleKeyDown}
                     placeholder={placeholder}
                     disabled={isLoading}
                     className="flex-1 px-5 py-3 bg-white/[0.04] border border-white/[0.08] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#5E6AD2]/40 focus:bg-white/[0.06] transition-all duration-200 resize-none min-h-[44px]"
                     rows={1}
                   />
                 </div>
                 <div className="flex items-center justify-between mt-2 px-1">
                   <div className="flex items-center gap-2">
                     <kbd className="text-[10px] px-1.5 py-0.5 rounded-md font-mono" style={{
                       backgroundColor: 'var(--color-bg-surface-3)',
                       color: 'var(--color-text-muted)',
                       border: '1px solid var(--color-border-subtle)'
                     }}>⌘K</kbd>
                     <span className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>命令面板</span>
                   </div>
                   {input.startsWith('/') && (
                     <div className="flex items-center gap-2">
                       <span className="text-[10px]" style={{ color: 'var(--color-accent)' }}>斜杠命令模式</span>
                     </div>
                   )}
                 </div>
               </div>
               <motion.button
                  type="submit"
                  disabled={!input.trim()}
                   whileTap={input.trim() ? { scale: 0.9 } : { scale: 1 }}
                   whileHover={input.trim() ? { scale: 1.05 } : { scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                  className="flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-[#5E6AD2] to-[#8B5CF6] text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#5E6AD2]/20 hover:shadow-[#5E6AD2]/30 transition-shadow"
                >
                  <Send size={16} />
                </motion.button>
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
            className="fixed inset-x-0 bottom-0 z-[60] mx-auto flex max-h-[85vh] w-full max-w-xl flex-col rounded-t-3xl outline-none"
            style={{
              backgroundColor: 'var(--color-bg-surface-1)',
              borderTop: '1px solid var(--color-border-subtle)',
              paddingBottom: 'env(safe-area-inset-bottom, 0px)',
            }}
          >
            <div className="mx-auto mt-3 h-1.5 w-12 shrink-0 rounded-full bg-white/[0.15]" />
            <div className="flex items-center justify-between px-5 pt-3 pb-2 border-b border-white/[0.06]">
              <h3 className="text-lg font-semibold text-white tracking-tight">编辑消息</h3>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={saveEdit} className="rounded-xl">
                  <Check size={14} /> 保存
                </Button>
                <Button size="sm" variant="ghost" onClick={cancelEdit} className="rounded-xl">
                  <X size={14} />
                </Button>
              </div>
            </div>
            <div className="flex-1 p-6 overflow-y-auto">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-48 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4 text-[var(--color-text-primary)] text-sm leading-relaxed resize-none focus:outline-none focus:border-[#5E6AD2]/40"
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
