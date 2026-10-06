import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Shield, Check, X, FileText, Terminal, Globe, ChevronDown, ChevronRight } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import type { StatusTone } from '../../lib/icons';
import { Button } from '../ui/Button';
import { StatusIcon } from '../ui/StatusIcon';
import { useWorkspaceStore } from '../../store/workspace';
import type { PermissionMode } from '../../store/workspace';

export interface PermissionRequest {
  id: string;
  action: 'file_read' | 'file_write' | 'file_delete' | 'command' | 'network' | 'mcp_tool';
  description: string;
  details?: string;
  severity: 'low' | 'medium' | 'high';
  timestamp: number;
  /** Exact shell command that will run, when the backend can supply it. */
  command?: string;
  /** Exact filesystem path that will be written or deleted. */
  path?: string;
  /** Exact URL that will be fetched. */
  url?: string;
  /** Remote tool identifier for `mcp_tool` actions. */
  tool?: string;
}

interface FloatingPermissionDialogProps {
  requests: PermissionRequest[];
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  onApproveAll: () => void;
}

type ApprovalTargetKind = 'command' | 'path' | 'url' | 'tool';

export interface ApprovalTarget {
  kind: ApprovalTargetKind;
  value: string;
}

/**
 * Where a request stands in its own submission lifecycle. `submitting`,
 * `submitted` and `expired` are locked, and an expired request stays locked on
 * purpose: the backend has already dropped that decision, so replaying it could
 * only fail again.
 */
export type ApprovalStatus = 'idle' | 'submitting' | 'submitted' | 'expired' | 'error';

/** The decision the user made, and the one the backend answered. */
export type ApprovalDecision = 'approve' | 'deny';

/**
 * The state a card is actually in, which is not the same thing as its
 * submission status: `submitting` with a `deny` decision is a different state
 * from `submitting` with an `approve` decision, and the copy says so.
 *
 * `unreported` has no producer in this component. It is the fallback for a
 * status this build does not know, so a state it cannot read renders as
 * "not reported" instead of borrowing a success it never observed.
 */
export type ApprovalState =
  | 'pending'
  | 'approving'
  | 'denying'
  | 'approved'
  | 'denied'
  | 'expired'
  | 'error'
  | 'unreported';

/**
 * State to status tone. `pending` is the `approval` tone because the workbench
 * is waiting on the user, and that is the one state no run can leave by itself.
 * `approved` and `denied` are both real outcomes the backend confirmed, so they
 * take `success` and `info` respectively: a deliberate denial is a decision, not
 * a fault. `expired` and `unreported` share the `unknown` tone on purpose,
 * because both mean the backend stopped waiting for this request.
 */
const STATE_TONE: Record<ApprovalState, StatusTone> = {
  pending: 'approval',
  approving: 'loading',
  denying: 'loading',
  approved: 'success',
  denied: 'info',
  expired: 'unknown',
  error: 'error',
  unreported: 'unknown',
};

/** Resolve a submission status and its decision into the state a card reports. */
export function approvalState(status: ApprovalStatus, decision: ApprovalDecision | null): ApprovalState {
  switch (status) {
    case 'idle':
      return 'pending';
    case 'submitting':
      return decision === 'deny' ? 'denying' : 'approving';
    case 'submitted':
      return decision === 'deny' ? 'denied' : 'approved';
    case 'expired':
      return 'expired';
    case 'error':
      return 'error';
    default:
      return 'unreported';
  }
}

/** Tone for a card state, so a caller never picks the colour itself. */
export function approvalTone(state: ApprovalState): StatusTone {
  return STATE_TONE[state];
}

/**
 * How much authority the backend's current permission mode leaves with the
 * dialog. `default` is the mode where only reads pass on their own and every
 * mutation waits for a person, `auto` is where the backend classifier decides
 * and only an out-of-workspace path still asks, and `bypass` is where nothing
 * is checked at all. The three are the whole point of the chip: a card arriving
 * means something stopped the run, and which of the three produced it is the
 * first thing worth knowing.
 */
const MODE_TONE: Record<PermissionMode, StatusTone> = {
  // Reads pass, mutations wait on a human: the dialog is the release valve.
  default: 'approval',
  // Edits inside the workspace pass, so a card here is about the file edits
  // the classifier accepted.
  acceptEdits: 'success',
  // Read-only planning: nothing the dialog could allow would run anyway.
  plan: 'queued',
  // The backend judges each action; only a path outside the workspace asks.
  auto: 'info',
  // No check at all, so an approval here is a leftover rather than a gate.
  bypass: 'warning',
  // Deny unless explicitly allowed: this request is an explicit allow.
  strict: 'approval',
};

/** The decision the user has made about a request, held outside its card. */
export interface ApprovalDraft {
  /** The authorisable content the decision was made against. */
  signature: string;
  active: 'approve' | null;
}

/**
 * A rejection the backend will never accept again. 409 is the conflict the
 * permission endpoint answers once the request is gone; a body that names the
 * condition counts too, because a proxy or a newer backend version can report it
 * as text. Everything else — network, validation, server faults — is retryable.
 */
export function isExpiredError(error: unknown): boolean {
  const carrier = error as { status?: number; response?: { status?: number } } | null | undefined;
  const status = carrier?.status ?? carrier?.response?.status;
  if (status === 409) return true;
  if (status !== undefined) return false;
  const message = error instanceof Error ? error.message : typeof error === 'string' ? error : '';
  return /\bexpired\b|已过期|已失效/i.test(message);
}

/** Icon for each action kind. Wording lives in the `permission_dialog` locale
 *  namespace so the whole card reads in the current language. */
const ACTION_ICONS = {
  file_read: FileText,
  file_write: FileText,
  file_delete: FileText,
  command: Terminal,
  network: Globe,
  mcp_tool: Terminal,
};

function firstPathIn(text: string): string | undefined {
  // Handles the shapes a free-text `details` field arrives in: a `key: value`
  // line, shell redirection, a bare absolute path among words, or a flag value.
  const keyed = text.match(/(?:^|\n)\s*(?:path|file|target|destination)\s*[:=]\s*(\S+)/i);
  if (keyed?.[1]) return keyed[1];
  const redirect = text.match(/(?:^|\s)>{1,2}\s*(\S+)/);
  if (redirect?.[1]) return redirect[1];
  const absolute = text.match(/(?:^|\s)((?:\/[^\s]*|[A-Za-z]:\\[^\s]*|\.{1,2}[\\/][^\s]*))/);
  if (absolute?.[1]) return absolute[1];
  const flag = text.match(/(?:^|\s)-{1,2}[A-Za-z][\w-]*(?:=|\s+)(\S+)/);
  if (flag?.[1]) return flag[1];
  const bare = text.trim().match(/^(?:\/[^\s]*|[A-Za-z]:\\[^\s]*|\.{1,2}[\\/][^\s]*)$/);
  return bare?.[0];
}

/**
 * The concrete thing the user is authorising. Structured fields win; the
 * free-text `details` fallback keeps older callers honest by naming the
 * command or path even when the backend only sent a blob.
 */
export function extractApprovalTarget(request: PermissionRequest): ApprovalTarget | undefined {
  const structured = request.action === 'command' ? request.command
    : request.action === 'network' ? request.url
      : request.action === 'mcp_tool' ? request.tool
        : request.path;
  if (structured?.trim()) return { kind: request.action === 'mcp_tool' ? 'tool' : request.action === 'network' ? 'url' : request.action === 'command' ? 'command' : 'path', value: structured.trim() };

  const details = request.details?.trim();
  if (details) {
    if (request.action === 'command') return { kind: 'command', value: details };
    const path = firstPathIn(details);
    if (path) return { kind: 'path', value: path };
  }
  return undefined;
}

function ApprovalChip({ state }: { state: ApprovalState }) {
  const { t } = useI18n();
  const label = t(`permission_dialog.state.${state}`);
  return (
    <span className="flex min-w-0 items-center gap-[var(--space-1)] text-[length:var(--text-2xs)]">
      <StatusIcon tone={approvalTone(state)} size="xs" />
      <span className="truncate text-[var(--color-text-muted)]">{label}</span>
    </span>
  );
}

/**
 * A decided request, reduced to the record of what was decided and over what.
 * It is not a card: there is nothing left to decide, so the target is dropped,
 * the row is muted, and the state tone in the glyph plus the wording is the
 * only thing it reports. It disappears with the request it belongs to, which
 * the host usually removes as soon as the decision lands.
 */
function PermissionReceipt({ request, decision }: { request: PermissionRequest; decision: ApprovalDecision }) {
  const { t } = useI18n();
  const state: ApprovalState = decision === 'deny' ? 'denied' : 'approved';
  const Icon = ACTION_ICONS[request.action];
  return (
    <div
      data-approval-decision={decision}
      className="flex items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-2xs)] last:border-b-0"
    >
      <StatusIcon tone={approvalTone(state)} size="xs" />
      <span className="shrink-0 text-[var(--color-text-muted)]">
        {t(`permission_dialog.state.${state}`)}
      </span>
      <span className="min-w-0 flex-1 truncate font-mono text-[var(--color-text-disabled)]">{request.description}</span>
      <Icon size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-disabled)]" />
    </div>
  );
}

function PermissionItem({ request, onApprove, onDeny, bulkPending, focusOnMount, registerShortcut, draft, onDraftChange }: {
  request: PermissionRequest;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  bulkPending: boolean;
  focusOnMount: boolean;
  /** Publishes the guarded responder so global shortcuts obey the same locks. */
  registerShortcut: ((respond: (approve: boolean) => void) => void) | undefined;
  draft: ApprovalDraft | undefined;
  onDraftChange: (id: string, draft: ApprovalDraft) => void;
}) {
  const { t } = useI18n();
  const dangerous = request.severity === 'high' || request.action === 'file_delete';
  const [status, setStatus] = useState<ApprovalStatus>('idle');
  /** Which way the user decided, kept so the card can name its own state. */
  const [decision, setDecision] = useState<ApprovalDecision | null>(null);
  const [error, setError] = useState<string>();
  const responding = useRef(false);
  const id = useId();
  const Icon = ACTION_ICONS[request.action];
  const label = t(`permission_dialog.action.${request.action}`);
  const locked = status === 'submitting' || status === 'submitted' || status === 'expired';
  const disabled = locked || bulkPending;
  const state = approvalState(status, decision);

  // The concrete thing being authorised, and the signature of everything the
  // decision is about. A draft taken against different content is void, so a
  // stale confirmation can never carry over to another command or path.
  const target = extractApprovalTarget(request);
  const targetSignature = `${request.action}|${target?.kind ?? ''}|${target?.value ?? ''}|${request.details ?? ''}`;
  const confirmed = draft?.signature === targetSignature && draft.active === 'approve';
  const setConfirmed = useCallback((value: boolean) => {
    onDraftChange(request.id, { signature: targetSignature, active: value ? 'approve' : null });
  }, [onDraftChange, request.id, targetSignature]);

  const extraDetails = request.details && request.details.trim() !== target?.value.trim() ? request.details : undefined;
  const [detailsOpen, setDetailsOpen] = useState(false);

  const respond = useCallback((approve: boolean) => {
    if (locked || responding.current || bulkPending || (approve && dangerous && !confirmed)) return;
    responding.current = true;
    setDecision(approve ? 'approve' : 'deny');
    setStatus('submitting');
    setError(undefined);
    void (async () => {
      try {
        await (approve ? onApprove(request.id) : onDeny(request.id));
        setStatus('submitted');
      } catch (cause) {
        if (isExpiredError(cause)) {
          // Terminal: the request is gone upstream, so the lock stays and the
          // reason is shown instead of a retry that could only fail again.
          setStatus('expired');
          return;
        }
        // The request stays mounted with its command/path intact and its decision
        // intact, so the re-enabled approve button is a retry, not a fresh choice.
        responding.current = false;
        setStatus('error');
        setError(cause instanceof Error ? cause.message : t('common.error'));
      }
    })();
  }, [bulkPending, confirmed, dangerous, locked, onApprove, onDeny, request.id, t]);

  useEffect(() => {
    registerShortcut?.(respond);
    return () => { registerShortcut?.(() => {}); };
  }, [registerShortcut, respond]);

  // Land keyboard focus on the request itself rather than a button, so the
  // shortcuts are live without arming a one-key decision.
  const sectionRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (focusOnMount) sectionRef.current?.focus();
  }, [focusOnMount]);

  // A decided request has nothing left to decide, so the card gives way to a
  // one-line record of the decision. A decision the backend did not accept
  // never reaches this branch: the request keeps its card and its reason.
  if (status === 'submitted' && decision) return <PermissionReceipt request={request} decision={decision} />;

  return (
    <section ref={sectionRef} tabIndex={-1} aria-labelledby={`${id}-title`} aria-busy={disabled} data-approval-status={status} data-approval-state={state} className="space-y-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-3)] last:border-b-0 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]">

      <div className="flex flex-wrap items-center gap-[var(--space-2)] text-[length:var(--text-xs)]">
        <Icon size={14} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
        <span id={`${id}-title`} className="font-medium text-[var(--color-text-primary)]">{label}</span>
        <span className="ms-auto flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)]">
          <StatusIcon tone={dangerous ? 'warning' : 'queued'} size="xs" />
          <span className={dangerous ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}>
            {t(`permission_dialog.risk.${dangerous ? 'high' : request.severity}`)}
          </span>
        </span>
      </div>

      <p className="break-words text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">{request.description}</p>

      {target && (
        <div>
          <span className="text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            {t(`permission_dialog.target.${target.kind}`)}
          </span>
          <pre
            tabIndex={0}
            data-testid={`${id}-target`}
            className={cn(
              'mt-[var(--space-1)] max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border p-[var(--space-2)] font-mono text-[length:var(--text-2xs)]',
              dangerous ? 'border-[var(--color-error)]/40 bg-[var(--color-error-subtle)] text-[var(--color-text-primary)]' : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-secondary)]',
            )}
          >
            {target.value}
          </pre>
        </div>
      )}

      {extraDetails !== undefined && (
        <div>
          <button type="button" data-testid="permission-details-toggle" aria-expanded={detailsOpen} aria-controls={`${id}-details`} onClick={() => setDetailsOpen(value => !value)} className="flex items-center gap-[var(--space-1)] py-[var(--space-1)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]">
            {detailsOpen ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
            {t('permission_dialog.details')}
          </button>
          {detailsOpen && <pre id={`${id}-details`} tabIndex={0} className="mt-[var(--space-1)] max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] p-[var(--space-2)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">{extraDetails}</pre>}
        </div>
      )}

      {dangerous && (
        <label className="flex items-start gap-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={confirmed} disabled={disabled} onChange={event => setConfirmed(event.target.checked)} className="mt-[var(--space-0-5)] accent-[var(--color-error)]" />
          {t('permission_dialog.confirm_risk')}
        </label>
      )}

      {status === 'expired' ? (
        <p role="alert" className="break-words text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
          {t('permission_dialog.expired')}
          <span className="ms-1 text-[var(--color-text-secondary)]">
            {t('permission_dialog.expired_hint')}
          </span>
        </p>
      ) : error && (
        <p role="alert" className="break-words text-[length:var(--text-xs)] text-[var(--color-error)]">
          {error}
          <span className="ms-1 text-[var(--color-text-muted)]">
            {t('permission_dialog.retry_hint')}
          </span>
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-[var(--space-2)]">
        <ApprovalChip state={state} />
        <span className="flex flex-wrap gap-[var(--space-2)]">
          <Button type="button" variant="outline" size="sm" disabled={disabled} aria-keyshortcuts="Control+Shift+Backspace Meta+Shift+Backspace" onClick={() => respond(false)} icon={<X size={12} aria-hidden="true" />}>
            {t('permission_dialog.deny')}
          </Button>
          <Button type="button" variant={dangerous ? 'destructive' : 'secondary'} size="sm" disabled={disabled || (dangerous && !confirmed)} aria-keyshortcuts="Control+Enter Meta+Enter" onClick={() => respond(true)} icon={<Check size={12} aria-hidden="true" />}>
            {t(dangerous ? 'permission_dialog.approve_risk' : 'permission_dialog.approve')}
          </Button>
        </span>
      </div>
    </section>
  );
}

export function FloatingPermissionDialog({ requests, onApprove, onDeny, onApproveAll }: FloatingPermissionDialogProps) {
  const { t } = useI18n();
  const titleId = useId();
  const [minimized, setMinimized] = useState(false);
  const [bulkPending, setBulkPending] = useState(false);
  const [error, setError] = useState<string>();
  const responding = useRef(false);
  const canApproveAll = requests.length > 1 && requests.every(request => request.severity === 'low' && request.action !== 'file_delete');

  // The mode in force is the backend's, not the dialog's: a card arriving means
  // the mode let something through, and the chip says which mode did it. A mode
  // the backend has not reported is rendered as "not reported" rather than
  // assumed to be the safest one.
  const permissionMode = useWorkspaceStore(state => state.permissionMode);
  const modeTone = permissionMode ? MODE_TONE[permissionMode] : 'unknown';

  // Drafts live here, above the cards. A request whose content changes is given a
  // new card key, so a decision kept inside the card would be thrown away by the
  // next streaming update; from here it survives the remount.
  const [drafts, setDrafts] = useState<Record<string, ApprovalDraft>>({});
  const updateDraft = useCallback((id: string, draft: ApprovalDraft) => {
    setDrafts(previous => ({ ...previous, [id]: draft }));
  }, []);

  // A request that is gone has no decision left to keep.
  useEffect(() => {
    const live = new Set(requests.map(request => request.id));
    setDrafts(previous => {
      const kept = Object.entries(previous).filter(([id]) => live.has(id));
      return kept.length === Object.keys(previous).length ? previous : Object.fromEntries(kept);
    });
  }, [requests]);

  const approveAll = useCallback(async () => {
    if (responding.current || !canApproveAll) return;
    responding.current = true;
    setBulkPending(true);
    setError(undefined);
    try {
      await onApproveAll();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t('common.error'));
    } finally {
      responding.current = false;
      setBulkPending(false);
    }
  }, [canApproveAll, onApproveAll, t]);

  const hasRequests = requests.length > 0;
  const shortcutTarget = useRef<((approve: boolean) => void) | null>(null);
  const setShortcutTarget = useCallback((respond: (approve: boolean) => void) => {
    shortcutTarget.current = respond;
  }, []);

  useEffect(() => {
    if (!hasRequests || minimized) {
      shortcutTarget.current = null;
      return undefined;
    }
    const isTyping = (node: EventTarget | null) => node instanceof HTMLElement
      && (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA' || node.isContentEditable);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || (!event.metaKey && !event.ctrlKey)) return;
      if (event.isComposing || isTyping(event.target)) return;
      const approve = event.key === 'Enter';
      const deny = event.key === 'Backspace' && event.shiftKey;
      if (!approve && !deny) return;
      // Route through the item's own responder so the high-risk confirmation
      // and the in-flight lock apply to keyboard decisions too.
      const respond = shortcutTarget.current;
      if (!respond) return;
      event.preventDefault();
      respond(approve);
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [hasRequests, minimized]);

  if (requests.length === 0) return null;

  return (
    <aside aria-labelledby={titleId} data-approval-mode={permissionMode ?? 'unreported'} className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-lg overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-md)]">
      <div className="flex flex-wrap items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-[var(--space-3)] py-[var(--space-2)]">
        <Shield size={14} aria-hidden="true" className="text-[var(--color-text-muted)]" />
        <h2 id={titleId} className="text-[length:var(--text-xs)] font-semibold text-[var(--color-text-primary)]">{t('permission_dialog.title')} ({requests.length})</h2>
        {/* The three modes that can produce a card, one tone and one container
            apart, so "why did this ask" is answerable without opening settings.
            An unreported mode is a dashed unknown chip, never the safe default. */}
        <span
          data-approval-mode-state={permissionMode ?? 'unreported'}
          className={cn(
            'flex items-center gap-[var(--space-1)] rounded-[var(--radius-sm)] border px-[var(--space-1-5)] py-[var(--space-0-5)] text-[length:var(--text-2xs)]',
            permissionMode
              ? modeTone === 'warning'
                ? 'border-[var(--color-warning)]/40 bg-[var(--color-warning-subtle)] text-[var(--color-warning)]'
                : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] text-[var(--color-text-muted)]'
              : 'border-dashed border-[var(--color-unknown)]/40 text-[var(--color-unknown)]',
          )}
        >
          <StatusIcon tone={modeTone} size="xs" />
          <span>{permissionMode
            ? t(`permission_dialog.mode.${permissionMode}`)
            : t('permission_dialog.mode.unreported')}</span>
        </span>
        <span className="ms-auto hidden text-[length:var(--text-2xs)] text-[var(--color-text-muted)] sm:inline">
          {t('permission_dialog.keyboard_hint')}
        </span>
        <Button type="button" variant="ghost" size="sm" aria-expanded={!minimized} aria-controls={`${titleId}-requests`} onClick={() => setMinimized(value => !value)}>
          {t(minimized ? 'tool_call.expand_all' : 'tool_call.collapse_all')}
        </Button>
      </div>
      <div id={`${titleId}-requests`} hidden={minimized} className="max-h-[min(65dvh,28rem)] overflow-y-auto">
        {requests.map((request, index) => (
          <PermissionItem
            key={JSON.stringify([request.id, request.action, request.severity, request.description, request.details, request.command, request.path, request.url, request.tool])}
            request={request}
            onApprove={onApprove}
            onDeny={onDeny}
            bulkPending={bulkPending}
            focusOnMount={index === 0}
            registerShortcut={index === 0 ? setShortcutTarget : undefined}
            draft={drafts[request.id]}
            onDraftChange={updateDraft}
          />
        ))}
        {error && <p role="alert" className="px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-error)]">{error}</p>}
        {canApproveAll && (
          <div className="flex justify-end border-t border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)]">
            <Button type="button" variant="outline" size="sm" disabled={bulkPending} onClick={() => void approveAll()}>
              {t('permission_dialog.approve_all')}
            </Button>
          </div>
        )}
      </div>
    </aside>
  );
}
