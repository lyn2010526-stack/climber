import React, { useState } from 'react';
import {
  Save, X, Eye, Edit3, FileText, Clock,
  Hash, Type, Bold, Italic, List, Code,
  Image, Link2, Heading1, Heading2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface MemoryFileEditorProps {
  initialContent?: string;
  fileName?: string;
  onSave?: (content: string, commitMessage: string) => void;
  onClose?: () => void;
}

export function MemoryFileEditor({
  initialContent = '',
  fileName = 'untitled.md',
  onSave,
  onClose,
}: MemoryFileEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [view, setView] = useState<'edit' | 'preview' | 'split'>('split');
  const [commitMessage, setCommitMessage] = useState('');
  const [showCommitDialog, setShowCommitDialog] = useState(false);

  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const charCount = content.length;
  const lineCount = content.split('\n').length;

  const handleSave = () => {
    if (!commitMessage.trim()) {
      setShowCommitDialog(true);
      return;
    }
    onSave?.(content, commitMessage);
    setShowCommitDialog(false);
    setCommitMessage('');
  };

  const insertMarkdown = (prefix: string, suffix: string = '') => {
    setContent(prev => prev + prefix + suffix);
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-white/[0.06] bg-[#0D0D12]/80 backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <FileText size={15} className="text-blue-400" />
          <span className="text-sm font-medium text-white">{fileName}</span>
          <span className="px-2 py-0.5 rounded-md text-[10px] bg-amber-500/10 text-amber-400 font-medium">
            {view === 'edit' ? '编辑' : view === 'preview' ? '预览' : '分屏'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setView('edit')}
            className={cn(
              'p-1.5 rounded-lg transition-all',
              view === 'edit' ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            )}
          >
            <Edit3 size={13} />
          </button>
          <button
            onClick={() => setView('split')}
            className={cn(
              'p-1.5 rounded-lg transition-all',
              view === 'split' ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            )}
          >
            <Code size={13} />
          </button>
          <button
            onClick={() => setView('preview')}
            className={cn(
              'p-1.5 rounded-lg transition-all',
              view === 'preview' ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            )}
          >
            <Eye size={13} />
          </button>
          <div className="w-px h-4 bg-white/[0.06] mx-1" />
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-[11px] font-medium hover:bg-blue-500/15 transition-all"
          >
            <Save size={12} />
            保存
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.06] transition-all">
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Toolbar */}
      {view !== 'preview' && (
        <div className="flex items-center gap-0.5 px-4 py-2 border-b border-white/[0.04]">
          <ToolbarButton icon={Heading1} onClick={() => insertMarkdown('# ')} />
          <ToolbarButton icon={Heading2} onClick={() => insertMarkdown('## ')} />
          <div className="w-px h-4 bg-white/[0.06] mx-1" />
          <ToolbarButton icon={Bold} onClick={() => insertMarkdown('**', '**')} />
          <ToolbarButton icon={Italic} onClick={() => insertMarkdown('*', '*')} />
          <ToolbarButton icon={Code} onClick={() => insertMarkdown('`', '`')} />
          <div className="w-px h-4 bg-white/[0.06] mx-1" />
          <ToolbarButton icon={List} onClick={() => insertMarkdown('- ')} />
          <ToolbarButton icon={Hash} onClick={() => insertMarkdown('1. ')} />
          <div className="w-px h-4 bg-white/[0.06] mx-1" />
          <ToolbarButton icon={Link2} onClick={() => insertMarkdown('[', '](url)')} />
          <ToolbarButton icon={Image} onClick={() => insertMarkdown('![alt](', ')')} />
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 flex overflow-hidden">
        {view !== 'preview' && (
          <div className={cn('flex-1 flex flex-col overflow-hidden', view === 'split' && 'border-r border-white/[0.06]')}>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
               className="flex-1 w-full p-4 bg-transparent text-sm text-[var(--color-text-primary)] font-mono leading-relaxed resize-none focus:outline-none"
              placeholder="在此输入 Markdown..."
            />
          </div>
        )}
        {view !== 'edit' && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="prose prose-invert prose-sm max-w-none">
              <pre                className="text-sm text-[var(--color-text-secondary)] font-mono whitespace-pre-wrap leading-relaxed">
                {content || '*空文件*'}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
         <div className="flex items-center justify-between px-4 py-2 border-t border-white/[0.06]">
           <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1"><Type size={10} />{charCount} 字符</span>
          <span className="flex items-center gap-1"><FileText size={10} />{wordCount} 词</span>
          <span className="flex items-center gap-1"><List size={10} />{lineCount} 行</span>
        </div>
         <div className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
          <Clock size={10} />
          <span>Markdown</span>
        </div>
      </div>

      {/* Commit dialog */}
      {showCommitDialog && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="w-80 bg-[#1A1A24] border border-white/[0.08] rounded-2xl p-5 shadow-2xl">
            <h4 className="text-sm font-semibold text-white mb-3">提交更改</h4>
            <input
              type="text"
              value={commitMessage}
              onChange={e => setCommitMessage(e.target.value)}
              placeholder="提交信息..."
               className="w-full h-9 px-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/40 transition-all mb-4"
              autoFocus
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setShowCommitDialog(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-[var(--color-text-secondary)] hover:text-white hover:bg-white/[0.06] transition-all"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                className="px-3 py-1.5 rounded-lg text-xs bg-blue-500/10 text-blue-400 font-medium hover:bg-blue-500/15 transition-all"
              >
                确认保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolbarButton({ icon: Icon, onClick }: { icon: React.ComponentType<any>; onClick: () => void }) {
  return (
      <button
        onClick={onClick}
        className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/[0.06] transition-all"
      >
      <Icon size={14} />
    </button>
  );
}
