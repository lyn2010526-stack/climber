import { useCallback, useState } from 'react';
import { ChevronRight, Wrench } from 'lucide-react';
import { api } from '../../../../api';
import { useI18n } from '../../../../i18n';
import {
  PanelEmpty, PanelError, PanelLoading, resolveReportedCount, useAsyncData, useReportedCount, type ReportCount,
} from '../PanelState';
import { cn } from '../../../../lib/utils';
import { normalizeToolStatus, resolveToolStatus } from '../../../agent/toolCallStatus';

interface ToolCallEntry {
  id: string;
  name: string | undefined;
  arguments: string;
  result: string | null;
  status: string | boolean | null | undefined;
  error: string | null;
  approval: string | null;
  retryCount: number | undefined;
}

function messageField(message: unknown, key: string): unknown {
  return typeof message === 'object' && message !== null ? (message as Record<string, unknown>)[key] : undefined;
}

function nestedField(message: unknown, parent: string, key: string): unknown {
  return messageField(messageField(message, parent), key);
}

export function ActivitySection({
  sessionId,
  onCount,
}: { sessionId: string | null; onCount?: ReportCount } = { sessionId: null }) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState<string | null>(null);
  const { data, loading, error, reload } = useAsyncData<ToolCallEntry[]>(async () => {
    if (!sessionId) return [];
    const messages = await api.getSessionMessages(sessionId);
    const results = new Map(
      messages
        .filter((message) => message.role === 'tool' && message.tool_call_id)
        .map((message) => [message.tool_call_id, message]),
    );
    return messages.flatMap((message) =>
      (message.tool_calls ?? []).map((call, index) => {
        const result = results.get(call.id);
        const rawArguments = call.function?.arguments ?? call.arguments;
        let args = typeof rawArguments === 'string' ? rawArguments : JSON.stringify(rawArguments, null, 2);
        try {
          if (typeof rawArguments === 'string') args = JSON.stringify(JSON.parse(rawArguments), null, 2);
        } catch {
          // Preserve unparseable input so the inspector reflects the actual call.
        }
        const rawStatus = messageField(message, 'status') ?? nestedField(message, 'metadata', 'status')
          ?? messageField(result, 'status') ?? nestedField(result, 'metadata', 'status');
        const rawError = messageField(result, 'error') ?? nestedField(result, 'metadata', 'error');
        const rawApproval = messageField(message, 'approval') ?? messageField(message, 'approval_status') ?? messageField(message, 'block_reason');
        const retryCount = messageField(message, 'retry_count') ?? messageField(message, 'retryCount') ?? nestedField(message, 'metadata', 'retryCount');
        return {
          id: call.id || `${message.id}-${index}`,
          name: call.function?.name || call.name,
          arguments: args,
          result: result?.content ?? null,
          status: typeof rawStatus === 'string' || typeof rawStatus === 'boolean' ? rawStatus : undefined,
          error: typeof rawError === 'string' ? rawError : null,
          approval: typeof rawApproval === 'string' ? rawApproval : null,
          retryCount: typeof retryCount === 'number' && Number.isFinite(retryCount) ? retryCount : undefined,
        };
      }),
    );
  }, [sessionId]);

  // Without a session there is nothing to count: the panel is unpopulated
  // rather than empty, so the heading drops its tally.
  useReportedCount(sessionId ? resolveReportedCount({ data, loading, error }) : undefined, onCount);

  // Arguments and results stay unmounted until the call is opened, so opening
  // the group reads one list and never pays for every payload up front.
  const toggle = useCallback((id: string) => {
    setExpanded((current) => (current === id ? null : id));
  }, []);

  if (loading) return <PanelLoading rows={2} />;
  if (error) return <PanelError onRetry={reload} />;
  if (!data || data.length === 0) {
    return (
      <PanelEmpty
        icon={Wrench}
        title={t('right_panel.states.empty_tools')}
        hint={t('right_panel.states.empty_tools_hint')}
      />
    );
  }

  // SessionMessage carries no execution status; a response alone proves neither success nor failure.
  return (
    <ul>
      {data.map((call) => {
        const open = expanded === call.id;
        const descriptor = resolveToolStatus(normalizeToolStatus(call.status), t);
        const StatusIcon = descriptor.icon;
        const summary = call.error ?? call.approval ?? call.result;
        return (
          <li key={call.id} className="border-b border-[var(--color-border-subtle)] last:border-b-0">
            <button
              type="button"
              aria-expanded={open}
              aria-controls={`tool-detail-${call.id}`}
              aria-label={call.name || t('right_panel.summary.none')}
              onClick={() => toggle(call.id)}
              className="flex w-full items-center gap-1.5 rounded-[var(--radius-md)] py-1.5 text-left text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)]"
            >
              <ChevronRight
                size={11}
                aria-hidden="true"
                className={cn(
                  'shrink-0 text-[var(--color-text-muted)] transition-transform duration-150',
                  open && 'rotate-90',
                )}
              />
              <Wrench size={11} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
              <span className="min-w-0 flex-1 truncate">{call.name || t('right_panel.summary.none')}</span>
              <StatusIcon size={11} aria-hidden="true" className={cn('shrink-0', descriptor.className, descriptor.spin && 'animate-spin motion-reduce:animate-none')} />
              <span className={cn('shrink-0 text-[10px]', descriptor.className)}>{descriptor.label}</span>
              {call.retryCount !== undefined && call.retryCount > 0 && (
                <span className="shrink-0 text-[10px] text-[var(--color-text-muted)]">retry {call.retryCount}</span>
              )}
            </button>
            {!open && summary && (
              <p className={cn('truncate pb-1 pl-6 text-[10px]', call.error ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]')}>
                {summary}
              </p>
            )}
            {open && (
              <dl
                id={`tool-detail-${call.id}`}
                className="space-y-1 pb-2 pl-6 text-[11px] text-[var(--color-text-muted)]"
              >
                <dt className="text-[10px] font-semibold uppercase tracking-[0.06em]">{t('tool_call.arguments')}</dt>
                <dd>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono">
                    {call.arguments ?? t('right_panel.summary.none')}
                  </pre>
                </dd>
                {call.approval && <><dt className="text-[10px] font-semibold uppercase tracking-[0.06em]">approval</dt><dd>{call.approval}</dd></>}
                {call.error && <><dt className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[var(--color-error)]">{t('tool_call.error_detail')}</dt><dd className="text-[var(--color-error)]">{call.error}</dd></>}
                <dt className="text-[10px] font-semibold uppercase tracking-[0.06em]">{t('tool_call.result')}</dt>
                <dd>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono">
                    {call.result ?? t('right_panel.summary.none')}
                  </pre>
                </dd>
              </dl>
            )}
          </li>
        );
      })}
    </ul>
  );
}
