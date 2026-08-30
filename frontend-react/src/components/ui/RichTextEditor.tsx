import { useState, useCallback, useRef, forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import {
  Bold, Italic, Underline, Strikethrough, Code, List, ListOrdered,
  AlignLeft, AlignCenter, AlignRight, Link, Image, Quote,
  Heading1, Heading2, Heading3, Undo, Redo, Minus,
  Pilcrow,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const ALLOWED_HTML_ATTRIBUTES = new Set(['class', 'href', 'src', 'alt', 'title', 'target', 'rel']);
const ALLOWED_URL_SCHEMES = /^(?:https?:|mailto:|tel:|\/|#)/i;

function sanitizeEditorHtml(html: string): string {
  if (typeof document === 'undefined') {
    return html.replace(/[&<>"']/g, (character) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character] ?? character
    ));
  }

  const template = document.createElement('template');
  template.innerHTML = html;
  template.content.querySelectorAll('script,style,iframe,object,embed,link,meta').forEach((node) => node.remove());
  template.content.querySelectorAll<HTMLElement>('*').forEach((element) => {
    [...element.attributes].forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      if (name.startsWith('on') || !ALLOWED_HTML_ATTRIBUTES.has(name)) {
        element.removeAttribute(attribute.name);
      }
    });

    for (const name of ['href', 'src']) {
      const value = element.getAttribute(name);
      if (value && !ALLOWED_URL_SCHEMES.test(value.trim())) {
        element.removeAttribute(name);
      }
    }
    if (element.getAttribute('target') === '_blank') {
      element.setAttribute('rel', 'noopener noreferrer');
    }
  });
  return template.innerHTML;
}

const editorVariants = cva(
  'flex flex-col rounded-xl border overflow-hidden transition-all duration-200',
  {
    variants: {
      variant: {
        default: 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)]',
        outline: 'border-[var(--color-border-strong)] bg-transparent',
        filled: 'border-transparent bg-[var(--color-bg-surface-2)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

const toolbarVariants = cva(
  'flex flex-wrap items-center gap-0.5 border-b px-2 py-1.5',
  {
    variants: {
      variant: {
        default: 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]',
        minimal: 'border-transparent bg-transparent',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

const contentVariants = cva(
  'flex-1 min-h-[120px] px-4 py-3 text-sm text-[var(--color-text-primary)] outline-none overflow-y-auto leading-relaxed',
  {
    variants: {
      size: {
        sm: 'min-h-[80px] text-xs',
        md: 'min-h-[120px] text-sm',
        lg: 'min-h-[200px] text-base',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

interface RichTextEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  maxLength?: number;
  className?: string;
  variant?: 'default' | 'outline' | 'filled';
  toolbarVariant?: 'default' | 'minimal';
  size?: 'sm' | 'md' | 'lg';
  autoFocus?: boolean;
  onFocus?: () => void;
  onBlur?: () => void;
}

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  isActive?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

function ToolbarButton({ icon, label, isActive, disabled, onClick }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'flex h-7 w-7 items-center justify-center rounded-md transition-all duration-150',
        isActive && 'bg-blue-500/20 text-[var(--color-accent)]',
        !isActive && 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-3)]',
        disabled && 'opacity-30 cursor-not-allowed',
      )}
    >
      {icon}
    </button>
  );
}

interface ToolbarDividerProps {
  className?: string;
}

function ToolbarDivider({ className }: ToolbarDividerProps) {
  return <div className={cn('h-5 w-px bg-[var(--color-bg-surface-3)] mx-1', className)} />;
}

function execCommand(command: string, value?: string) {
  document.execCommand(command, false, value);
}

const RichTextEditor = forwardRef<HTMLDivElement, RichTextEditorProps>(
  ({ value, onChange, placeholder = '开始输入...', disabled, maxLength, className, variant = 'default', toolbarVariant = 'default', size = 'md', autoFocus, onFocus, onBlur }, ref) => {
    const [activeFormats, setActiveFormats] = useState<Set<string>>(new Set());
    const editorRef = useRef<HTMLDivElement>(null);
    const [charCount, setCharCount] = useState(0);

    const checkActiveFormats = useCallback(() => {
      const formats = new Set<string>();
      const queryState = (cmd: string) => {
        try {
          return document.queryCommandState(cmd);
        } catch {
          return false;
        }
      };
      if (queryState('bold')) formats.add('bold');
      if (queryState('italic')) formats.add('italic');
      if (queryState('underline')) formats.add('underline');
      if (queryState('strikeThrough')) formats.add('strikeThrough');
      if (queryState('insertUnorderedList')) formats.add('ul');
      if (queryState('insertOrderedList')) formats.add('ol');
      if (queryState('justifyLeft')) formats.add('left');
      if (queryState('justifyCenter')) formats.add('center');
      if (queryState('justifyRight')) formats.add('right');
      setActiveFormats(formats);
    }, []);

    const handleInput = useCallback(() => {
      if (editorRef.current) {
        const text = editorRef.current.innerHTML;
        onChange?.(text);
        setCharCount(editorRef.current.textContent?.length || 0);
        checkActiveFormats();
      }
    }, [onChange, checkActiveFormats]);

    const handleCommand = useCallback((command: string, value?: string) => {
      editorRef.current?.focus();
      execCommand(command, value);
      handleInput();
    }, [handleInput]);

    const handleLinkInsert = useCallback(() => {
      const url = prompt('请输入链接地址:', 'https://');
      if (url) handleCommand('createLink', url);
    }, [handleCommand]);

    const handleImageInsert = useCallback(() => {
      const url = prompt('请输入图片地址:', 'https://');
      if (url) handleCommand('insertImage', url);
    }, [handleCommand]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        execCommand('insertHTML', '&emsp;');
      }
    }, []);

    const setHeading = useCallback((level: string) => {
      handleCommand('formatBlock', level);
    }, [handleCommand]);

    return (
      <div ref={ref} className={cn(editorVariants({ variant }), disabled && 'opacity-50 pointer-events-none', className)}>
        <div className={cn(toolbarVariants({ variant: toolbarVariant }))}>
          <ToolbarButton
            icon={<Undo className="h-3.5 w-3.5" />}
            label="撤销"
            onClick={() => handleCommand('undo')}
          />
          <ToolbarButton
            icon={<Redo className="h-3.5 w-3.5" />}
            label="重做"
            onClick={() => handleCommand('redo')}
          />
          <ToolbarDivider />
          <ToolbarButton
            icon={<Heading1 className="h-3.5 w-3.5" />}
            label="标题1"
            onClick={() => setHeading('H1')}
          />
          <ToolbarButton
            icon={<Heading2 className="h-3.5 w-3.5" />}
            label="标题2"
            onClick={() => setHeading('H2')}
          />
          <ToolbarButton
            icon={<Heading3 className="h-3.5 w-3.5" />}
            label="标题3"
            onClick={() => setHeading('H3')}
          />
          <ToolbarButton
            icon={<Pilcrow className="h-3.5 w-3.5" />}
            label="段落"
            onClick={() => setHeading('P')}
          />
          <ToolbarDivider />
          <ToolbarButton
            icon={<Bold className="h-3.5 w-3.5" />}
            label="粗体"
            isActive={activeFormats.has('bold')}
            onClick={() => handleCommand('bold')}
          />
          <ToolbarButton
            icon={<Italic className="h-3.5 w-3.5" />}
            label="斜体"
            isActive={activeFormats.has('italic')}
            onClick={() => handleCommand('italic')}
          />
          <ToolbarButton
            icon={<Underline className="h-3.5 w-3.5" />}
            label="下划线"
            isActive={activeFormats.has('underline')}
            onClick={() => handleCommand('underline')}
          />
          <ToolbarButton
            icon={<Strikethrough className="h-3.5 w-3.5" />}
            label="删除线"
            isActive={activeFormats.has('strikeThrough')}
            onClick={() => handleCommand('strikeThrough')}
          />
          <ToolbarButton
            icon={<Code className="h-3.5 w-3.5" />}
            label="行内代码"
            onClick={() => handleCommand('formatBlock', 'CODE')}
          />
          <ToolbarDivider />
          <ToolbarButton
            icon={<List className="h-3.5 w-3.5" />}
            label="无序列表"
            isActive={activeFormats.has('ul')}
            onClick={() => handleCommand('insertUnorderedList')}
          />
          <ToolbarButton
            icon={<ListOrdered className="h-3.5 w-3.5" />}
            label="有序列表"
            isActive={activeFormats.has('ol')}
            onClick={() => handleCommand('insertOrderedList')}
          />
          <ToolbarButton
            icon={<Quote className="h-3.5 w-3.5" />}
            label="引用"
            onClick={() => handleCommand('formatBlock', 'BLOCKQUOTE')}
          />
          <ToolbarButton
            icon={<Minus className="h-3.5 w-3.5" />}
            label="分割线"
            onClick={() => handleCommand('insertHorizontalRule')}
          />
          <ToolbarDivider />
          <ToolbarButton
            icon={<AlignLeft className="h-3.5 w-3.5" />}
            label="左对齐"
            isActive={activeFormats.has('left')}
            onClick={() => handleCommand('justifyLeft')}
          />
          <ToolbarButton
            icon={<AlignCenter className="h-3.5 w-3.5" />}
            label="居中"
            isActive={activeFormats.has('center')}
            onClick={() => handleCommand('justifyCenter')}
          />
          <ToolbarButton
            icon={<AlignRight className="h-3.5 w-3.5" />}
            label="右对齐"
            isActive={activeFormats.has('right')}
            onClick={() => handleCommand('justifyRight')}
          />
          <ToolbarDivider />
          <ToolbarButton
            icon={<Link className="h-3.5 w-3.5" />}
            label="插入链接"
            onClick={handleLinkInsert}
          />
          <ToolbarButton
            icon={<Image className="h-3.5 w-3.5" />}
            label="插入图片"
            onClick={handleImageInsert}
          />
        </div>

        <div
          ref={editorRef}
          contentEditable={!disabled}
          role="textbox"
          aria-multiline="true"
          aria-label="富文本编辑器"
          suppressContentEditableWarning
          className={cn(
            contentVariants({ size }),
            '[&]:empty:before:content-[attr(data-placeholder)] [&]:empty:before:text-[var(--color-text-muted)] [&]:empty:before:pointer-events-none',
            '[&_h1]:text-xl [&_h1]:font-bold [&_h1]:text-[var(--color-text-primary)] [&_h1]:mb-2',
            '[&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-[var(--color-text-primary)] [&_h2]:mb-2',
            '[&_h3]:text-base [&_h3]:font-medium [&_h3]:text-[var(--color-text-primary)] [&_h3]:mb-1',
            '[&_p]:mb-1',
            '[&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-2',
            '[&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-2',
            '[&_blockquote]:border-l-2 [&_blockquote]:border-[var(--color-border-strong)] [&_blockquote]:pl-3 [&_blockquote]:text-[var(--color-text-secondary)] [&_blockquote]:italic [&_blockquote]:my-2',
            '[&_code]:bg-[var(--color-bg-surface-3)] [&_code]:rounded [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-sm [&_code]:text-violet-300 [&_code]:font-mono',
            '[&_a]:text-[var(--color-accent)] [&_a]:underline',
            '[&_hr]:border-[var(--color-border-default)] [&_hr]:my-3',
          )}
          data-placeholder={placeholder}
          dangerouslySetInnerHTML={value ? { __html: sanitizeEditorHtml(value) } : undefined}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          onFocus={onFocus}
          onBlur={onBlur}
          autoFocus={autoFocus}
        />

        {maxLength && (
          <div className="border-t border-[var(--color-border-subtle)] px-4 py-1.5 flex justify-end">
            <span className={cn(
              'text-[10px]',
              charCount > maxLength ? 'text-red-400' : 'text-[var(--color-text-muted)]',
            )}>
              {charCount} / {maxLength}
            </span>
          </div>
        )}
      </div>
    );
  }
);
RichTextEditor.displayName = 'RichTextEditor';

export { RichTextEditor, editorVariants, toolbarVariants, contentVariants };
export type { RichTextEditorProps };
