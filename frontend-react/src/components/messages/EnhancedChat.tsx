// @ts-nocheck
import React, { useState, useRef, useCallback } from 'react';
import {
  Send, Square, Paperclip, Image, Mic, X, FileText,
  Bot, User, Sparkles, Maximize2, Minimize2,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';
import { MessageBubble, MessageActions, ToolCallCard, ErrorBanner } from '../messages/MessageComponents';
import { ThinkingIndicator } from '../agent/ThinkingIndicator';

interface Attachment {
  id: string;
  type: 'file' | 'image';
  name: string;
  size: number;
  url: string;
  file: File;
}

interface MultimodalInputProps {
  onSend: (message: string, attachments?: Attachment[]) => void;
  onStop?: (() => void) | undefined;
  isLoading?: boolean | undefined;
  placeholder?: string;
  className?: string;
}

export function MultimodalInput({ onSend, onStop, isLoading, placeholder = '输入消息...（Enter 发送）', className }: MultimodalInputProps) {
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if ((input.trim() || attachments.length > 0) && !isLoading) {
      onSend(input.trim(), attachments);
      setInput('');
      setAttachments([]);
      setIsExpanded(false);
    }
  }, [input, attachments, isLoading, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }, [handleSubmit]);

  const handleFileSelect = (files: FileList | null, type: 'file' | 'image') => {
    if (!files) return;
    const newAttachments: Attachment[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      type,
      name: file.name,
      size: file.size,
      url: type === 'image' ? URL.createObjectURL(file) : '',
      file,
    }));
    setAttachments((prev) => [...prev, ...newAttachments]);
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const firstFile = files[0];
      if (firstFile) {
        handleFileSelect(files, firstFile.type.startsWith('image/') ? 'image' : 'file');
      }
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const toggleRecording = () => {
    setIsRecording(!isRecording);
  };

  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, isExpanded ? 400 : 120) + 'px';
  }, [isExpanded]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1048576).toFixed(1)}MB`;
  };

  return (
    <div
      className={cn('relative border-t p-4 transition-all duration-200', isDragOver && 'drop-zone-active', className)}
      style={{
        backgroundColor: 'var(--color-bg-surface-1)',
        borderColor: isDragOver ? 'var(--color-accent)' : 'var(--color-border-subtle)',
      }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {isDragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-[var(--color-accent-subtle)]/50 backdrop-blur-sm">
          <div className="text-center">
            <Paperclip size={24} className="mx-auto mb-2 text-[var(--color-accent)]" />
            <p className="text-sm font-medium text-[var(--color-accent)]">释放以上传文件</p>
          </div>
        </div>
      )}

      {attachments.length > 0 && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl border text-xs"
              style={{ backgroundColor: 'var(--color-bg-surface-2)', borderColor: 'var(--color-border-subtle)' }}
            >
              {att.type === 'image' ? (
                <Image size={14} className="text-[var(--color-accent)]" />
              ) : (
                <FileText size={14} className="text-[var(--color-text-muted)]" />
              )}
              <span className="text-[var(--color-text-secondary)] truncate max-w-[120px]">{att.name}</span>
              <span className="text-[var(--color-text-muted)]">{formatSize(att.size)}</span>
              <button
                onClick={() => removeAttachment(att.id)}
                className="p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors"
                aria-label="移除附件"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {isRecording && (
        <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-xl bg-[var(--color-error-subtle)] border border-[var(--color-error)]/20">
          <span className="w-2 h-2 rounded-full bg-[var(--color-error)] animate-pulse" />
          <span className="text-xs text-[var(--color-error)]">录音中...</span>
          <button
            onClick={toggleRecording}
            className="ml-auto px-2 py-0.5 rounded-lg text-[10px] bg-[var(--color-error)]/20 text-[var(--color-error)] hover:bg-[var(--color-error)]/30 transition-colors"
          >
            停止
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <div className="flex items-center gap-1 shrink-0">
          <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => handleFileSelect(e.target.files, 'file')} />
          <input ref={imageInputRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleFileSelect(e.target.files, 'image')} />
          <button type="button" onClick={() => fileInputRef.current?.click()} className="p-2.5 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors" aria-label="上传文件" title="上传文件">
            <Paperclip size={16} />
          </button>
          <button type="button" onClick={() => imageInputRef.current?.click()} className="p-2.5 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors" aria-label="上传图片" title="上传图片">
            <Image size={16} />
          </button>
          <button type="button" onClick={toggleRecording} className={cn('p-2.5 rounded-xl transition-colors', isRecording ? 'text-[var(--color-error)] bg-[var(--color-error-subtle)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]')} aria-label="语音输入" title="语音输入">
            <Mic size={16} />
          </button>
        </div>

        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoGrow(e); }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className={cn(
              'w-full px-4 py-3 rounded-xl text-sm resize-none transition-all duration-200',
              'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]',
              'text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]',
              'focus:outline-none focus:border-[var(--color-accent)]/30',
              isExpanded && 'min-h-[200px]'
            )}
            rows={1}
            aria-label="消息输入框"
          />
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button type="button" onClick={() => setIsExpanded(!isExpanded)} className="p-2.5 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors md:hidden" aria-label={isExpanded ? '收起' : '展开'}>
            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          {isLoading ? (
            <Button type="button" variant="destructive" size="icon" onClick={onStop} aria-label="停止生成">
              <Square size={16} />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={!input.trim() && attachments.length === 0} aria-label="发送消息">
              <Send size={16} />
            </Button>
          )}
        </div>
      </form>

      <div className="flex items-center justify-between mt-2 px-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-muted)]">Enter 发送 | Shift+Enter 换行</span>
          {attachments.length > 0 && (
            <span className="text-[10px] text-[var(--color-accent)]">{attachments.length} 个附件</span>
          )}
        </div>
        <span className="text-[10px] text-[var(--color-text-muted)]">支持拖拽上传</span>
      </div>
    </div>
  );
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: any[];
  reasoning?: string;
  timestamp?: Date;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSend: (message: string) => void;
  onStop?: (() => void) | undefined;
  isLoading?: boolean | undefined;
  error?: string | null;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  suggestions?: string[];
}

export function EnhancedChatInterface({
  messages,
  onSend,
  onStop,
  isLoading,
  error,
  emptyStateTitle = '开始新的对话',
  emptyStateDescription = '输入任何问题或任务，Climber 将为你自主执行。',
  suggestions = ['帮我分析代码', '写一个 Python 脚本', '解释这个错误'],
}: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const renderAvatar = (role: string) => {
    return (
      <div className={cn(
        'flex items-center justify-center rounded-xl text-xs font-bold shrink-0 w-8 h-8',
        role === 'user'
          ? 'bg-[var(--color-accent)] text-white'
          : 'bg-gradient-to-br from-purple-500 to-blue-500 text-white'
      )}>
        {role === 'user' ? <User size={14} /> : <Bot size={14} />}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-8 py-6 chat-container">
        {messages.length === 0 && !isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-lg">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[var(--color-accent)]/20 to-[#8B5CF6]/20 flex items-center justify-center mx-auto mb-6 p-5" style={{ boxShadow: '0 0 40px var(--color-accent-glow)' }}>
                <Sparkles size={36} className="text-[#8B5CF6]" />
              </div>
              <h3 className="text-2xl font-bold text-[var(--color-text-primary)] mb-3 tracking-tight">{emptyStateTitle}</h3>
              <p className="text-[var(--color-text-secondary)] text-sm mb-8 leading-relaxed max-w-sm mx-auto">{emptyStateDescription}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSend(suggestion)}
                    className="px-4 py-3 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-secondary)] hover:border-[var(--color-accent)]/40 hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-3)] transition-all duration-200 active:scale-[0.97] text-left flex items-center gap-3"
                  >
                    <span className="w-6 h-6 rounded-lg bg-[var(--color-accent-subtle)] flex items-center justify-center shrink-0">
                      <span className="text-[10px] text-[var(--color-accent)] font-bold">{idx + 1}</span>
                    </span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="space-y-5">
          {messages.map((msg) => (
            <div key={msg.id}>
              {msg.reasoning && !msg.content && (
                <div className="max-w-[85%]">
                  <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-3">
                    <div className="flex items-center gap-2">
                      <Bot size={12} className="text-[var(--color-text-muted)]" />
                      <span className="text-[10px] text-[var(--color-text-muted)]">思考过程</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-2 leading-relaxed whitespace-pre-wrap">{msg.reasoning}</p>
                  </div>
                </div>
              )}
              {msg.content && (
                <MessageBubble
                  content={msg.content}
                  role={msg.role as 'user' | 'assistant'}
                  timestamp={msg.timestamp}
                  isStreaming={isLoading && msg.role === 'assistant' && !msg.toolCalls}
                  avatar={renderAvatar(msg.role)}
                  actions={
                    msg.role === 'assistant' ? (
                      <MessageActions
                        onCopy={() => handleCopy(msg.content)}
                        onRegenerate={() => {}}
                        onQuote={() => handleCopy(`> ${msg.content}\n\n`)}
                      />
                    ) : (
                      <MessageActions
                        onCopy={() => handleCopy(msg.content)}
                        onEdit={() => {}}
                      />
                    )
                  }
                />
              )}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="flex flex-col gap-2 mt-2">
                  {msg.toolCalls.map((tc) => (
                    <ToolCallCard
                      key={tc.id}
                      name={tc.name}
                      arguments={tc.arguments}
                      result={tc.result}
                      error={tc.error}
                      isRunning={tc.status === 'running'}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
          {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/50 to-blue-500/50 text-white/70 w-8 h-8 shrink-0">
                <Bot size={14} />
              </div>
              <ThinkingIndicator sparkle />
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="px-4 pb-2">
          <ErrorBanner
            error={error}
            onRetry={() => onSend(messages[messages.length - 1]?.content || '')}
            onDismiss={() => {}}
            retryCount={0}
          />
        </div>
      )}

      <MultimodalInput
        onSend={(msg) => onSend(msg)}
        onStop={onStop}
        isLoading={isLoading}
      />
    </div>
  );
}

export default EnhancedChatInterface;
