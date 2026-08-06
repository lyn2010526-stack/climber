import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../lib/utils';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  enableStream?: boolean;
}

/* Reference: Dify `markdown/markdown-utils.ts` */
function preprocessLaTeX(content: string): string {
  if (typeof content !== 'string') return content;
  const codeBlockRegex = /```[\s\S]*?```/g;
  const codeBlocks = content.match(codeBlockRegex) || [];
  const escapeReplacement = (str: string) => str.replace(/\$/g, '_TMP_REPLACE_DOLLAR_');
  let processedContent = content.replace(codeBlockRegex, 'CODE_BLOCK_PLACEHOLDER');

  processedContent = processedContent
    .replace(/\\\[(.*?)\\\]/g, (_, equation) => `$$${equation}$$`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, equation) => `$$${equation}$$`)
    .replace(/\\\((.*?)\\\)/g, (_, equation) => `$$${equation}$$`)
    .replace(/(^|[^\\])\$(.+?)\$/g, (_, prefix, equation) => `${prefix}$${equation}$`);

  codeBlocks.forEach((block) => {
    processedContent = processedContent.replace('CODE_BLOCK_PLACEHOLDER', escapeReplacement(block));
  });

  return processedContent.replace(/_TMP_REPLACE_DOLLAR_/g, '$');
}

function preprocessThinkTag(content: string): string {
  return content
    .replace(/(<think>\s*)+/g, '<details data-think=true>\n')
    .replace(/(\s*<\/think>)+/g, '\n[ENDTHINKFLAG]</details>')
    .replace(/(<\/details>)(?![^\S\r\n]*[\r\n])(?![^\S\r\n]*$)/g, '$1\n');
}

function preprocessContent(content: string): string {
  return preprocessLaTeX(preprocessThinkTag(content));
}

/* Reference: Dify `customUrlTransform` */
function customUrlTransform(uri: string): string | undefined {
  if (uri.startsWith('#')) return uri;
  if (uri.startsWith('//')) return uri;

  const colonIndex = uri.indexOf(':');
  if (colonIndex === -1) return uri;

  const slashIndex = uri.indexOf('/');
  const questionMarkIndex = uri.indexOf('?');
  const hashIndex = uri.indexOf('#');

  if (
    (slashIndex !== -1 && colonIndex > slashIndex) ||
    (questionMarkIndex !== -1 && colonIndex > questionMarkIndex) ||
    (hashIndex !== -1 && colonIndex > hashIndex)
  ) {
    return uri;
  }

  const scheme = uri.substring(0, colonIndex + 1).toLowerCase();
  const PERMITTED_SCHEME_REGEX = /^(https?|ircs?|mailto|xmpp|abbr):$/i;
  if (PERMITTED_SCHEME_REGEX.test(scheme)) return uri;

  return undefined;
}

/* Reference: Lobe UI `Highlighter/SyntaxHighlighter/StreamRenderer.tsx` - token rendering + Vercel / Linear */
function CodeBlock({ children, className: codeClassName }: { children?: React.ReactNode; className?: string | undefined }) {
  const [copied, setCopied] = React.useState(false);
  const [showLineNumbers, setShowLineNumbers] = React.useState(false);
  const match = /language-(\w+)/.exec(codeClassName || '');
  const language = match ? match[1] : undefined;
  const codeText = String(children).replace(/\n$/, '');
  const lines = codeText.split('\n');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group/code my-3 message-enter">
      {language && (
        <div className="absolute top-2 right-10 z-10 flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-muted)] bg-white/5 px-2 py-0.5 rounded-md backdrop-blur-sm border border-white/5">
            {language}
          </span>
        </div>
      )}
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1 opacity-0 group-hover/code:opacity-100 transition-all duration-200">
        <button
          onClick={() => setShowLineNumbers(!showLineNumbers)}
          className="p-1.5 rounded-lg bg-white/5 text-[var(--color-text-muted)] hover:bg-white/10 hover:text-white backdrop-blur-sm border border-white/5 transition-all duration-150"
          title="行号"
        >
          <span className="text-[10px] font-mono">#</span>
        </button>
        <button
          onClick={handleCopy}
          className="p-1.5 rounded-lg bg-white/5 text-[var(--color-text-muted)] hover:bg-white/10 hover:text-white backdrop-blur-sm border border-white/5 transition-all duration-150"
          title="复制代码"
        >
          {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
        </button>
      </div>
      <pre className="code-block text-xs p-4 pt-10 rounded-xl overflow-x-auto" style={{
        border: '1px solid var(--color-border-subtle)',
        boxShadow: '0 0 0 1px rgba(94,106,210,0.05)',
      }}>
        <code className={cn('text-xs', codeClassName)}>
          {showLineNumbers ? (
            <table className="w-full border-collapse">
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="animate-in fade-in duration-300" style={{ animationDelay: `${i * 15}ms` }}>
                    <td className="text-right pr-4 text-[var(--color-text-muted)] select-none border-r border-white/10">{i + 1}</td>
                    <td className="pl-4">{line || ' '}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            children
          )}
        </code>
      </pre>
    </div>
  );
}

function InlineCode({ children }: { children?: React.ReactNode }) {
  return (
    <code className="code-block text-xs px-1.5 py-0.5 rounded-md" style={{
      color: '#f87171',
      backgroundColor: 'rgba(248,113,113,0.08)',
      border: '1px solid rgba(248,113,113,0.15)',
    }}>{children}</code>
  );
}

/* Reference: Dify `markdown-blocks/thinking-details.tsx` + Vercel */
function ThinkDetails({ children, open: defaultOpen }: { children?: React.ReactNode; open?: boolean | undefined }) {
  return (
    <details open={defaultOpen} className="group my-3 rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden message-enter" style={{
      boxShadow: '0 0 0 1px rgba(94,106,210,0.05)',
    }}>
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-xs font-medium text-[#5E6AD2] select-none hover:bg-white/[0.03] transition-colors">
        <span className="transition-transform duration-300 group-open:rotate-90 text-[10px]">▶</span>
        <span>Thinking</span>
      </summary>
      <div className="border-t border-white/[0.06] px-4 py-3">
        <div className="text-sm text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap font-mono text-xs">
          {children}
        </div>
      </div>
    </details>
  );
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className }) => {
  const processedContent = preprocessContent(content);

  return (
    <div className={cn('markdown-body prose prose-invert max-w-none text-sm leading-relaxed stagger-children', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={customUrlTransform}
        components={{
          details({ children, open }) {
            if ((children as any)?.props?.['data-think']) {
              return <ThinkDetails open={open}>{children}</ThinkDetails>;
            }
            return <details open={open}>{children}</details>;
          },
          img({ src, alt }) {
            if (!src) return null;
            const srcStr = String(src);
            if (srcStr.startsWith('http') || srcStr.startsWith('/')) {
              return <img src={srcStr} alt={alt || ''} className="max-w-full max-h-64 rounded-xl my-2 cursor-pointer hover:opacity-90 transition-opacity" />;
            }
            return null;
          },
          code({ node: _node, className: codeClassName, children }) {
            const match = /language-(\w+)/.exec(codeClassName || '');
            const inline = !match && !codeClassName;
            return inline ? (
              <InlineCode>{children}</InlineCode>
            ) : (
              <CodeBlock className={codeClassName}>{children}</CodeBlock>
            );
          },
          pre({ children }) {
            return <div className="my-3">{children}</div>;
          },
          a({ href, children }) {
            return (
              <a href={href} className="text-[#5E6AD2] hover:underline underline-offset-4 decoration-[#5E6AD2]/30 hover:decoration-[#5E6AD2] transition-all duration-200" target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-4 rounded-xl border border-white/[0.08]" style={{
                boxShadow: '0 0 0 1px rgba(255,255,255,0.03)',
              }}>
                <table className="min-w-full divide-y divide-white/[0.06] text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-[var(--color-text-secondary)] bg-white/[0.04] uppercase tracking-wider" style={{
                borderBottom: '1px solid var(--color-border-subtle)',
              }}>
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-4 py-2.5 text-xs text-[var(--color-text-secondary)] border-t border-white/[0.04]">
                {children}
              </td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-2 border-[#5E6AD2]/40 pl-4 py-2 my-4 bg-[#5E6AD2]/[0.03] rounded-r-xl text-[var(--color-text-secondary)] italic">
                {children}
              </blockquote>
            );
          },
          ul({ children }) {
            return <ul className="list-disc list-inside my-3 space-y-1.5 text-[var(--color-text-secondary)] marker:text-[#5E6AD2]">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside my-3 space-y-1.5 text-[var(--color-text-secondary)] marker:text-[#5E6AD2]">{children}</ol>;
          },
          h1({ children }) {
            return <h1 className="text-xl font-bold text-white mt-6 mb-3 tracking-tight">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-lg font-semibold text-white mt-5 mb-2 tracking-tight">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold text-white mt-4 mb-2 tracking-tight">{children}</h3>;
          },
          p({ children }) {
            return <p className="my-2.5 text-[var(--color-text-secondary)] leading-relaxed">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-white">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic text-[var(--color-text-secondary)]">{children}</em>;
          },
          hr() {
            return <hr className="border-white/[0.08] my-6" />;
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
