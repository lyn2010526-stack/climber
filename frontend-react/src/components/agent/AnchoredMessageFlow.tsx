import { memo, useId, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatTime } from '../../i18n/utils';
import { ToolCodeBlock } from './ToolDisclosure';
import { AgentToolCard, getAgentToolIcon, type AgentToolStatus } from './AgentToolCard';
import { ThoughtChainPanel, type ThoughtChainStep, type ThoughtStepStatus } from './ThoughtChainPanel';
import { DiffCell } from './DiffCell';
import { ThinkingBubble } from './ThinkingBubble';
import { useAnchoredStore } from '../../store/anchored';
import { StatusDot } from '../chat/StatusDot';
import { ChatStreamSkeleton } from '../chat/ChatStreamStates';
import type { ToolCall } from '../../useChat';
import type { Message } from '../../useChat';

/**
 * 五种消息样式（严格区分，样式与顺序不可混用）：
 *   1. 用户输入气泡 —— 靠右，主色浅淡背景。
 *   2. Agent 答复 —— 靠左，正文直接可见，公开推理摘要默认折叠。宿主在
 *      ThinkingBubble.tsx：ReasoningPanel 承载推理正文，MessageActions 承载
 *      hover / focus 才显形的操作条。
 *   3. 工具调用卡片 —— 工具名 + 状态标签，参数与日志通过详情展开。卡在审批上的
 *      调用改用 AgentToolCard（唯一带审批行的工具面），其余留在 Codex 卡片上。
 *   4. 工具结果块 —— 默认折叠（仅状态标签 + 展开按钮），展开后最大高 240px。
 *   5. 代码差异块 —— 左右分栏，左删除红底，右新增绿底，行号对齐。
 * 一个 tool turn 里的多步调用额外用 ThoughtChainPanel 串成一条链路概览。
 * 对齐规则：用户消息靠右，Agent 消息靠左。时间戳在每条消息下方居中，小字辅助色。
 */

type ToolStatus = 'running' | 'success' | 'error' | undefined;

/** Codex 风格会话头常量：产品名与版本号。 */
export const CODEX_PRODUCT_NAME = 'Climber';
export const CODEX_VERSION = 'v1';
export const CODEX_PROMPT_GLYPH = '>_';
export const CODEX_USER_GLYPH = '›';
export const CODEX_MAX_OUTPUT_HEAD_LINES = 5;

/**
 * 计算 Codex 输出省略行文本：截断后按需追加 `… +{N} lines (⌃t to view transcript)`。
 * 仅在原始行数超过上限时返回省略文本，否则返回 null。
 */
export function outputEllipsisText(output: string, headLines = CODEX_MAX_OUTPUT_HEAD_LINES): string | null {
  const lines = output.split('\n');
  if (lines.length <= headLines) return null;
  const dropped = lines.length - headLines;
  return `… +${dropped} ${dropped === 1 ? 'line' : 'lines'} (⌃t to view transcript)`;
}

/** 判断工具输出是否是 unified diff，命中即按代码差异块渲染。 */
export function looksLikeDiff(text: string): boolean {
  return /^\s*diff --git /m.test(text) || /^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@/m.test(text);
}

interface DiffSplitLine {
  left: { number: number | null; text: string } | null;
  right: { number: number | null; text: string } | null;
}

/** 把 unified diff 文本拆成左右两栏（左删除、右新增），行号对齐。 */
export function splitDiffRows(text: string): DiffSplitLine[] {
  const rows: DiffSplitLine[] = [];
  let oldN = 0;
  let newN = 0;
  for (const line of text.split('\n')) {
    if (line.startsWith('diff --git') || line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('index ')) {
      continue;
    }
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match?.[1] && match?.[2]) {
        oldN = parseInt(match[1], 10);
        newN = parseInt(match[2], 10);
      }
      rows.push({
        left: { number: null, text: line },
        right: { number: null, text: '' },
      });
      continue;
    }
    const marker = line[0];
    const content = line.slice(1);
    if (marker === '+') {
      rows.push({ left: null, right: { number: newN++, text: content } });
    } else if (marker === '-') {
      rows.push({ left: { number: oldN++, text: content }, right: null });
    } else if (marker === ' ' || marker === '') {
      if (line === '' && rows.length > 0) continue;
      rows.push({
        left: { number: oldN++, text: content },
        right: { number: newN++, text: content },
      });
    }
  }
  return rows;
}

/** 代码差异块：左右分栏，左删除红底，右新增绿底，行号对齐。 */
export function DiffBlock({ diffText }: { diffText: string }) {
  const { t } = useI18n();
  const rows = useMemo(() => splitDiffRows(diffText), [diffText]);
  return (
    <div
      data-testid="anchored-diff-block"
      role="table"
      aria-label={t('anchored.messages.diff_block')}
      className="mt-[var(--space-2)] overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] font-mono text-[length:var(--text-2xs)] leading-[var(--leading-normal)]"
    >
      <div role="row" className="grid grid-cols-2 divide-x divide-[var(--color-border-subtle)] border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-center text-[var(--color-text-muted)]">
        <span role="columnheader" className="py-[var(--space-1)]">
          {t('anchored.messages.diff_removed')}
        </span>
        <span role="columnheader" className="py-[var(--space-1)]">
          {t('anchored.messages.diff_added')}
        </span>
      </div>
      <div className="max-h-[var(--anchored-result-height)] overflow-auto">
        {rows.map((row, index) => (
          <div role="row" key={index} className="grid grid-cols-2 divide-x divide-[var(--color-border-subtle)]">
            <div
              role="cell"
              className={cn(
                'flex min-w-0 gap-[var(--space-1-5)] px-[var(--space-2)]',
                row.left
                  ? 'anchored-diff-del-line text-[var(--color-diff-removed)]'
                  : 'bg-transparent',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'w-8 shrink-0 select-none text-right text-[var(--color-syntax-comment)]',
                  row.left && 'anchored-diff-del-num',
                )}
              >
                {row.left?.number ?? ''}
              </span>
              <span className="min-w-0 [overflow-wrap:anywhere] whitespace-pre-wrap">{row.left?.text ?? ''}</span>
            </div>
            <div
              role="cell"
              className={cn(
                'flex min-w-0 gap-[var(--space-1-5)] px-[var(--space-2)]',
                row.right
                  ? 'anchored-diff-add-line text-[var(--color-diff-added)]'
                  : 'bg-transparent',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'w-8 shrink-0 select-none text-right text-[var(--color-syntax-comment)]',
                  row.right && 'anchored-diff-add-num',
                )}
              >
                {row.right?.number ?? ''}
              </span>
              <span className="min-w-0 [overflow-wrap:anywhere] whitespace-pre-wrap">{row.right?.text ?? ''}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const TOOL_STATUS_LABEL_KEY: Record<Exclude<ToolStatus, undefined>, string> = {
  running: 'anchored.messages.tool_running',
  success: 'anchored.messages.tool_success',
  error: 'anchored.messages.tool_error',
};

const TOOL_STATUS_TONE: Record<Exclude<ToolStatus, undefined>, string> = {
  running: 'bg-[var(--color-info-subtle)] text-[var(--color-info)]',
  success: 'bg-[var(--color-success-subtle)] text-[var(--color-success)]',
  error: 'bg-[var(--color-error-subtle)] text-[var(--color-error)]',
};

/** 状态色点映射：running  teal 脉动 / success / error，未上报不渲染。 */
function statusDotFor(status: ToolStatus): 'running' | 'success' | 'error' | null {
  if (status === 'running') return 'running';
  if (status === 'success') return 'success';
  if (status === 'error') return 'error';
  return null;
}

/** 状态 pill：卡片语言的 11-500 全圆 + 状态底色，左侧配状态色点。 */
function ToolStatusPill({ status }: { status: Exclude<ToolStatus, undefined> }) {
  const { t } = useI18n();
  const dot = statusDotFor(status);
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] px-2 py-px',
        'text-[11px] font-medium leading-[17px]',
        TOOL_STATUS_TONE[status],
      )}
    >
      {dot && <StatusDot status={dot} />}
      {t(TOOL_STATUS_LABEL_KEY[status])}
    </span>
  );
}

/** Codex 状态子弹：成功绿、失败红、运行中动画/暗淡。 */
function CodexBullet({ status }: { status: ToolStatus }) {
  const color =
    status === 'success'
      ? 'text-[var(--color-success)]'
      : status === 'error'
        ? 'text-[var(--color-error)]'
        : 'text-[var(--color-text-muted)]';
  return (
    <span
      aria-hidden="true"
      data-testid="anchored-exec-bullet"
      data-status={status ?? 'unreported'}
      className={cn('shrink-0 select-none font-bold', color, status === 'running' && 'motion-safe:animate-pulse')}
    >
      •
    </span>
  );
}

/**
 * 从工具调用里读出退出码：结构化的 arguments 优先，其次从 result / error 文本
 * 里识别 `exit 1` / `exit code: 1` / `exited with code 1` / `(exit 1)`。
 * 读不到时返回 null，不伪造。
 */
export function extractExitCode(call: ToolCall): number | null {
  const args = call.arguments ?? {};
  for (const key of ['exit_code', 'exitCode', 'returncode', 'return_code'] as const) {
    const value = args[key];
    if (typeof value === 'number' && Number.isFinite(value)) return value;
  }
  const text = `${call.result ?? ''}\n${call.error ?? ''}`;
  const match = text.match(/\bexit(?:\s+code)?\s*[:=]?\s*(-?\d+)\b/i)
    ?? text.match(/\bexited with(?:\s+(?:code|status))?\s+(-?\d+)\b/i)
    ?? text.match(/\(exit\s+(-?\d+)\)/i);
  return match?.[1] !== undefined ? Number.parseInt(match[1], 10) : null;
}

/** 退出码徽标色：0 中性、1（搜索无匹配）暗淡、其余非 0 报红。 */
function exitCodeTone(code: number): string {
  if (code === 0) return 'text-[var(--color-text-muted)]';
  if (code === 1) return 'text-[var(--color-text-disabled)]';
  return 'text-[var(--color-error)]';
}

/**
 * Codex 工具调用摘要：`• Ran <command>` + 首行 `  └ `、续行 4 空格 + 输出块。
 * 输出表头最多 5 行，超出追加省略行。展开后仍复用原详情面板。
 */
function CodexExecSummary({ call, status }: { call: ToolCall; status: ToolStatus }) {
  const args = call.arguments ?? {};
  const command = [args.command, args.cmd, args.shell, args.script].find(
    (value): value is string => typeof value === 'string' && value.length > 0,
  );
  const title = status === 'running' ? 'Running' : command ? 'You ran' : 'Ran';
  const output = command && call.result && !looksLikeDiff(call.result) ? call.result : undefined;
  const ellipsis = output ? outputEllipsisText(output) : null;
  const headLines = output ? output.split('\n').slice(0, CODEX_MAX_OUTPUT_HEAD_LINES) : [];
  const exitCode = extractExitCode(call);

  return (
    <div className="min-w-0 font-mono text-[length:var(--text-xs)] leading-[var(--leading-normal)] tabular-nums">
      <p className="flex min-w-0 items-baseline gap-[var(--space-1-5)]">
        <CodexBullet status={status} />
        <span className="shrink-0 font-bold text-[var(--color-text-primary)]">{title}</span>
        {command && <span className="min-w-0 truncate text-[var(--color-text-secondary)]">{command}</span>}
        {exitCode !== null && (
          <span
            data-testid="anchored-exec-exit-code"
            data-exit-code={exitCode}
            className={cn('shrink-0', exitCodeTone(exitCode))}
          >
            {`(exit ${exitCode})`}
          </span>
        )}
      </p>
      {headLines.length > 0 && (
        <>
          {headLines.map((line, index) => (
            <p
              key={index}
              data-testid={index === 0 ? 'anchored-exec-command-continuation' : 'anchored-exec-output-line'}
              className="flex min-w-0 gap-[var(--space-1-5)] text-[var(--color-text-muted)]"
            >
              <span aria-hidden="true" className="shrink-0 select-none text-[var(--color-text-muted)]">
                {index === 0 ? '  └ ' : '    '}
              </span>
              <span className="min-w-0 truncate">{line}</span>
            </p>
          ))}
          {ellipsis && (
            <p className="flex min-w-0 gap-[var(--space-1-5)] text-[var(--color-text-muted)]">
              <span aria-hidden="true" className="shrink-0 select-none">
                {'  └ '}
              </span>
              <span data-testid="anchored-exec-output-ellipsis" className="min-w-0 truncate">
                {ellipsis}
              </span>
            </p>
          )}
        </>
      )}
    </div>
  );
}

/** 入参摘要：每个参数截成一行短文本。 */
export function summarizeArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args ?? {});
  if (entries.length === 0) return '';
  return entries
    .slice(0, 4)
    .map(([key, value]) => {
      const text = typeof value === 'string' ? value : JSON.stringify(value) ?? '';
      const clipped = text.length > 64 ? `${text.slice(0, 64)}…` : text;
      return `${key}: ${clipped}`;
    })
    .join(' · ');
}

/**
 * 工具调用卡片（样式 3）内嵌工具结果块（样式 4）。
 * 结果默认折叠，仅显示状态标签 + 展开按钮；展开后显示完整日志，最大高 240px。
 * 输出命中 unified diff 时按代码差异块（样式 5）渲染。
 */
export function ToolCallCard({
  call,
  active,
  defaultExpanded,
  rawResult = false,
}: {
  call: ToolCall;
  active: boolean;
  defaultExpanded: boolean;
  /**
   * 渲染为纯工具结果块（样式 4）：不显示入参摘要与调用状态标签，
   * 只保留结果状态与展开控件，用于 role === 'tool' 的历史结果节点。
   */
  rawResult?: boolean;
}) {
  const { t } = useI18n();
  const failedToolIds = useAnchoredStore((s) => s.failedToolIds);
  const status: ToolStatus = call.error || failedToolIds.includes(call.id)
    ? 'error'
    : call.status ?? (active ? 'running' : undefined);
  const failed = status === 'error';
  // 触发规则：工具执行失败则自动展开工具结果。
  const autoOpen = failed;
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [dismissedFailure, setDismissedFailure] = useState(false);
  const isOpen = (autoOpen && !dismissedFailure) || expanded;
  const hasArgs = !rawResult && Object.keys(call.arguments ?? {}).length > 0;
  const isDiff = call.result !== undefined && looksLikeDiff(call.result);
  const panelId = useId();

  if (rawResult) {
    return (
      <div
        data-testid="anchored-tool-result"
        data-tool-status={status ?? 'unreported'}
        className="workbench-tool overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)]"
      >
        <header className="flex min-h-[var(--control-height-sm)] items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-2-5)] py-[var(--space-1-5)]">
          <WorkbenchIcon name="tool" className="shrink-0 text-[var(--color-text-secondary)]" />
          <span className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]">
            {call.name}
          </span>
          {status && <ToolStatusPill status={status} />}
        </header>
        <div className="px-[var(--space-2-5)] pb-[var(--space-2)] pt-[var(--space-1)]">
          <button
            type="button"
            aria-expanded={isOpen}
            aria-controls={panelId}
            onClick={() => { setDismissedFailure(failed); setExpanded(!isOpen); }}
            className="flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            {isOpen ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
            <span className={cn(failed && 'text-[var(--color-error)]')}>
              {failed ? t('anchored.messages.tool_result_failed') : t(isOpen ? 'tool_call.collapse' : 'tool_call.expand')}
            </span>
          </button>
          <div id={panelId} hidden={!isOpen} className="workbench-tool-result max-h-[var(--anchored-result-height)] overflow-auto">
            {call.error && (
              <ToolCodeBlock tone="error" label={t('tool_call.error_detail')}>
                {call.error}
              </ToolCodeBlock>
            )}
            {call.result !== undefined && (isDiff ? (
              <DiffCell diffText={call.result ?? ''} />
            ) : (
              <ToolCodeBlock tone={failed ? 'error' : 'default'} label={t('anchored.messages.tool_result')}>
                {call.result || t('tool_call.output_empty')}
              </ToolCodeBlock>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="anchored-tool-card"
      data-tool-status={status ?? 'unreported'}
      className={cn(
        'workbench-tool overflow-hidden rounded-[var(--radius-lg)] border bg-[var(--color-bg-surface-1)]',
        failed ? 'border-[var(--color-error)]/40' : 'border-[var(--color-border-default)]',
      )}
    >
      <header className="flex min-h-[var(--control-height-sm)] items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-2-5)] py-[var(--space-1-5)]">
        <WorkbenchIcon name="tool" className="shrink-0 text-[var(--color-text-secondary)]" />
        <span className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]">
          {call.name}
        </span>
        {status && <ToolStatusPill status={status} />}
      </header>

      <div className="px-[var(--space-2-5)] pb-[var(--space-2)] pt-[var(--space-1-5)]">
        <CodexExecSummary call={call} status={status} />

        {(hasArgs || call.result !== undefined || failed) && (
          <div>
            <button
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => { setDismissedFailure(failed); setExpanded(!isOpen); }}
              className="mt-[var(--space-1-5)] flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
            >
              {isOpen ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
              <span className={cn(failed && 'text-[var(--color-error)]')}>
                {failed ? t('anchored.messages.tool_result_failed') : t(isOpen ? 'tool_call.collapse' : 'tool_call.expand')}
              </span>
            </button>
            <div id={panelId} hidden={!isOpen} className="workbench-tool-result max-h-[var(--anchored-result-height)] overflow-auto">
              {isOpen && hasArgs && (
                <ToolCodeBlock label={t('tool_call.arguments')}>
                  {JSON.stringify(call.arguments, null, 2)}
                </ToolCodeBlock>
              )}
              {isOpen && call.error && (
                <ToolCodeBlock tone="error" label={t('tool_call.error_detail')}>
                  {call.error}
                </ToolCodeBlock>
              )}
              {isOpen && call.result !== undefined && (isDiff ? (
                <DiffCell diffText={call.result ?? ''} />
              ) : (
                <ToolCodeBlock tone={failed ? 'error' : 'default'} label={t('anchored.messages.tool_result')}>
                  {call.result || t('tool_call.output_empty')}
                </ToolCodeBlock>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageTimestamp({ timestamp }: { timestamp?: Date }) {
  if (!timestamp) return null;
  return (
    <p className="mt-[var(--space-1)] text-center text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
      {formatTime(timestamp)}
    </p>
  );
}

function SessionHeaderCell({ workspace }: { workspace?: string }) {
  return (
    <div data-testid="anchored-session-header" className="flex flex-col gap-[var(--space-1)]">
      <p className="font-mono text-[length:var(--text-sm)] leading-[var(--leading-normal)]">
        <span className="font-bold text-[var(--color-accent-foreground)]">{CODEX_PROMPT_GLYPH} </span>
        <span className="font-bold text-[var(--color-text-primary)]">{CODEX_PRODUCT_NAME}</span>
        <span className="text-[var(--color-text-muted)]"> ({CODEX_VERSION})</span>
      </p>
      {workspace && (
        <p className="pl-[var(--space-4)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
          {workspace}
        </p>
      )}
    </div>
  );
}

function UserBubble({ message }: { message: Message }) {
  return (
    <div className="flex w-full min-w-0 items-start gap-[var(--space-2)]" data-testid="anchored-user-bubble">
      <span aria-hidden="true" className="mt-[var(--space-2)] shrink-0 select-none font-bold text-[var(--color-text-muted)]">
        {CODEX_USER_GLYPH}
      </span>
      <div className="flex min-w-0 flex-1 flex-col items-start">
        <div className="workbench-user-message max-w-[85%] rounded-[var(--radius-lg)] bg-[var(--color-bg-surface-2)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-sm)] leading-relaxed text-[var(--color-text-primary)]">
          <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{message.content}</p>
          {message.images && message.images.length > 0 && (
            <div className="mt-[var(--space-2)] flex flex-wrap gap-[var(--space-2)]">
              {message.images.map((image, index) => (
                <img
                  key={index}
                  src={image}
                  alt=""
                  className="h-20 w-20 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] object-cover"
                />
              ))}
            </div>
          )}
        </div>
        <MessageTimestamp timestamp={message.timestamp} />
      </div>
    </div>
  );
}

/**
 * 工具调用的状态。显式上报优先，其次是本轮仍在流式（tool turn 里还没落地结果
 * 的调用就是运行中），后端没上报状态且本轮已收尾时保持"未上报"，不编造成功。
 */
function resolveCallStatus(call: ToolCall, active: boolean, failed: boolean): AgentToolStatus {
  if (failed) return 'error';
  if (call.status === 'running') return 'running';
  if (call.status === 'success') return 'success';
  if (call.requiresApproval) return 'awaiting-approval';
  return active ? 'running' : 'pending';
}

/**
 * 是否仍卡在审批上。useChat 在等待决策时保持 `requiresApproval: true` 且不写
 * status，结果回来后把两者一起翻掉，所以"要审批且没落定"就是精确的判定。
 */
function awaitingApproval(call: ToolCall, failed: boolean): boolean {
  return Boolean(call.requiresApproval) && !call.error && !failed && call.status === undefined;
}

/** 步骤条用的状态：AgentToolStatus 的审批态在链路上落在未开始之前。 */
function toStepStatus(status: AgentToolStatus): ThoughtStepStatus {
  switch (status) {
    case 'running':
      return 'running';
    case 'success':
      return 'success';
    case 'error':
      return 'error';
    default:
      return 'pending';
  }
}

/** 少于两步的链路画成链没有信息量，卡片本身就是全部内容。 */
const MIN_CHAIN_STEPS = 2;

/**
 * 多步骤 / 子代理执行的可视化：数据全部来自这一回合自己的 tool turns——工具名
 * 即步骤标签（mono，与卡片同源），状态即步骤状态，不引入任何推断出来的步骤。
 */
function thoughtChainSteps(
  calls: ToolCall[],
  active: boolean,
  failed: (call: ToolCall) => boolean,
): ThoughtChainStep[] | null {
  if (calls.length < MIN_CHAIN_STEPS) return null;
  return calls.map((call) => ({
    id: call.id,
    label: call.name,
    status: toStepStatus(resolveCallStatus(call, active, failed(call))),
    icon: getAgentToolIcon(call.name),
  }));
}

/**
 * 一个 tool turn：先一条链路概览（≥2 步时），再逐个调用卡片。
 *
 * 卡在审批上的调用走 AgentToolCard——整份 transcript 里唯一带审批行的工具面；
 * 其余调用留在 Codex 工具卡上，它的折叠摘要（CodexExecSummary）只在存在
 * `command` 时才显示输出头，所以 read_file 这类调用在折叠态不会泄露输出、
 * 展开后也不会出现同一段文本两次。审批由 AnchoredPopupStack 统一接管，
 * 这里只把状态呈现出来。
 */
function ToolTurn({ message, active }: { message: Message; active: boolean }) {
  const calls = message.toolCalls ?? [];
  const failedToolIds = useAnchoredStore((s) => s.failedToolIds);
  const isFailed = (call: ToolCall) => Boolean(call.error) || call.status === 'error' || failedToolIds.includes(call.id);
  const steps = thoughtChainSteps(calls, active, isFailed);
  return (
    <div className="flex w-full min-w-0 flex-col items-start gap-[var(--space-2)]" data-testid="anchored-tool-turn">
      {steps && <ThoughtChainPanel steps={steps} className="w-full" />}
      {calls.map((call) => (
        <div key={call.id} className="w-full">
          {awaitingApproval(call, isFailed(call)) ? (
            <AgentToolCard name={call.name} status="awaiting-approval" input={call.arguments} />
          ) : (
            <ToolCallCard call={call} active={active} defaultExpanded={false} />
          )}
        </div>
      ))}
      <MessageTimestamp timestamp={message.timestamp} />
    </div>
  );
}

/**
 * 消息流。用户消息靠右、Agent 消息靠左；样式按五种消息类型严格区分。
 */
/**
 * 单条消息行（含前置 hairline 分隔）。用 React.memo 包裹：useChat 的 applyTurn
 * 用 `prev.map(msg => msg.id === id ? mutate(msg) : msg)` 更新，未变的历史消息
 * 保留原引用，于是流式分片落地时只有当前流式那一行重渲，200 条历史行被跳过——
 * 这是消除长任务 / 帧阻塞（任务48 实测 frameP95 200-333ms）的关键。
 */
const MessageRow = memo(function MessageRow({
  message,
  active,
  showDivider,
}: {
  message: Message;
  active: boolean;
  showDivider: boolean;
}) {
  const turn = (() => {
    if (message.role === 'user') {
      return <UserBubble message={message} />;
    }
    if (message.role === 'tool') {
      return (
        <ToolCallCard
          call={{
            id: message.id,
            name: message.tool_name ?? 'tool',
            arguments: {},
            result: message.content,
            status: 'success',
          }}
          active={false}
          defaultExpanded={false}
          rawResult
        />
      );
    }
    if (message.role === 'system') {
      return (
        <p className="text-center text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
          {message.content}
        </p>
      );
    }
    const hasTools = (message.toolCalls?.length ?? 0) > 0;
    return (
      <div className="flex flex-col gap-[var(--space-2)]">
        {hasTools && <ToolTurn message={message} active={active} />}
        {(message.content || message.reasoning || message.failed || (!hasTools && active)) && (
          <ThinkingBubble message={message} active={active} />
        )}
      </div>
    );
  })();
  // 8px 节奏 + hairline 分隔：相邻 turn 之间一条细线，首条前不画。
  return (
    <div className="flex flex-col gap-[var(--space-2)]">
      {showDivider && <hr className="w-full border-0 border-t border-[var(--color-border-subtle)]" aria-hidden="true" />}
      {turn}
    </div>
  );
});

export function AnchoredMessageFlow({
  messages,
  activeMessageId,
  workspace,
  loading = false,
}: {
  messages: Message[];
  activeMessageId?: string;
  workspace?: string;
  /** 历史消息尚在加载：在会话头之下渲染骨架行，加载态不冒充空态。 */
  loading?: boolean;
}) {
  return (
    <div data-transcript className="flex flex-col gap-[var(--space-2)]">
      <SessionHeaderCell workspace={workspace} />
      {loading && messages.length === 0 && <ChatStreamSkeleton />}
      {messages.map((message, index) => (
        <MessageRow
          key={message.id}
          message={message}
          active={message.id === activeMessageId}
          showDivider={index > 0}
        />
      ))}
    </div>
  );
}
