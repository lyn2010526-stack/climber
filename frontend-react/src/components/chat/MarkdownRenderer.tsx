import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../i18n';
import { Copy, Check, ChevronRight } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  enableStream?: boolean;
  /** 长回复时展示标题目录。默认在标题数达到阈值后自动开启。 */
  showToc?: boolean;
}

interface TocEntry {
  level: number;
  text: string;
  id: string;
}

const TOC_MIN_HEADINGS = 3;
const HEADING_RE = /^(#{2,4})\s+(.+?)\s*#*$/gm;

function slugify(text: string, index: number): string {
  const base = text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .trim()
    .replace(/\s+/g, '-');
  return `heading-${base || 'section'}-${index}`;
}

/** 从已预处理的内容里抽取 2-4 级标题，忽略代码块内的 `#` 注释。 */
function extractHeadings(content: string): TocEntry[] {
  const withoutCode = content.replace(/```[\s\S]*?```/g, '');
  const entries: TocEntry[] = [];
  let match: RegExpExecArray | null;
  let index = 0;
  HEADING_RE.lastIndex = 0;
  while ((match = HEADING_RE.exec(withoutCode)) !== null) {
    const text = (match[2] ?? '').trim();
    if (text) {
      entries.push({ level: match[1]!.length, text, id: slugify(text, index) });
      index += 1;
    }
  }
  return entries;
}

/** 把标题子节点还原为纯文本，用于生成与目录一致的锚点 id。 */
function nodeText(children: React.ReactNode): string {
  if (typeof children === 'string' || typeof children === 'number') return String(children);
  if (Array.isArray(children)) return children.map(nodeText).join('');
  if (React.isValidElement(children)) {
    return nodeText((children.props as { children?: React.ReactNode }).children);
  }
  return '';
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

/* Reference: assistant-ui `elements/markdown-text.tsx` `aui-code-header-root` */
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
    <div className="my-3">
      <div className="mb-1 flex items-center justify-between gap-2 text-xs text-[var(--color-text-muted)]">
        <span className="font-mono lowercase">{language ?? ''}</span>
        <span className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setShowLineNumbers(open => !open)}
            aria-pressed={showLineNumbers}
            className="rounded-md px-1.5 py-0.5 font-mono transition-colors duration-150 hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none"
            title="行号"
          >
            #
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md p-1 transition-colors duration-150 hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none"
            title="复制代码"
          >
            {copied ? <Check size={12} aria-hidden="true" className="text-[var(--color-success)]" /> : <Copy size={12} aria-hidden="true" />}
          </button>
        </span>
      </div>
      <pre className="code-block text-xs">
        <code className={cn('text-xs', codeClassName)}>
          {showLineNumbers ? (
            <table className="w-full border-collapse">
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i}>
                    <td className="border-r border-[var(--color-border-default)] pr-4 text-right text-[var(--color-text-muted)] select-none">{i + 1}</td>
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

/* Reference: assistant-ui `aui-md-code-inline` — a neutral chip, not a highlight. */
function InlineCode({ children }: { children?: React.ReactNode }) {
  return (
    <code className="rounded-[4px] bg-[var(--color-bg-surface-3)] px-1 py-0.5 font-mono text-[0.9em] text-[var(--color-text-primary)]">
      {children}
    </code>
  );
}

/* Reference: Dify `markdown-blocks/thinking-details.tsx` */
function ThinkDetails({ children, open: defaultOpen }: { children?: React.ReactNode; open?: boolean | undefined }) {
  const { t } = useTranslation();
  return (
    <details open={defaultOpen} className="group my-2 overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs text-[var(--color-text-muted)] select-none transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] motion-reduce:transition-none">
        <ChevronRight size={12} aria-hidden="true" className="shrink-0 transition-transform duration-150 group-open:rotate-90 motion-reduce:transition-none" />
        <span>{t('common.thinking')}</span>
      </summary>
      <div className="border-t border-[var(--color-border-subtle)] px-3 py-2">
        <div className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-[var(--color-text-secondary)]">
          {children}
        </div>
      </div>
    </details>
  );
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
  showToc,
}) => {
  const { t } = useTranslation();
  const processedContent = preprocessContent(content);
  const headings = useMemo(() => extractHeadings(processedContent), [processedContent]);
  const tocVisible = showToc ?? headings.length >= TOC_MIN_HEADINGS;

  // 渲染期的标题序号必须与 extractHeadings 的产出顺序一致，锚点才对得上目录。
  let headingCursor = 0;
  const headingId = (children: React.ReactNode) => {
    const entry = headings[headingCursor];
    headingCursor += 1;
    const text = entry ? entry.text : nodeText(children).trim();
    return entry ? entry.id : slugify(text, headingCursor - 1);
  };

  return (
    <div className={cn('max-w-none text-sm leading-relaxed', className)}>
      {tocVisible && headings.length > 0 && (
        <nav
          aria-label={t('chat.table_of_contents')}
          className="mb-3 border-l-2 border-[var(--color-border-default)] pl-3"
        >
          <ol className="space-y-0.5">
            {headings.map(heading => (
              <li key={heading.id} style={{ paddingLeft: `${(heading.level - 2) * 12}px` }}>
                <a
                  href={`#${heading.id}`}
                  className="block truncate text-xs text-[var(--color-text-muted)] transition-colors duration-150 hover:text-[var(--color-text-primary)] motion-reduce:transition-none"
                >
                  {heading.text}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      )}
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
            return <div>{children}</div>;
          },
          a({ href, children }) {
            return (
              <a href={href} className="text-[var(--color-accent-foreground)] underline underline-offset-4 decoration-[var(--color-border-accent)] hover:decoration-current transition-colors" target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
                <table className="min-w-full divide-y divide-[var(--color-border-subtle)] text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface-2)]" style={{
                borderBottom: '1px solid var(--color-border-subtle)',
              }}>
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-3 py-2 text-xs text-[var(--color-text-secondary)] border-t border-[var(--color-border-subtle)]">
                {children}
              </td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-3 border-l-2 border-[var(--color-border-default)] pl-3 text-[var(--color-text-secondary)]">
                {children}
              </blockquote>
            );
          },
          ul({ children }) {
            return <ul className="my-2 list-disc space-y-1 pl-5 marker:text-[var(--color-text-muted)]">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-2 list-decimal space-y-1 pl-5 marker:text-[var(--color-text-muted)]">{children}</ol>;
          },
          h1({ children }) {
            return <h1 className="mt-5 mb-2 text-lg font-semibold text-[var(--color-text-primary)]">{children}</h1>;
          },
          h2({ children }) {
            return <h2 id={headingId(children)} className="mt-5 mb-2 scroll-mt-4 text-base font-semibold text-[var(--color-text-primary)]">{children}</h2>;
          },
          h3({ children }) {
            return <h3 id={headingId(children)} className="mt-4 mb-1.5 scroll-mt-4 text-sm font-semibold text-[var(--color-text-primary)]">{children}</h3>;
          },
          h4({ children }) {
            return <h4 id={headingId(children)} className="mt-3 mb-1.5 scroll-mt-4 text-sm font-semibold text-[var(--color-text-primary)]">{children}</h4>;
          },
          p({ children }) {
            return <p className="my-2 leading-relaxed text-[var(--color-text-primary)]">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-[var(--color-text-primary)]">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic text-[var(--color-text-secondary)]">{children}</em>;
          },
          hr() {
            return <hr className="my-4 border-[var(--color-border-subtle)]" />;
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
