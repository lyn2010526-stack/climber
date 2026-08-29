import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, ChevronDown, Command, FileText, Paperclip, Square, X } from 'lucide-react';
import { api } from '../../api';
import { cn } from '../../lib/utils';

interface ChatComposerProps {
  onSend: (message: string, model?: { provider?: string; modelId?: string }) => void;
  onStop?: () => void;
  isLoading?: boolean;
  placeholder: string;
}

const commands = [
  { name: '/plan', label: '制定计划', prompt: '请先分析目标、约束与风险，再制定可执行计划：' },
  { name: '/research', label: '深度调研', prompt: '请围绕以下主题进行深度调研并给出来源：' },
  { name: '/review', label: '代码审查', prompt: '请审查以下代码，优先指出缺陷、风险和缺失测试：' },
  { name: '/explain', label: '解释内容', prompt: '请清晰解释以下内容，并给出关键示例：' },
];

export function ChatComposer({ onSend, onStop, isLoading, placeholder }: ChatComposerProps) {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [models, setModels] = useState<Array<{ id?: string; model_id?: string; name?: string; provider?: string }>>([]);
  const [model, setModel] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const showCommands = input.startsWith('/') && !input.includes(' ');

  useEffect(() => {
    api.listModels().then(data => {
      setModels(data);
      const first = data[0];
      if (first) setModel(`${first.provider || ''}:${first.id || first.model_id || ''}`);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    const focusComposer = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isEditing = target?.matches('input, textarea, [contenteditable="true"]');
      if (event.key === '/' && !isEditing) {
        event.preventDefault();
        textareaRef.current?.focus();
        setInput('/');
      }
      if (event.key === 'Escape' && isLoading) onStop?.();
    };
    document.addEventListener('keydown', focusComposer);
    return () => document.removeEventListener('keydown', focusComposer);
  }, [isLoading, onStop]);

  const resize = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
  }, []);

  const submit = useCallback(() => {
    if (isLoading || (!input.trim() && files.length === 0)) return;
    const attachmentContext = files.length > 0
      ? `[附件: ${files.map(file => file.name).join(', ')}]\n\n`
      : '';
    const selected = models.find(item => `${item.provider || ''}:${item.id || item.model_id || ''}` === model);
    const provider = selected?.provider;
    const modelId = selected?.model_id || selected?.id;
    const modelSelection = provider || modelId
      ? { ...(provider ? { provider } : {}), ...(modelId ? { modelId } : {}) }
      : undefined;
    onSend(`${attachmentContext}${input.trim()}`.trim(), modelSelection);
    setInput('');
    setFiles([]);
    requestAnimationFrame(resize);
  }, [files, input, isLoading, model, models, onSend, resize]);

  return (
    <div className="relative mx-auto w-full max-w-4xl px-4 pb-4 pt-2 md:px-6">
      {showCommands && (
        <div className="absolute bottom-full left-6 z-20 mb-2 w-72 overflow-hidden rounded-xl p-1 shadow-xl" style={{ backgroundColor: 'var(--color-bg-surface-1)', border: '1px solid var(--color-border-default)' }} role="listbox" aria-label="斜杠命令">
          <div className="px-2 py-1.5 text-[11px] font-semibold uppercase" style={{ color: 'var(--color-text-muted)' }}>快速指令</div>
          {commands.filter(command => command.name.startsWith(input)).map(command => (
            <button key={command.name} type="button" onClick={() => { setInput(`${command.prompt} `); textareaRef.current?.focus(); requestAnimationFrame(resize); }} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-[var(--color-bg-surface-2)]" role="option">
              <Command size={14} style={{ color: 'var(--color-accent)' }} />
              <span className="flex-1"><span className="block text-xs font-semibold">{command.name}</span><span className="block text-[11px]" style={{ color: 'var(--color-text-muted)' }}>{command.label}</span></span>
            </button>
          ))}
        </div>
      )}

      <div className="overflow-hidden rounded-xl shadow-sm transition-[border-color,box-shadow] focus-within:border-[var(--color-border-accent)] focus-within:shadow-md" style={{ backgroundColor: 'var(--color-bg-surface-1)', border: '1px solid var(--color-border-default)' }}>
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 px-3 pt-3">
            {files.map((file, index) => (
              <span key={`${file.name}-${index}`} className="flex max-w-48 items-center gap-1.5 rounded-lg px-2 py-1 text-[11px]" style={{ backgroundColor: 'var(--color-bg-surface-2)', color: 'var(--color-text-secondary)' }}>
                <FileText size={12} className="shrink-0" /><span className="truncate">{file.name}</span>
                <button type="button" onClick={() => setFiles(current => current.filter((_, fileIndex) => fileIndex !== index))} aria-label={`移除 ${file.name}`}><X size={11} /></button>
              </span>
            ))}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={event => { setInput(event.target.value); resize(); }}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          className="block min-h-14 max-h-[220px] w-full resize-none bg-transparent px-4 pb-2 pt-3 text-sm leading-6 outline-none"
          style={{ color: 'var(--color-text-primary)' }}
          rows={1}
          aria-label="消息输入框"
        />
        <div className="flex h-11 items-center gap-1 px-2 pb-2">
          <input ref={fileRef} type="file" multiple className="hidden" onChange={event => setFiles(current => [...current, ...Array.from(event.target.files || [])].slice(0, 5))} />
          <button type="button" onClick={() => fileRef.current?.click()} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--color-bg-surface-2)]" style={{ color: 'var(--color-text-muted)' }} title="添加附件" aria-label="添加附件"><Paperclip size={15} /></button>
          {models.length > 0 && (
            <label className="relative flex h-8 items-center rounded-lg px-2 hover:bg-[var(--color-bg-surface-2)]" style={{ color: 'var(--color-text-secondary)' }}>
              <select value={model} onChange={event => setModel(event.target.value)} className="max-w-36 appearance-none bg-transparent pr-5 text-[11px] font-medium outline-none" aria-label="选择模型">
                {models.map(item => {
                  const value = `${item.provider || ''}:${item.id || item.model_id || ''}`;
                  return <option key={value} value={value}>{item.name || item.model_id || item.id}{item.provider ? ` · ${item.provider}` : ''}</option>;
                })}
              </select>
              <ChevronDown size={11} className="pointer-events-none absolute right-1.5" />
            </label>
          )}
          <span className="ml-auto hidden text-[11px] sm:block" style={{ color: 'var(--color-text-muted)' }}>Enter 发送 · Shift+Enter 换行</span>
          {isLoading ? (
            <button type="button" onClick={onStop} className="ml-2 flex h-8 w-8 items-center justify-center rounded-lg text-white" style={{ backgroundColor: 'var(--color-error)' }} title="停止生成 (Esc)" aria-label="停止生成"><Square size={12} fill="currentColor" /></button>
          ) : (
            <button type="button" onClick={submit} disabled={!input.trim() && files.length === 0} className={cn('ml-2 flex h-8 w-8 items-center justify-center rounded-lg text-white transition-all', (!input.trim() && files.length === 0) && 'opacity-35')} style={{ backgroundColor: 'var(--color-accent)' }} title="发送消息" aria-label="发送消息"><ArrowUp size={16} strokeWidth={2.5} /></button>
          )}
        </div>
      </div>
      <div className="mt-1.5 flex min-h-4 items-center justify-center gap-1.5 text-[11px]" style={{ color: 'var(--color-text-muted)' }} aria-live="polite">
        {isLoading ? (
          <><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] animate-pulse" /><span>Agent 正在执行，可按 Esc 停止</span></>
        ) : (
          <span>Climber 可能产生不准确结果，执行关键操作前请确认。</span>
        )}
      </div>
    </div>
  );
}
