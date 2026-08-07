import { useState, useRef, useCallback } from 'react';
import { Send, Square, Paperclip, Image, Mic, X, FileText } from 'lucide-react';
import { cn } from '../../lib/utils';

interface Attachment {
  id: string;
  type: 'file' | 'image';
  name: string;
  size: number;
  url: string;
}

interface ChatInputProps {
  onSend: (message: string, attachments?: Attachment[]) => void;
  onStop?: (() => void) | undefined;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  quotedMessage?: string | null;
  onCancelQuote?: (() => void) | undefined;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ChatInput({
  onSend,
  onStop,
  isLoading,
  placeholder = '输入消息... (Enter 发送，Shift+Enter 换行)',
  className,
  quotedMessage,
  onCancelQuote,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if ((!input.trim() && attachments.length === 0) || isLoading) return;
      onSend(input.trim(), attachments.length > 0 ? attachments : undefined);
      setInput('');
      setAttachments([]);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    },
    [input, attachments, isLoading, onSend],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const autoGrow = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  const handleFileSelect = (files: FileList | null, type: 'file' | 'image') => {
    if (!files) return;
    const newAttachments: Attachment[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      type,
      name: file.name,
      size: file.size,
      url: type === 'image' ? URL.createObjectURL(file) : '',
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
      const type = files[0]?.type.startsWith('image/') ? 'image' : 'file';
      handleFileSelect(files, type);
    }
  }, []);

  return (
    <div
      className={cn(
        'relative border-t p-4 transition-colors duration-200',
        isDragOver ? 'bg-[var(--color-accent-subtle)]/30' : 'bg-[var(--color-bg-surface-1)]',
        className,
      )}
      style={{ borderColor: 'var(--color-border-subtle)' }}
      onDrop={handleDrop}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
    >
      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-[var(--color-accent-subtle)]/40 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-2">
            <Paperclip size={24} className="text-[var(--color-accent)]" />
            <span className="text-sm font-medium text-[var(--color-accent)]">释放以上传文件</span>
          </div>
        </div>
      )}

      {/* Quoted message */}
      {quotedMessage && (
        <div
          className="flex items-center gap-2 mb-3 px-3 py-2 rounded-xl text-xs"
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            border: '1px solid var(--color-border-subtle)',
          }}
        >
          <span className="text-[var(--color-text-muted)] truncate flex-1">{quotedMessage}</span>
          <button
            onClick={onCancelQuote}
            className="p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-xs border"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                borderColor: 'var(--color-border-subtle)',
              }}
            >
              {att.type === 'image' ? (
                <Image size={13} className="text-[var(--color-accent)]" />
              ) : (
                <FileText size={13} className="text-[var(--color-text-muted)]" />
              )}
              <span className="text-[var(--color-text-secondary)] truncate max-w-[120px]">
                {att.name}
              </span>
              <span className="text-[var(--color-text-muted)]">{formatSize(att.size)}</span>
              <button
                onClick={() => removeAttachment(att.id)}
                className="p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors"
              >
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input row */}
      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        {/* Action buttons */}
        <div className="flex items-center gap-1 shrink-0">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files, 'file')}
          />
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files, 'image')}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
            title="上传文件"
          >
            <Paperclip size={16} />
          </button>
          <button
            type="button"
            onClick={() => imageInputRef.current?.click()}
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
            title="上传图片"
          >
            <Image size={16} />
          </button>
          <button
            type="button"
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
            title="语音输入"
          >
            <Mic size={16} />
          </button>
        </div>

        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoGrow(e);
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className={cn(
              'w-full px-4 py-3 text-sm resize-none rounded-2xl transition-all duration-200',
              'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]',
              'text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]',
              'focus:outline-none focus:border-[var(--color-accent)]/30 focus:bg-[var(--color-bg-surface-3)]',
            )}
            style={{
              minHeight: '44px',
              maxHeight: '200px',
            }}
          />
        </div>

        {/* Send/Stop button */}
        <div className="shrink-0">
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="flex items-center justify-center w-11 h-11 rounded-2xl bg-[var(--color-error)]/90 text-white hover:bg-[var(--color-error)] transition-colors shadow-lg shadow-[var(--color-error)]/20"
              title="停止生成"
            >
              <Square size={16} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() && attachments.length === 0}
              className={cn(
                'flex items-center justify-center w-11 h-11 rounded-2xl transition-all duration-200',
                'bg-[var(--color-accent)] text-white shadow-lg shadow-[var(--color-accent)]/20',
                'hover:brightness-110 hover:shadow-[var(--color-accent)]/30',
                'disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed',
              )}
              title="发送"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </form>

      {/* Keyboard hint */}
      <div className="flex items-center justify-between mt-2 px-1">
        <span className="text-[10px] text-[var(--color-text-muted)]">
          Enter 发送 | Shift+Enter 换行
        </span>
        {attachments.length > 0 && (
          <span className="text-[10px] text-[var(--color-accent)]">
            {attachments.length} 个附件
          </span>
        )}
      </div>
    </div>
  );
}
