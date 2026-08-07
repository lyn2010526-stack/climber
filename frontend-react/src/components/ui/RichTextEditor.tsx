import React, { useState, useRef, useCallback, useId } from 'react';
import { cn } from '../../lib/utils';
import {
  Bold, Italic, Underline, Strikethrough, Code, List, ListOrdered,
  Link, Image, Quote, Heading1, Heading2, Undo, Redo, Eye, Edit3, Maximize2, Minimize2,
} from 'lucide-react';

export interface RichTextEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  label?: string;
  hint?: string;
  error?: string;
  minHeight?: number;
  maxHeight?: number;
  className?: string;
  id?: string;
  readOnly?: boolean;
}

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ icon, label, onClick, active, disabled }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    title={label}
    aria-label={label}
    aria-pressed={active}
    className={cn(
      'p-[var(--space-1-5)] rounded-[var(--radius-md)] transition-colors',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      active ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-bg-hover)] hover:text-[var(--text-primary)]'
    )}
  >
    {icon}
  </button>
);

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value: controlledValue,
  onChange,
  placeholder = 'Start typing...',
  disabled = false,
  label,
  hint,
  error,
  minHeight = 200,
  maxHeight = 500,
  className,
  id,
  readOnly = false,
}) => {
  const [internalValue, setInternalValue] = useState(controlledValue || '');
  const [isPreview, setIsPreview] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const generatedId = useId();
  const editorId = id || generatedId;

  const currentValue = controlledValue !== undefined ? controlledValue : internalValue;

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    if (controlledValue === undefined) setInternalValue(newValue);
    onChange?.(newValue);
  }, [controlledValue, onChange]);

  const insertText = useCallback((before: string, after: string = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = currentValue.substring(start, end);
    const newValue = currentValue.substring(0, start) + before + selectedText + after + currentValue.substring(end);
    if (controlledValue === undefined) setInternalValue(newValue);
    onChange?.(newValue);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    }, 0);
  }, [currentValue, controlledValue, onChange]);

  const toolbarGroups = [
    [
      { icon: <Heading1 className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Heading 1', action: () => insertText('# ') },
      { icon: <Heading2 className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Heading 2', action: () => insertText('## ') },
    ],
    [
      { icon: <Bold className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Bold', action: () => insertText('**', '**') },
      { icon: <Italic className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Italic', action: () => insertText('*', '*') },
      { icon: <Underline className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Underline', action: () => insertText('<u>', '</u>') },
      { icon: <Strikethrough className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Strikethrough', action: () => insertText('~~', '~~') },
      { icon: <Code className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Code', action: () => insertText('`', '`') },
    ],
    [
      { icon: <List className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Bullet List', action: () => insertText('- ') },
      { icon: <ListOrdered className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Numbered List', action: () => insertText('1. ') },
      { icon: <Quote className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Quote', action: () => insertText('> ') },
    ],
    [
      { icon: <Link className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Link', action: () => insertText('[', '](url)') },
      { icon: <Image className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />, label: 'Image', action: () => insertText('![alt](', ')') },
    ],
  ];

  const renderPreview = (markdown: string) => {
    let html = markdown
      .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/~~(.+?)~~/g, '<del>$1</del>')
      .replace(/`(.+?)`/g, '<code class="px-1 py-0.5 bg-[var(--surface-bg-subtle)] rounded text-[var(--font-size-xs)] font-mono">$1</code>')
      .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
      .replace(/^> (.+)$/gm, '<blockquote class="border-l-2 border-[var(--accent)] pl-3 italic text-[var(--text-muted)]">$1</blockquote>')
      .replace(/\n/g, '<br/>');
    return html;
  };

  return (
    <div className={cn(
      'flex flex-col border border-[var(--border-default)] rounded-[var(--radius-xl)] overflow-hidden bg-[var(--surface-bg)]',
      isFullscreen && 'fixed inset-4 z-[var(--z-modal)]',
      error && 'border-[var(--border-error)]',
      className
    )}>
      {(label || hint) && (
        <div className="px-[var(--space-4)] py-[var(--space-3)] border-b border-[var(--border-subtle)]">
          {label && <label htmlFor={editorId} className="text-[var(--font-size-sm)] font-medium text-[var(--text-primary)]">{label}</label>}
          {hint && <p className="text-[var(--font-size-xs)] text-[var(--text-muted)] mt-[var(--space-0-5)]">{hint}</p>}
        </div>
      )}

      <div className="flex items-center gap-[var(--space-1)] px-[var(--space-3)] py-[var(--space-2)] border-b border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)]">
        {toolbarGroups.map((group, groupIndex) => (
          <React.Fragment key={groupIndex}>
            {group.map((item, itemIndex) => (
              <ToolbarButton
                key={itemIndex}
                icon={item.icon}
                label={item.label}
                onClick={item.action}
                disabled={disabled || readOnly || isPreview}
              />
            ))}
            {groupIndex < toolbarGroups.length - 1 && (
              <div className="w-px h-5 bg-[var(--border-subtle)] mx-[var(--space-1)]" />
            )}
          </React.Fragment>
        ))}
        <div className="flex-1" />
        <ToolbarButton
          icon={isPreview ? <Edit3 className="w-[var(--icon-sm)] h-[var(--icon-sm)]" /> : <Eye className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />}
          label={isPreview ? 'Edit' : 'Preview'}
          onClick={() => setIsPreview(!isPreview)}
          active={isPreview}
          disabled={disabled || readOnly}
        />
        <ToolbarButton
          icon={isFullscreen ? <Minimize2 className="w-[var(--icon-sm)] h-[var(--icon-sm)]" /> : <Maximize2 className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />}
          label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          onClick={() => setIsFullscreen(!isFullscreen)}
          disabled={disabled}
        />
      </div>

      <div className="flex-1 relative">
        {isPreview ? (
          <div
            className="p-[var(--space-4)] overflow-y-auto prose-sm"
            style={{ minHeight: `${minHeight}px`, maxHeight: isFullscreen ? 'none' : `${maxHeight}px` }}
            dangerouslySetInnerHTML={{ __html: renderPreview(currentValue) }}
          />
        ) : (
          <textarea
            ref={textareaRef}
            id={editorId}
            value={currentValue}
            onChange={handleChange}
            placeholder={placeholder}
            disabled={disabled}
            readOnly={readOnly}
            className={cn(
              'w-full h-full resize-none p-[var(--space-4)] bg-transparent text-[var(--text-primary)] text-[var(--font-size-sm)] leading-[var(--line-height-relaxed)] placeholder:text-[var(--text-muted)]',
              'focus-visible:outline-none',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
            style={{ minHeight: `${minHeight}px`, maxHeight: isFullscreen ? 'none' : `${maxHeight}px` }}
            aria-label={label || 'Rich text editor'}
          />
        )}
      </div>

      <div className="px-[var(--space-3)] py-[var(--space-1-5)] border-t border-[var(--border-subtle)] bg-[var(--surface-bg-subtle)] flex items-center justify-between">
        <span className="text-[10px] text-[var(--text-muted)]">
          {currentValue.length} characters
        </span>
        <span className="text-[10px] text-[var(--text-muted)]">
          Markdown supported
        </span>
      </div>
    </div>
  );
};

export { RichTextEditor };
