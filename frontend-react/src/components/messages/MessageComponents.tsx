import { useState } from 'react';
import {
  Copy, Check, ThumbsUp, ThumbsDown, Edit3, RotateCcw, Quote,
  Play, ChevronDown, Terminal,
  Loader2, AlertCircle, Clock, Code2,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { Badge } from '../ui/Badge';

/* ─── Streaming Cursor ─── */
export const StreamingCursor = () => (
  <span className="inline-block w-[2px] h-4 ml-0.5 rounded-full bg-gradient-to-b from-[var(--color-accent)] to-[#8B5CF6] animate-pulse" />
);

/* ─── Message Bubble ─── */
interface MessageBubbleProps {
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp?: Date | undefined;
  isStreaming?: boolean | undefined;
  actions?: React.ReactNode;
  avatar?: React.ReactNode;
  className?: string;
}

export function MessageBubble({ content, role, timestamp, isStreaming, actions, avatar, className }: MessageBubbleProps) {
  const isUser = role === 'user';
  const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <div className={cn('group flex gap-3 message-enter', isUser ? 'flex-row-reverse ml-auto' : '', className)}>
      {avatar && <div className="shrink-0 mt-1">{avatar}</div>}
      <div className={cn('flex flex-col gap-1 min-w-0 max-w-[85%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'px-4 py-3 text-sm leading-[1.7] shadow-lg',
            isUser
              ? 'bg-[var(--color-accent)] text-white rounded-2xl rounded-br-lg'
              : 'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] rounded-2xl rounded-tl-lg backdrop-blur-sm'
          )}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{content}</span>
          ) : (
            <MarkdownRenderer content={content} />
          )}
          {isStreaming && <StreamingCursor />}
        </div>
        <div className={cn('flex items-center gap-2 px-1 transition-opacity duration-200', isUser ? 'flex-row-reverse' : '')}>
          {timeStr && <span className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</span>}
          {actions && <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">{actions}</div>}
        </div>
      </div>
    </div>
  );
}

/* ─── Message Actions ─── */
interface MessageActionsProps {
  onCopy: () => void;
  onEdit?: (() => void) | undefined;
  onRegenerate?: (() => void) | undefined;
  onQuote?: (() => void) | undefined;
  onFeedback?: ((type: 'up' | 'down') => void) | undefined;
  compact?: boolean | undefined;
}

export function MessageActions({ onCopy, onEdit, onRegenerate, onQuote, onFeedback, compact }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = () => {
    onCopy?.();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedback(feedback === type ? null : type);
    onFeedback?.(type);
  };

  const btnClass = cn(
    'p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors',
    compact ? 'p-1' : ''
  );

  return (
    <div className="flex items-center gap-0.5">
      <button onClick={handleCopy} className={btnClass} aria-label="复制" title="复制">
        {copied ? <Check size={12} className="text-[var(--color-success)]" /> : <Copy size={12} />}
      </button>
      {onQuote && (
        <button onClick={onQuote} className={btnClass} aria-label="引用" title="引用">
          <Quote size={12} />
        </button>
      )}
      {onEdit && (
        <button onClick={onEdit} className={btnClass} aria-label="编辑" title="编辑">
          <Edit3 size={12} />
        </button>
      )}
      {onRegenerate && (
        <button onClick={onRegenerate} className={btnClass} aria-label="重新生成" title="重新生成">
          <RotateCcw size={12} />
        </button>
      )}
      {onFeedback && (
        <>
          <button
            onClick={() => handleFeedback('up')}
            className={cn(btnClass, feedback === 'up' && 'text-[var(--color-success)]')}
            aria-label="有用"
            title="有用"
          >
            <ThumbsUp size={12} />
          </button>
          <button
            onClick={() => handleFeedback('down')}
            className={cn(btnClass, feedback === 'down' && 'text-[var(--color-error)]')}
            aria-label="无用"
            title="无用"
          >
            <ThumbsDown size={12} />
          </button>
        </>
      )}
    </div>
  );
}

/* ─── Tool Call Card ─── */
interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  isRunning?: boolean;
  duration?: number;
  retryCount?: number;
}

export function ToolCallCard({ name, arguments: args, result, error, isRunning, duration, retryCount }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const status = error ? 'error' : isRunning ? 'running' : result ? 'success' : 'running';

  const statusConfig = {
    running: { color: 'var(--color-accent)', bg: 'var(--color-accent-subtle)', label: '执行中' },
    success: { color: 'var(--color-success)', bg: 'var(--color-success-subtle)', label: '成功' },
    error: { color: 'var(--color-error)', bg: 'var(--color-error-subtle)', label: '失败' },
  };
  const config = statusConfig[status];

  return (
    <div className="tool-call-card max-w-[85%]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors cursor-pointer"
        style={{ borderBottom: expanded ? '1px solid var(--color-border-subtle)' : 'none' }}
        aria-expanded={expanded}
      >
        <div className="p-1.5 rounded-xl flex items-center justify-center" style={{ backgroundColor: config.bg, color: config.color }}>
          <Terminal size={12} />
        </div>
        <span className="text-xs font-semibold flex-1 text-[var(--color-text-primary)]">{name}</span>
        {Object.keys(args).length > 0 && (
          <span className="text-[10px] text-[var(--color-text-muted)] truncate max-w-[120px]">
            ({Object.keys(args).slice(0, 2).join(', ')})
          </span>
        )}
        {isRunning && (
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: config.bg, color: config.color }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: config.color }} />
            {config.label}
          </span>
        )}
        {!isRunning && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: config.bg, color: config.color }}>
            {config.label}
          </span>
        )}
        {duration !== undefined && (
          <span className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
            <Clock size={10} />
            {(duration / 1000).toFixed(1)}s
          </span>
        )}
        {retryCount !== undefined && retryCount > 0 && (
          <span className="text-[10px] text-[var(--color-warning)]">retry:{retryCount}</span>
        )}
        <div className="p-1 rounded-lg transition-transform duration-200" style={{ color: 'var(--color-text-muted)', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <ChevronDown size={14} />
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3 slide-down">
          {Object.keys(args).length > 0 && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-[var(--color-text-muted)]">Input</div>
              <pre className="code-block text-xs whitespace-pre-wrap">{JSON.stringify(args, null, 2)}</pre>
            </div>
          )}
          {result && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-[var(--color-text-muted)]">Output</div>
              <pre className="code-block text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">{result}</pre>
            </div>
          )}
          {error && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-error)' }}>Error</div>
              <pre className="code-block text-xs" style={{ color: 'var(--color-error)' }}>{error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Code Block ─── */
interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  showCopy?: boolean;
  showRun?: boolean;
  onRun?: () => void;
  filename?: string;
  className?: string;
}

export function CodeBlock({ code, language = 'text', showLineNumbers = true, showCopy = true, showRun = false, onRun, filename, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<string | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = () => {
    setRunning(true);
    setOutput(null);
    onRun?.();
    setTimeout(() => {
      setRunning(false);
      setOutput('// Execution simulated');
    }, 1000);
  };

  const lines = code.split('\n');
  const runnableLanguages = ['python', 'javascript', 'typescript', 'bash', 'sh', 'shell'];
  const canRun = showRun && runnableLanguages.includes(language);

  return (
    <div className={cn('rounded-xl border overflow-hidden', className)} style={{ borderColor: 'var(--color-code-border)', backgroundColor: 'var(--color-code-bg)' }}>
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--color-code-border)', backgroundColor: 'var(--color-bg-surface-2)' }}>
        <div className="flex items-center gap-2">
          <Code2 size={12} className="text-[var(--color-text-muted)]" />
          {filename && <span className="text-[10px] font-medium text-[var(--color-text-secondary)]">{filename}</span>}
          <Badge variant="default" size="xs">{language}</Badge>
        </div>
        <div className="flex items-center gap-1">
          {canRun && (
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] text-[var(--color-success)] hover:bg-[var(--color-success-subtle)] transition-colors disabled:opacity-50"
              aria-label="运行代码"
            >
              {running ? <Loader2 size={10} className="animate-spin" /> : <Play size={10} />}
              运行
            </button>
          )}
          {showCopy && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
              aria-label="复制代码"
            >
              {copied ? <Check size={10} className="text-[var(--color-success)]" /> : <Copy size={10} />}
              {copied ? '已复制' : '复制'}
            </button>
          )}
        </div>
      </div>
      <div className="overflow-x-auto">
        <pre className="p-4 text-xs leading-[1.7] font-mono">
          {lines.map((line, i) => (
            <div key={i} className="flex">
              {showLineNumbers && (
                <span className="inline-block w-8 text-right pr-3 select-none text-[var(--color-text-muted)] opacity-50">
                  {i + 1}
                </span>
              )}
              <span className="flex-1 text-[var(--color-code-text)]">{line || ' '}</span>
            </div>
          ))}
        </pre>
      </div>
      {output && (
        <div className="border-t px-3 py-2" style={{ borderColor: 'var(--color-code-border)' }}>
          <div className="flex items-center gap-1.5 mb-1">
            <Terminal size={10} className="text-[var(--color-text-muted)]" />
            <span className="text-[10px] font-medium text-[var(--color-text-muted)]">Output</span>
          </div>
          <pre className="text-[10px] text-[var(--color-success)] font-mono">{output}</pre>
        </div>
      )}
    </div>
  );
}

/* ─── Thinking Block ─── */
interface ThinkingBlockProps {
  content: string;
  defaultOpen?: boolean;
  tokens?: number;
}

export function ThinkingBlock({ content, defaultOpen = false, tokens }: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(defaultOpen);

  return (
    <div className="max-w-[85%] rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-[var(--color-bg-surface-2)] rounded-xl transition-colors"
        aria-expanded={expanded}
      >
        <div className="w-1 h-4 rounded-full bg-[var(--color-text-muted)]" />
        <span className="text-xs font-medium text-[var(--color-text-muted)]">思考过程</span>
        {tokens !== undefined && <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">{tokens} tokens</span>}
        {expanded ? <ChevronDown size={14} className="text-[var(--color-text-muted)]" /> : <Copy size={0} className="hidden" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3 pl-10 slide-down">
          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>
      )}
    </div>
  );
}

/* ─── Error Banner ─── */
interface ErrorBannerProps {
  error: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  retryCount?: number;
  maxRetries?: number;
}

export function ErrorBanner({ error, onRetry, onDismiss, retryCount = 0, maxRetries = 3 }: ErrorBannerProps) {
  const canRetry = retryCount < maxRetries;

  return (
    <div className="mx-auto max-w-md px-4 py-3 rounded-xl border border-[var(--color-error)]/20 bg-[var(--color-error-subtle)] flex items-start gap-3 fade-enter" role="alert">
      <AlertCircle size={16} className="text-[var(--color-error)] shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[var(--color-error)] leading-relaxed">{error}</p>
        <div className="flex items-center gap-2 mt-2">
          {canRetry && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium bg-[var(--color-error)]/20 text-[var(--color-error)] hover:bg-[var(--color-error)]/30 transition-colors"
            >
              <RotateCcw size={10} />
              重试 ({retryCount}/{maxRetries})
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="px-2.5 py-1 rounded-lg text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            >
              忽略
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Message Group ─── */
interface MessageGroupProps {
  role: 'user' | 'assistant';
  messages: {
    id: string;
    content: string;
    toolCalls?: any[];
    reasoning?: string;
    timestamp?: Date;
    isStreaming?: boolean;
  }[];
  onCopy: (content: string) => void;
  onEdit: (id: string, content: string) => void;
  onRegenerate: (id: string) => void;
  onQuote: (content: string) => void;
  onFeedback: (id: string, type: 'up' | 'down') => void;
  avatar?: React.ReactNode;
}

export function MessageGroup({ role, messages, onCopy, onEdit, onRegenerate, onQuote, onFeedback, avatar }: MessageGroupProps) {
  const isUser = role === 'user';

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse ml-auto' : '')}>
      {avatar && <div className="shrink-0 mt-1">{avatar}</div>}
      <div className={cn('flex flex-col gap-2 min-w-0 max-w-[85%]', isUser ? 'items-end' : 'items-start')}>
        {messages.map((msg) => (
          <div key={msg.id} className="w-full">
            {msg.reasoning && !msg.content && (
              <ThinkingBlock content={msg.reasoning} />
            )}
            {msg.content && (
              <MessageBubble
                content={msg.content}
                role={role}
                timestamp={msg.timestamp}
                isStreaming={msg.isStreaming}
                actions={
                  <MessageActions
                    onCopy={() => onCopy(msg.content)}
                    onEdit={!isUser ? () => onEdit(msg.id, msg.content) : undefined}
                    onRegenerate={!isUser ? () => onRegenerate(msg.id) : undefined}
                    onQuote={() => onQuote(msg.content)}
                    onFeedback={!isUser ? (type) => onFeedback(msg.id, type) : undefined}
                  />
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
      </div>
    </div>
  );
}
