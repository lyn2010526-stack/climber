import React, { useRef, useCallback, useState, useEffect } from 'react';
import { cn } from '../../lib/utils';
import { AlertCircle, Check, Copy } from 'lucide-react';

export interface CodeEditorProps {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  language?: string;
  theme?: 'vs-dark' | 'light';
  readOnly?: boolean;
  minimap?: boolean;
  lineNumbers?: 'on' | 'off' | 'relative';
  wordWrap?: 'on' | 'off' | 'wordWrapColumn' | 'bounded';
  autoComplete?: boolean;
  height?: string;
  placeholder?: string;
  errors?: { line: number; column?: number; message: string; severity: 'error' | 'warning' | 'info' }[];
  className?: string;
  ariaLabel?: string;
  onMount?: () => void;
}

const LANGUAGE_SYNTAX: Record<string, { patterns: { token: string; regex: string }[] }> = {
  javascript: {
    patterns: [
      { token: 'keyword', regex: '\\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|throw|new|this|typeof|instanceof)\\b' },
      { token: 'string', regex: '(["\'])(?:(?=(\\\\?))\\2.)*?\\1' },
      { token: 'comment', regex: '//.*' },
      { token: 'number', regex: '\\b\\d+\\.?\\d*\\b' },
    ],
  },
  typescript: {
    patterns: [
      { token: 'keyword', regex: '\\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|throw|new|this|typeof|instanceof|interface|type|enum|implements|extends|abstract|private|public|protected|readonly)\\b' },
      { token: 'string', regex: '(["\'])(?:(?=(\\\\?))\\2.)*?\\1' },
      { token: 'comment', regex: '//.*' },
      { token: 'number', regex: '\\b\\d+\\.?\\d*\\b' },
    ],
  },
  json: {
    patterns: [
      { token: 'keyword', regex: '\\b(true|false|null)\\b' },
      { token: 'string', regex: '"(?:[^"\\\\]|\\\\.)*"' },
      { token: 'number', regex: '\\b\\d+\\.?\\d*\\b' },
    ],
  },
  python: {
    patterns: [
      { token: 'keyword', regex: '\\b(def|class|return|if|elif|else|for|while|import|from|as|try|except|raise|with|yield|lambda|pass|break|continue|and|or|not|in|is|None|True|False)\\b' },
      { token: 'string', regex: '(["\'])(?:(?=(\\\\?))\\2.)*?\\1' },
      { token: 'comment', regex: '#.*' },
      { token: 'number', regex: '\\b\\d+\\.?\\d*\\b' },
    ],
  },
};

const TOKEN_COLORS: Record<string, string> = {
  keyword: 'text-purple-400',
  string: 'text-green-400',
  comment: 'text-gray-500 italic',
  number: 'text-orange-400',
};

function tokenizeLine(line: string, language: string): React.ReactNode[] {
  const syntax = (LANGUAGE_SYNTAX[language] ?? LANGUAGE_SYNTAX.javascript)!;
  const tokens: React.ReactNode[] = [];
  let remaining = line;
  let key = 0;

  while (remaining.length > 0) {
    let earliest: { index: number; length: number; token: string; match: string } | null = null;

    for (const pattern of syntax.patterns) {
      const regex = new RegExp(pattern.regex);
      const match = regex.exec(remaining);
      if (match && (earliest === null || match.index < earliest.index)) {
        earliest = { index: match.index, length: match[0].length, token: pattern.token, match: match[0] };
      }
    }

    if (earliest && earliest.index === 0) {
      tokens.push(
        <span key={key++} className={TOKEN_COLORS[earliest.token]}>{earliest.match}</span>
      );
      remaining = remaining.slice(earliest.length);
    } else if (earliest) {
      tokens.push(
        <span key={key++} className="text-[var(--text-primary)]">{remaining.slice(0, earliest.index)}</span>
      );
      remaining = remaining.slice(earliest.index);
    } else {
      tokens.push(
        <span key={key++} className="text-[var(--text-primary)]">{remaining}</span>
      );
      remaining = '';
    }
  }

  return tokens;
}

function CodeEditor({
  value,
  defaultValue = '',
  onChange,
  language = 'javascript',
  theme = 'vs-dark',
  readOnly = false,
  minimap = false,
  lineNumbers = 'on',
  wordWrap = 'on',
  autoComplete = true,
  height = '300px',
  placeholder = '',
  errors = [],
  className,
  ariaLabel = 'Code editor',
  onMount,
}: CodeEditorProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const [focused, setFocused] = useState(false);
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const isControlled = value !== undefined;
  const currentValue = isControlled ? value : internalValue;

  useEffect(() => {
    onMount?.();
  }, [onMount]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    if (!isControlled) setInternalValue(newValue);
    onChange?.(newValue);
  }, [isControlled, onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = currentValue.substring(0, start) + '  ' + currentValue.substring(end);
      if (!isControlled) setInternalValue(newValue);
      onChange?.(newValue);
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      });
    }
    if (autoComplete && e.key === '(') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const newValue = currentValue.substring(0, start) + '()' + currentValue.substring(textarea.selectionEnd);
      if (!isControlled) setInternalValue(newValue);
      onChange?.(newValue);
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1;
      });
    }
    if (autoComplete && e.key === '{') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const newValue = currentValue.substring(0, start) + '{}' + currentValue.substring(textarea.selectionEnd);
      if (!isControlled) setInternalValue(newValue);
      onChange?.(newValue);
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1;
      });
    }
    if (autoComplete && e.key === '[') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const newValue = currentValue.substring(0, start) + '[]' + currentValue.substring(textarea.selectionEnd);
      if (!isControlled) setInternalValue(newValue);
      onChange?.(newValue);
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1;
      });
    }
    if (autoComplete && e.key === '"') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const newValue = currentValue.substring(0, start) + '""' + currentValue.substring(textarea.selectionEnd);
      if (!isControlled) setInternalValue(newValue);
      onChange?.(newValue);
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1;
      });
    }
  }, [autoComplete, currentValue, isControlled, onChange]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLTextAreaElement>) => {
    if (preRef.current) {
      preRef.current.scrollTop = e.currentTarget.scrollTop;
      preRef.current.scrollLeft = e.currentTarget.scrollLeft;
    }
  }, []);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(currentValue);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [currentValue]);

  const lines = currentValue.split('\n');
  const errorLines = new Set(errors.filter(e => e.severity === 'error').map(e => e.line));
  const warningLines = new Set(errors.filter(e => e.severity === 'warning').map(e => e.line));

  return (
    <div
      className={cn(
        'relative border rounded-xl overflow-hidden font-mono text-sm',
        theme === 'vs-dark' ? 'bg-[#1e1e2e] border-[var(--border-subtle)]' : 'bg-white border-gray-300',
        focused && 'ring-2 ring-[var(--accent)]',
        className
      )}
      style={{ height }}
    >
      <div className={cn(
        'flex items-center justify-between px-3 py-2 border-b',
        theme === 'vs-dark' ? 'bg-[#181825] border-[var(--border-subtle)]' : 'bg-gray-50 border-gray-200'
      )}>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs text-[var(--text-muted)] ml-2">{language}</span>
        </div>
        <div className="flex items-center gap-2">
          {errors.length > 0 && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <AlertCircle className="w-3.5 h-3.5" />
              {errors.filter(e => e.severity === 'error').length}
            </span>
          )}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md hover:bg-[var(--surface-bg-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Copy code"
          >
            {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="relative w-full h-[calc(100%-40px)] overflow-hidden">
        <pre
          ref={preRef}
          className="absolute inset-0 p-4 overflow-auto pointer-events-none whitespace-pre"
          style={{ wordWrap: wordWrap === 'on' ? 'break-word' : 'normal' }}
        >
          {lines.map((line, i) => (
            <div key={i} className="flex">
              {lineNumbers !== 'off' && (
                <span className={cn(
                  'inline-block text-right pr-4 select-none min-w-[3rem]',
                  errorLines.has(i + 1) ? 'text-red-400' : warningLines.has(i + 1) ? 'text-yellow-400' : 'text-[var(--text-muted)]'
                )}>
                  {lineNumbers === 'relative' ? Math.abs(i - (textareaRef.current ? 0 : 0)) || i + 1 : i + 1}
                </span>
              )}
              <span className={cn(
                errorLines.has(i + 1) && 'bg-red-500/10 w-full',
                warningLines.has(i + 1) && 'bg-yellow-500/10 w-full'
              )}>
                {line.length > 0 ? tokenizeLine(line, language) : '\u200B'}
              </span>
            </div>
          ))}
        </pre>
        <textarea
          ref={textareaRef}
          value={currentValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onScroll={handleScroll}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          readOnly={readOnly}
          placeholder={placeholder}
          aria-label={ariaLabel}
          spellCheck={false}
          className="absolute inset-0 w-full h-full p-4 bg-transparent text-transparent caret-[var(--text-primary)] resize-none outline-none whitespace-pre"
          style={{ wordWrap: wordWrap === 'on' ? 'break-word' : 'normal', caretColor: 'var(--text-primary)' }}
        />
      </div>

      {errors.length > 0 && (
        <div className={cn(
          'max-h-24 overflow-y-auto border-t text-xs',
          theme === 'vs-dark' ? 'bg-[#181825] border-[var(--border-subtle)]' : 'bg-gray-50 border-gray-200'
        )}>
          {errors.map((error, i) => (
            <div key={i} className={cn(
              'flex items-center gap-2 px-3 py-1.5',
              error.severity === 'error' && 'text-red-400',
              error.severity === 'warning' && 'text-yellow-400',
              error.severity === 'info' && 'text-blue-400'
            )}>
              {error.severity === 'error' ? <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> : null}
              <span className="text-[var(--text-muted)]">Ln {error.line}</span>
              <span>{error.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export { CodeEditor };
