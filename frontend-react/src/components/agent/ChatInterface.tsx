import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Send, Square, Bot, MessageSquare, Edit3, Check, X, Maximize2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import { MessageContent, MessageActions, ToolCallCard } from '../chat/MessageContent';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { ThinkingIndicator, ThinkingDots } from './ThinkingIndicator';
import { FloatingPermissionDialog, PermissionRequest } from './FloatingPermissionDialog';
import { api } from '../../api';

/* Reference: Lobe UI `chat/ChatItem/style.ts` - message enter animation */
const messageEnterStyle = `
  @keyframes message-enter {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes slide-in-top {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

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
    setPermissionRequests(prev => prev.filter(r => r.id !== id));
  }, []);

  const handleDenyPermission = useCallback(async (id: string) => {
    setPermissionRequests(prev => prev.filter(r => r.id !== id));
  }, []);

  const handleApproveAllPermissions = useCallback(async () => {
    setPermissionRequests([]);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    const styleId = 'message-enter-animation';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = messageEnterStyle;
      document.head.appendChild(style);
    }
  }, []);

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
                className="w-full bg-transparent text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none resize-none"
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
        <div className="flex gap-3 max-w-[85%] message-enter">
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
        </div>
      );
    }

    if (msg.reasoning && !msg.content) {
      return (
        <div className="max-w-[85%] message-enter">
          <ThinkingDetails defaultOpen={true}>
            {msg.reasoning}
          </ThinkingDetails>
        </div>
      );
    }

    return (
      <div className={cn('group flex gap-3 max-w-[85%] message-enter', msg.role === 'user' ? 'flex-row-reverse ml-auto' : '')}>
        <div>
          <MessageContent
            content={msg.content}
            role={msg.role}
            timestamp={msg.timestamp}
            actions={
              msg.role === 'assistant' ? (
                <MessageActions
                  onCopy={() => navigator.clipboard.writeText(msg.content)}
                  onFeedback={(type) => console.log('feedback', type)}
                  onEdit={() => startEditing(msg.id, msg.content)}
                />
              ) : undefined
            }
          />
        </div>
      </div>
    );
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-8 py-6 chat-container">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md fade-enter">
              <div className="w-18 h-18 rounded-3xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 flex items-center justify-center mx-auto mb-5 p-4">
                <MessageSquare size={28} className="text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2 tracking-tight">{emptyStateTitle}</h3>
              <p className="text-gray-400 text-sm mb-6 leading-relaxed">{emptyStateDescription}</p>
              <div className="flex flex-wrap justify-center gap-2">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSend(suggestion)}
                    className="px-4 py-2 bg-white/[0.04] border border-white/[0.08] rounded-2xl text-xs text-gray-400 hover:border-blue-500/40 hover:text-gray-200 hover:bg-white/[0.06] transition-all duration-200 active:scale-[0.97]"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="space-y-5">
          {messages.map(renderMessageContent)}
          {isLoading && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/50 to-blue-500/50 text-white/70 w-9 h-9 shrink-0">
                <Bot size={16} />
              </div>
              <div className="flex-1">
                <ThinkingIndicator sparkle />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="border-t border-white/[0.04] p-4 md:p-5 bg-[#0F0F14]/90 backdrop-blur-xl">
        <div className="flex gap-2.5 max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className="chat-input-mobile flex-1 px-5 py-3 bg-white/[0.04] border border-white/[0.08] rounded-3xl text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-[#3B82F6]/40 focus:bg-white/[0.06] transition-all duration-200 resize-none"
            rows={1}
          />
          {isLoading ? (
            <Button type="button" variant="destructive" size="icon" onClick={onStop} className="rounded-2xl">
              <Square size={16} />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={!input.trim()} className="rounded-2xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30">
              <Send size={16} />
            </Button>
          )}
        </div>
      </form>

      {/* Edit Modal */}
      {editState?.mode === 'modal' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-black/80 backdrop-blur-md fade-enter">
          <div className="bg-[#121218] border border-white/[0.08] rounded-3xl w-full h-full max-w-7xl max-h-[90vh] flex flex-col shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
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
                className="w-full h-full bg-transparent text-gray-200 text-sm leading-relaxed resize-none focus:outline-none"
                autoFocus
              />
            </div>
          </div>
        </div>
      )}

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
