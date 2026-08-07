import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../lib/utils';
import { Copy, Check, List } from 'lucide-react';

export interface TocItem {
  id: string;
  level: number;
  text: string;
}

export interface MarkdownRendererProps {
  content: string;
  className?: string;
  showToc?: boolean;
  tocTitle?: string;
  onTocClick?: (id: string) => void;
  darkMode?: boolean;
  codeTheme?: 'dark' | 'light';
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
}

function CodeBlock({ children, className: codeClassName }: { children?: React.ReactNode; className?: string | undefined }) {
  const [copied, setCopied] = React.useState(false);
  const match = /language-(\w+)/.exec(codeClassName || '');
  const language = match ? match[1] : undefined;
  const codeText = String(children).replace(/\n$/, '');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group/code my-4">
      {language && (
        <div className="absolute top-3 right-12 z-10">
          <span className="text-[10px] text-[var(--text-muted)] bg-[var(--surface-bg)]/5 px-2 py-0.5 rounded-md backdrop-blur-sm border border-white/5">
            {language}
          </span>
        </div>
      )}
      <button
        onClick={handleCopy}
        className="absolute top-3 right-3 z-10 p-1.5 rounded-lg bg-[var(--surface-bg)]/5 text-[var(--text-muted)] hover:bg-[var(--surface-bg)] hover:text-[var(--text-primary)] backdrop-blur-sm border border-white/5 opacity-0 group-hover/code:opacity-100 transition-all"
        aria-label="Copy code"
      >
        {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
      </button>
      <pre className="p-4 pt-10 rounded-xl overflow-x-auto bg-[var(--surface-bg-subtle)] border border-[var(--border-subtle)] text-sm">
        <code className={cn('text-sm', codeClassName)}>{children}</code>
      </pre>
    </div>
  );
}

function MarkdownRenderer({
  content,
  className,
  showToc = false,
  tocTitle = 'Table of Contents',
  onTocClick,
  darkMode = true,
}: MarkdownRendererProps) {
  const toc = useMemo(() => {
    const headings = content.match(/^#{1,6}\s+.+$/gm) || [];
    return headings.map((heading, index) => {
      const level = heading.match(/^#+/)?.[0].length || 1;
      const text = heading.replace(/^#+\s+/, '');
      const id = `heading-${slugify(text)}-${index}`;
      return { id, level, text };
    });
  }, [content]);

  return (
    <div className={cn('w-full', showToc && 'flex gap-6')}>
      {showToc && toc.length > 0 && (
        <nav className="w-56 flex-shrink-0 sticky top-4 self-start" aria-label="Table of contents">
          <div className="border border-[var(--border-subtle)] rounded-xl bg-[var(--surface-bg)] p-4">
            <div className="flex items-center gap-2 mb-3">
              <List className="w-4 h-4 text-[var(--accent)]" />
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">{tocTitle}</h4>
            </div>
            <ul className="space-y-1.5">
              {toc.map(item => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    onClick={(e) => { e.preventDefault(); onTocClick?.(item.id); }}
                    className={cn(
                      'block text-xs hover:text-[var(--accent)] transition-colors truncate',
                      item.level === 1 && 'text-[var(--text-secondary)] font-medium',
                      item.level === 2 && 'text-[var(--text-muted)] pl-3',
                      item.level >= 3 && 'text-[var(--text-muted)] pl-6'
                    )}
                  >
                    {item.text}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      )}
      <div className={cn('markdown-body flex-1 min-w-0 text-sm leading-relaxed', className)}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1({ children, ...props }) {
              const text = String(children);
              const id = `heading-${slugify(text)}-h1`;
              return <h1 id={id} className="text-2xl font-bold text-[var(--text-primary)] mt-8 mb-4 tracking-tight" {...props}>{children}</h1>;
            },
            h2({ children, ...props }) {
              const text = String(children);
              const id = `heading-${slugify(text)}-h2`;
              return <h2 id={id} className="text-xl font-semibold text-[var(--text-primary)] mt-6 mb-3 tracking-tight" {...props}>{children}</h2>;
            },
            h3({ children, ...props }) {
              const text = String(children);
              const id = `heading-${slugify(text)}-h3`;
              return <h3 id={id} className="text-lg font-semibold text-[var(--text-primary)] mt-5 mb-2" {...props}>{children}</h3>;
            },
            h4({ children, ...props }) {
              const text = String(children);
              const id = `heading-${slugify(text)}-h4`;
              return <h4 id={id} className="text-base font-semibold text-[var(--text-primary)] mt-4 mb-2" {...props}>{children}</h4>;
            },
            p({ children }) {
              return <p className="my-3 text-[var(--text-secondary)] leading-relaxed">{children}</p>;
            },
            a({ href, children }) {
              return (
                <a href={href} className="text-[var(--accent)] hover:underline underline-offset-4 transition-colors" target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              );
            },
            code({ className: codeClassName, children }) {
              const match = /language-(\w+)/.exec(codeClassName || '');
              const inline = !match && !codeClassName;
              return inline ? (
                <code className="px-1.5 py-0.5 rounded-md text-xs bg-[var(--accent)]/10 text-[var(--accent)] font-mono">{children}</code>
              ) : (
                <CodeBlock className={codeClassName}>{children}</CodeBlock>
              );
            },
            pre({ children }) {
              return <>{children}</>;
            },
            ul({ children }) {
              return <ul className="list-disc list-inside my-3 space-y-1.5 text-[var(--text-secondary)] marker:text-[var(--accent)]">{children}</ul>;
            },
            ol({ children }) {
              return <ol className="list-decimal list-inside my-3 space-y-1.5 text-[var(--text-secondary)] marker:text-[var(--accent)]">{children}</ol>;
            },
            li({ children }) {
              return <li className="text-[var(--text-secondary)]">{children}</li>;
            },
            blockquote({ children }) {
              return (
                <blockquote className="border-l-2 border-[var(--accent)]/40 pl-4 py-2 my-4 bg-[var(--accent)]/[0.03] rounded-r-xl text-[var(--text-secondary)] italic">
                  {children}
                </blockquote>
              );
            },
            hr() {
              return <hr className="border-[var(--border-subtle)] my-6" />;
            },
            table({ children }) {
              return (
                <div className="overflow-x-auto my-4 rounded-xl border border-[var(--border-subtle)]">
                  <table className="min-w-full divide-y divide-[var(--border-subtle)] text-sm">{children}</table>
                </div>
              );
            },
            th({ children }) {
              return (
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-[var(--text-secondary)] bg-[var(--surface-bg-subtle)] uppercase tracking-wider border-b border-[var(--border-subtle)]">
                  {children}
                </th>
              );
            },
            td({ children }) {
              return <td className="px-4 py-2.5 text-sm text-[var(--text-secondary)] border-t border-[var(--border-subtle)]">{children}</td>;
            },
            img({ src, alt }) {
              return <img src={src} alt={alt || ''} className="max-w-full max-h-80 rounded-xl my-3 object-contain" />;
            },
            strong({ children }) {
              return <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>;
            },
            em({ children }) {
              return <em className="italic">{children}</em>;
            },
            del({ children }) {
              return <del className="line-through text-[var(--text-muted)]">{children}</del>;
            },
            input({ type, checked, ...props }) {
              if (type === 'checkbox') {
                return <input type="checkbox" checked={checked} readOnly className="mr-2 rounded" {...props} />;
              }
              return <input type={type} {...props} />;
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

export { MarkdownRenderer };
