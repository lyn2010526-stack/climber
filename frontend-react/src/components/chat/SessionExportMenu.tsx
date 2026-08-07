import { useState, useRef, useEffect } from 'react';
import { Download, FileText, Image, Code2, Share2, Check, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
}

interface SessionExportMenuProps {
  messages: Message[];
  sessionTitle?: string;
  className?: string;
}

type ExportFormat = 'markdown' | 'json' | 'text' | 'copy';

const formatConfig = {
  markdown: { icon: FileText, label: 'Markdown', desc: '格式化文档' },
  json: { icon: Code2, label: 'JSON', desc: '结构化数据' },
  text: { icon: FileText, label: '纯文本', desc: '简单可读' },
  copy: { icon: Copy, label: '复制全部', desc: '复制到剪贴板' },
};

export function SessionExportMenu({ messages, sessionTitle = '对话', className }: SessionExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const generateMarkdown = (): string => {
    const lines = [`# ${sessionTitle}`, ''];
    messages.forEach((msg) => {
      const role = msg.role === 'user' ? '**用户**' : msg.role === 'assistant' ? '**AI**' : '**系统**';
      lines.push(`### ${role}`);
      lines.push(msg.content);
      lines.push('');
    });
    return lines.join('\n');
  };

  const generateJSON = (): string => {
    return JSON.stringify(
      { title: sessionTitle, exportedAt: new Date().toISOString(), messages },
      null,
      2,
    );
  };

  const generateText = (): string => {
    const lines = [`会话: ${sessionTitle}`, `导出时间: ${new Date().toLocaleString()}`, ''];
    messages.forEach((msg) => {
      const role = msg.role === 'user' ? '用户' : msg.role === 'assistant' ? 'AI' : '系统';
      lines.push(`[${role}] ${msg.content}`);
      lines.push('');
    });
    return lines.join('\n');
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExport = (format: ExportFormat) => {
    const safeName = sessionTitle.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_');

    switch (format) {
      case 'markdown':
        downloadFile(generateMarkdown(), `${safeName}.md`, 'text/markdown');
        break;
      case 'json':
        downloadFile(generateJSON(), `${safeName}.json`, 'application/json');
        break;
      case 'text':
        downloadFile(generateText(), `${safeName}.txt`, 'text/plain');
        break;
      case 'copy':
        navigator.clipboard.writeText(generateMarkdown());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        break;
    }

    if (format !== 'copy') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs',
          'border transition-all duration-200',
          'hover:bg-[var(--color-bg-surface-3)]',
          isOpen
            ? 'bg-[var(--color-bg-surface-3)] border-[var(--color-border-default)]'
            : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)]',
        )}
        title="导出对话"
      >
        <Download size={12} className="text-[var(--color-text-muted)]" />
        <span className="text-[var(--color-text-muted)]">导出</span>
      </button>

      {isOpen && (
        <div
          className="absolute top-full right-0 mt-2 w-56 rounded-2xl border overflow-hidden z-50 fade-enter"
          style={{
            backgroundColor: 'var(--color-bg-surface-2)',
            borderColor: 'var(--color-border-default)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          }}
        >
          <div className="p-1.5">
            {(Object.keys(formatConfig) as ExportFormat[]).map((format) => {
              const config = formatConfig[format];
              const Icon = config.icon;
              return (
                <button
                  key={format}
                  onClick={() => handleExport(format)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left transition-colors hover:bg-[var(--color-bg-surface-3)]"
                >
                  <Icon size={13} className="text-[var(--color-accent)]" />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-[var(--color-text-primary)]">
                      {config.label}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-muted)]">{config.desc}</div>
                  </div>
                  {format === 'copy' && copied && (
                    <Check size={12} className="text-[var(--color-success)]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
