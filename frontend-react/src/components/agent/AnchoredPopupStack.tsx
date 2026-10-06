import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { api } from '../../api';
import { useI18n } from '../../i18n';
import { useAnchoredStore } from '../../store/anchored';
import type { AnchoredPopup } from '../../store/anchored';
import { useWorkspaceStore } from '../../store/workspace';
import type { PermissionMode } from '../../store/workspace';
import { HitlPanel } from './HitlPanel';

const DEFAULT_EXEC_TITLE = 'Would you like to run the following command?';
const DEFAULT_PATCH_TITLE = 'Would you like to make the following edits?';
const DEFAULT_PERMISSIONS_TITLE = 'Would you like to grant these permissions?';
const CONFIRM_FOOTER = 'Press enter to confirm or esc to cancel';

export type CodexApprovalVariant = 'exec' | 'patch' | 'permissions';

/**
 * 后端模式下不存在"本会话持续放行"这个决策的三种：strict 与 plan 未显式放行即
 * 拒绝，bypass 直接跳过权限检查（见 components/workspace/permissionMode.ts 的
 * 模式说明）。其余模式才逐次询问，"始终允许"才有落点。
 */
const MODES_WITHOUT_SESSION_ALLOW: readonly PermissionMode[] = ['strict', 'plan', 'bypass'];

interface CodexOption {
  id: 'allow' | 'allow_session' | 'allow_always' | 'deny' | 'dismiss';
  label: string;
  hint: string;
  decision?: 'allow' | 'deny';
}

interface PopupMeta {
  variant: CodexApprovalVariant;
  reason?: string;
  prefix?: string;
  command?: string;
  path?: string;
  description?: string;
  permissionRule?: string;
  supported: boolean;
}

function readString(payload: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = payload?.[key];
  return typeof value === 'string' && value.trim() ? value : undefined;
}

/** 弹窗显式声明的审批变体；未声明返回 null，交给推断或兜底形态。 */
function readDeclaredVariant(popup: AnchoredPopup): CodexApprovalVariant | null {
  const explicit = popup.payload?.['variant'];
  if (explicit === 'exec' || explicit === 'patch' || explicit === 'permissions') return explicit;
  if (explicit === 'command') return 'exec';
  if (explicit === 'edit' || explicit === 'edits') return 'patch';
  return null;
}

/** 没有显式声明时按弹窗自带的信息推断审批形态；无任何线索按 exec 处理。 */
function inferVariant(popup: AnchoredPopup): CodexApprovalVariant {
  if (readString(popup.payload, 'permissionRule') || popup.fields?.some((f) => f.key === 'permissionRule')) {
    return 'permissions';
  }
  if (popup.kind === 'params') return 'permissions';
  if (popup.path && !popup.command) return 'patch';
  if (popup.command) return 'exec';
  if (/permission/i.test(popup.title)) return 'permissions';
  if (/\bedit/i.test(popup.title)) return 'patch';
  return 'exec';
}

function detectVariant(popup: AnchoredPopup): CodexApprovalVariant {
  return readDeclaredVariant(popup) ?? inferVariant(popup);
}

/**
 * 编号选项是否成立：弹窗要么显式声明变体，要么带着具体的审批对象（命令 / 路径 /
 * 权限规则 / 参数表），要么自己声明了主确认按钮。只剩标题与描述的通用审批列不出
 * 有意义的编号选项，交给 HitlPanel 兜底。
 */
function hasCodexOptions(popup: AnchoredPopup, meta: PopupMeta): boolean {
  if (readDeclaredVariant(popup)) return true;
  if (meta.command || meta.path || meta.permissionRule) return true;
  if (popup.fields?.length) return true;
  return Boolean(popup.confirmLabel?.trim());
}

/** 当前权限配置是否提供"始终允许"。配置未上报时按没有该能力处理。 */
function sessionAllowAvailable(mode: PermissionMode | null): boolean {
  return mode !== null && !MODES_WITHOUT_SESSION_ALLOW.includes(mode);
}

function resolveMeta(popup: AnchoredPopup): PopupMeta {
  const variant = detectVariant(popup);
  const prefix = readString(popup.payload, 'commandPrefix') ?? readString(popup.payload, 'prefix');
  const permissionRule =
    readString(popup.payload, 'permissionRule') ??
    popup.fields?.find((f) => f.key === 'permissionRule')?.value;
  const toolCallId = popup.payload?.['toolCallId'];
  return {
    variant,
    reason: popup.description,
    prefix,
    command: popup.command,
    path: popup.path,
    description: readString(popup.payload, 'description'),
    permissionRule,
    supported: popup.kind === 'approval' && typeof toolCallId === 'string',
  };
}

function codexTitle(meta: PopupMeta, popup: AnchoredPopup): string {
  if (popup.title && popup.title.trim()) return popup.title;
  if (meta.variant === 'patch') return DEFAULT_PATCH_TITLE;
  if (meta.variant === 'permissions') return DEFAULT_PERMISSIONS_TITLE;
  return DEFAULT_EXEC_TITLE;
}

function optionsFor(meta: PopupMeta): CodexOption[] {
  if (meta.variant === 'patch') {
    return [
      { id: 'allow', label: 'Yes, proceed', hint: 'y', decision: 'allow' },
      { id: 'allow_session', label: 'Yes, and don\'t ask again for these files', hint: 'a', decision: 'allow' },
      { id: 'dismiss', label: 'No, and tell Climber what to do differently', hint: 'esc', decision: 'deny' },
    ];
  }
  if (meta.variant === 'permissions') {
    return [
      { id: 'allow', label: 'Yes, grant these permissions for this turn', hint: 'y', decision: 'allow' },
      { id: 'allow_session', label: 'Yes, grant for this turn with strict auto review', hint: 'r', decision: 'allow' },
      { id: 'allow_always', label: 'Yes, grant these permissions for this session', hint: 'a', decision: 'allow' },
      { id: 'dismiss', label: 'No, continue without permissions', hint: 'd', decision: 'deny' },
    ];
  }
  const prefixLabel = meta.prefix ?? meta.command ?? '';
  return [
    { id: 'allow', label: 'Yes, proceed', hint: 'y', decision: 'allow' },
    {
      id: 'allow_session',
      label: `Yes, and don't ask again for commands that start with \`${prefixLabel}\``,
      hint: 'p',
      decision: 'allow',
    },
    { id: 'dismiss', label: 'No, and tell Climber what to do differently', hint: 'esc', decision: 'deny' },
  ];
}

function CodexPopupCard({ popup, selected }: { popup: AnchoredPopup; selected: boolean }) {
  const { t } = useI18n();
  const headingId = useId();
  const listId = useId();
  const resolvePopup = useAnchoredStore((s) => s.resolvePopup);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRef = useRef<HTMLLIElement>(null);

  const meta = useMemo(() => resolveMeta(popup), [popup]);
  const title = codexTitle(meta, popup);
  const options = useMemo(() => optionsFor(meta), [meta]);
  const [activeIndex, setActiveIndex] = useState(0);
  const active = Math.min(activeIndex, options.length - 1);

  useEffect(() => {
    if (selected) activeRef.current?.focus?.();
  }, [selected, active]);

  const decisionOf = (option: CodexOption): 'allow' | 'deny' => option.decision ?? 'deny';

  const run = async (option: CodexOption | undefined) => {
    if (submitting || !option) return;
    const decision = decisionOf(option);
    const toolCallId = popup.payload?.['toolCallId'];
    if (!meta.supported || typeof toolCallId !== 'string') {
      resolvePopup(popup.id);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.resolvePermission(toolCallId, decision);
      resolvePopup(popup.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t('anchored.popup.submit_failed'));
    } finally {
      setSubmitting(false);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown' || event.key === 'j') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % options.length);
      return;
    }
    if (event.key === 'ArrowUp' || event.key === 'k') {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + options.length) % options.length);
      return;
    }
    const numeric = Number.parseInt(event.key, 10);
    if (!event.metaKey && !event.ctrlKey && !event.altKey && Number.isInteger(numeric) && numeric >= 1 && numeric <= options.length) {
      event.preventDefault();
      void run(options[numeric - 1]);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      void run(options[active]);
      return;
    }
    if (event.key === 'Escape' || event.key === 'n') {
      event.preventDefault();
      void run(options[options.length - 1]);
      return;
    }
    const shortcut = options.find((option) => option.hint.length === 1 && option.hint === event.key.toLowerCase());
    if (shortcut) {
      event.preventDefault();
      void run(shortcut);
    }
  };

  return (
    <section
      role="dialog"
      aria-modal="false"
      aria-labelledby={headingId}
      data-testid="anchored-popup"
      data-popup-kind={popup.kind}
      data-approval-variant={meta.variant}
      onKeyDown={onKeyDown}
      tabIndex={-1}
      className="rounded-[var(--radius-lg)] border border-[var(--color-border-accent)] bg-[var(--color-bg-surface-1)] p-[var(--space-3)] shadow-[var(--shadow-md)]"
    >
      <header className="flex items-start gap-2">
        <h3 id={headingId} className="min-w-0 flex-1 text-[length:var(--text-sm)] font-bold leading-snug text-[var(--color-text-primary)]">
          {title}
        </h3>
        <button
          type="button"
          onClick={() => void run(options[options.length - 1])}
          disabled={submitting}
          aria-label="Dismiss"
          className="mt-[1px] flex size-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        >
          <X size={12} aria-hidden="true" />
        </button>
      </header>

      {meta.reason && (
        <p className="mt-[var(--space-2)] text-[length:var(--text-xs)] leading-relaxed text-[var(--color-text-secondary)]">
          <span className="font-bold text-[var(--color-text-primary)]">Reason:</span> {meta.reason}
        </p>
      )}

      {meta.variant === 'patch' && meta.description && (
        <p className="mt-[var(--space-1)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
          <span className="font-bold text-[var(--color-text-primary)]">Description:</span> {meta.description}
        </p>
      )}

      {meta.command && (
        <p className="mt-[var(--space-2)] truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]" title={meta.command}>
          $ {meta.command}
        </p>
      )}
      {meta.variant === 'patch' && (
        <p className="mt-[var(--space-1)] truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]" title={meta.path}>
          <span className="font-bold text-[var(--color-text-primary)]">Destination:</span> {meta.path ?? 'unavailable'}
        </p>
      )}
      {meta.variant === 'permissions' && meta.permissionRule && (
        <p className="mt-[var(--space-2)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">
          <span className="font-bold text-[var(--color-text-primary)]">Permission rule:</span> {meta.permissionRule}
        </p>
      )}

      {meta.supported && (
        <button
          type="button"
          onClick={() => void run(options[0])}
          disabled={submitting}
          aria-label={popup.confirmLabel ?? 'Approve'}
          className="mt-[var(--space-2)] w-full rounded-[var(--radius-sm)] bg-[var(--color-accent)] px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-xs)] font-bold text-[var(--color-accent-text)] transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {popup.confirmLabel ?? 'Approve'}
        </button>
      )}

      <ul id={listId} className="mt-[var(--space-2)] space-y-[2px]">
        {options.map((option, index) => {
          const isActive = index === active;
          return (
            <li key={option.id} ref={isActive ? activeRef : undefined}>
              <button
                type="button"
                onClick={() => void run(option)}
                disabled={submitting}
                aria-selected={isActive}
                className={cn(
                  'flex w-full items-baseline gap-2 rounded-[var(--radius-sm)] px-[var(--space-1)] py-[var(--space-1)] text-start text-[length:var(--text-xs)] transition-colors focus-visible:outline-none',
                  isActive
                    ? 'bg-[var(--color-accent-foreground)] font-bold text-[var(--color-bg-surface-1)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]',
                )}
              >
                <span className="shrink-0 font-mono">{index === 0 ? '›' : ' '}</span>
                <span className="min-w-0 flex-1">
                  {index + 1}. {option.label}
                </span>
                <span className={cn('shrink-0 font-mono text-[length:var(--text-2xs)]', isActive ? 'text-[var(--color-bg-surface-1)]' : 'text-[var(--color-text-muted)]')}>
                  ({option.hint})
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {!meta.supported && (
        <p role="status" className="mt-[var(--space-2)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
          {t('anchored.popup.unsupported_hint')}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-error)]">
          {t('anchored.popup.submit_error', { error })}
        </p>
      )}

      <p className="mt-[var(--space-3)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{CONFIRM_FOOTER}</p>
    </section>
  );
}

/**
 * 兜底审批形态：弹窗没有编号选项可列时，只保留允许 / 拒绝两个决策，权限配置提供
 * "始终允许"时再加一个。提交与编号选项分支共用同一入口——POST
 * /api/v1/permissions/resolve，body 仍是 { tool_call_id, decision }；decision 只做
 * 显式映射，不在界面里推导审批策略。悬停态、错误与提交中状态由 HitlPanel 负责。
 */
function HitlApprovalCard({ popup, meta }: { popup: AnchoredPopup; meta: PopupMeta }) {
  const { t } = useI18n();
  const resolvePopup = useAnchoredStore((s) => s.resolvePopup);
  const permissionMode = useWorkspaceStore((s) => s.permissionMode);

  const decide = async (decision: 'allow' | 'deny') => {
    const toolCallId = popup.payload?.['toolCallId'];
    if (!meta.supported || typeof toolCallId !== 'string') {
      resolvePopup(popup.id);
      return;
    }
    await api.resolvePermission(toolCallId, decision);
    resolvePopup(popup.id);
  };

  return (
    <HitlPanel
      title={codexTitle(meta, popup)}
      description={meta.reason}
      onApprove={() => decide('allow')}
      onReject={() => decide('deny')}
      onDismiss={() => decide('deny')}
      approveLabel={t('anchored.popup.approve')}
      rejectLabel={t('anchored.popup.cancel')}
      dismissLabel={t('anchored.popup.dismiss')}
      {...(sessionAllowAvailable(permissionMode) ? { onAlwaysAllow: () => decide('allow') } : {})}
      className="static w-full rounded-[var(--radius-md)] border-[var(--color-border-accent)] p-[var(--space-3)] shadow-[var(--shadow-md)]"
    />
  );
}

/** 有编号选项走 Codex 弹窗，没有则走兜底审批形态。 */
function AnchoredPopupCard({ popup, selected }: { popup: AnchoredPopup; selected: boolean }) {
  const meta = useMemo(() => resolveMeta(popup), [popup]);
  const codex = useMemo(() => hasCodexOptions(popup, meta), [popup, meta]);
  if (!codex) return <HitlApprovalCard popup={popup} meta={meta} />;
  return <CodexPopupCard popup={popup} selected={selected} />;
}

export function AnchoredPopupStack() {
  const popups = useAnchoredStore((s) => s.popups);
  if (popups.length === 0) return null;
  const ordered = [...popups].reverse();
  return (
    <div
      data-testid="anchored-popup-stack"
      aria-label="anchored.popups"
      className="flex flex-col gap-[var(--space-2)]"
    >
      {ordered.map((popup, index) => (
        <AnchoredPopupCard key={popup.id} popup={popup} selected={index === 0} />
      ))}
    </div>
  );
}
