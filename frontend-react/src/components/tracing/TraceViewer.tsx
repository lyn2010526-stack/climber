import React, { useEffect, useState, useCallback, useRef, useId } from 'react';
import { Activity, ListTree, RefreshCw, ChevronRight, ChevronDown } from 'lucide-react';
import { api } from '../../api';
import { useI18n, type TFunction } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatDuration } from '../../lib/duration';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';
import { ToolCodeBlock, ToolDisclosure } from '../agent/ToolDisclosure';
import { normalizeToolStatus, resolveToolStatus } from '../agent/toolCallStatus';

interface TraceSpan {
  id: string;
  trace_id: string;
  parent_id: string | null;
  kind: string;
  name: string;
  status: string;
  duration_ms: number;
  tokens_used: number;
  model: string | null;
  tool_name: string | null;
  error: string | null;
  started_at: string;
  metadata: string | null;
}

interface TraceStats {
  trace_id: string;
  total_spans: number;
  total_duration_ms: number;
  total_tokens: number;
  error_count: number;
  llm_calls: number;
  tool_calls: number;
}

interface TraceViewerProps {
  traceId?: string;
}

/** One indent step of the span tree, in the shared spacing scale. */
const INDENT_STEP = 'var(--space-4)';

/**
 * Span kind to the two roles a span is read through: the kind badge is a
 * categorical fact, so it takes the neutral information tone rather than a
 * status one. `llm_call` and `tool_call` are the only two kinds this view
 * names, and everything else stays on the quiet rung.
 */
const KIND_TONE: Record<string, StatusTone | undefined> = {
  llm_call: 'info',
  tool_call: 'warning',
};

/**
 * One trace span. Lives at module scope so its disclosure state survives
 * parent re-renders, and renders status through the shared tool-call
 * vocabulary so a span and a tool call never disagree about a state.
 *
 * The three facts on a collapsed row are separated by role: status is a semantic
 * outcome and rides `StatusIcon`, the duration and the token count are
 * measurements and take the syntax-number token in a monospace face so the
 * column of digits lines up down the tree, and the timeline itself is the
 * indent rule, which is a border and nothing else.
 */
function SpanRow({ span, depth, t }: { span: TraceSpan; depth: number; t: TFunction }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const descriptor = resolveToolStatus(normalizeToolStatus(span.status), t);
  const kindTone = KIND_TONE[span.kind];
  let metadata: string | undefined;
  if (span.metadata) {
    try {
      metadata = JSON.stringify(JSON.parse(span.metadata), null, 2);
    } catch {
      metadata = span.metadata;
    }
  }

  return (
    <div style={{ marginInlineStart: `calc(${INDENT_STEP} * ${depth})` }} className="border-s border-[var(--color-border-subtle)] ps-[var(--space-2)] py-[var(--space-1)]">
      <button type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(value => !value)}
        className="flex w-full flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)] break-all text-start text-[length:var(--text-xs)] transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
      >
        {open
          ? <ChevronDown size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
          : <ChevronRight size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />}
        <span className={cn(
          'shrink-0 font-mono text-[length:var(--text-2xs)]',
          kindTone ? 'text-[var(--color-info)]' : 'text-[var(--color-text-muted)]',
        )}>[{span.kind}]</span>
        <span className="font-mono text-[var(--color-text-primary)]">{span.name}</span>
        {span.tool_name && <span className="font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{span.tool_name}</span>}
        <StatusIcon tone={descriptor.tone} size="xs" spin={descriptor.spin} className="shrink-0" />
        <span className={descriptor.className}>{descriptor.label}</span>
        <span className="font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-syntax-number)]">{formatDuration(span.duration_ms, 'ms')}</span>
        {span.tokens_used > 0 && <span className="font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-syntax-number)]">{span.tokens_used}t</span>}
        {span.model && <span className="font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{span.model}</span>}
      </button>
      {open && (
        <div id={panelId} className="mt-[var(--space-1)] space-y-[var(--space-1-5)]">
          <dl className="grid grid-cols-[auto_1fr] gap-x-[var(--space-2)] gap-y-[var(--space-0-5)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
            <dt>{t('common.id')}</dt>
            <dd className="min-w-0 break-all font-mono text-[var(--color-syntax-string)]">{span.id}</dd>
            <dt>{t('common.time')}</dt>
            <dd className="min-w-0 break-all font-mono text-[var(--color-syntax-string)]">{span.started_at}</dd>
          </dl>
          {span.error && (
            <div>
              <span className="flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-error)]">
                <StatusIcon tone="error" size="xs" />
                {t('tool_call.error_detail')}
              </span>
              <ToolCodeBlock tone="error" label={t('tool_call.error_detail')}>{span.error}</ToolCodeBlock>
            </div>
          )}
          {metadata !== undefined && (
            <ToolDisclosure title={t('tool_call.arguments')}>
              <ToolCodeBlock label={t('tool_call.arguments')}>{metadata}</ToolCodeBlock>
            </ToolDisclosure>
          )}
        </div>
      )}
    </div>
  );
}

export default function TraceViewer({ traceId }: TraceViewerProps) {
  const { t } = useI18n();
  const [traces, setTraces] = useState<{ id: string; kind: string; name: string; started_at: string }[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(traceId || null);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [stats, setStats] = useState<TraceStats | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const detailRequest = useRef(0);

  const fetchTraces = useCallback(async () => {
    setListLoading(true);
    setListError(false);
    try {
      const data = await api.listTraces();
        setTraces(data);
    } catch {
      setListError(true);
    }
    setListLoading(false);
  }, []);

  const fetchTrace = useCallback(async (tid: string) => {
    const request = ++detailRequest.current;
    setDetailLoading(true);
    setDetailError(false);
    setSpans([]);
    setStats(null);
    try {
      const data = await api.getTrace(tid);
      if (request !== detailRequest.current) return;
        setSpans(data.spans || []);
        setStats(data.stats || null);
    } catch {
      if (request !== detailRequest.current) return;
      setDetailError(true);
    }
    if (request === detailRequest.current) setDetailLoading(false);
  }, []);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  useEffect(() => {
    setSelectedTrace(traceId || null);
  }, [traceId]);

  useEffect(() => {
    if (selectedTrace) {
      fetchTrace(selectedTrace);
    } else {
      setSpans([]);
      setStats(null);
      setDetailLoading(false);
      setDetailError(false);
    }
    // Invalidate any request still in flight when the selection moves or the
    // view goes away, so a late response cannot repaint a trace that is no
    // longer the one on screen.
    const issued = detailRequest.current;
    return () => { detailRequest.current = issued + 1; };
  }, [selectedTrace, fetchTrace]);

  const renderSpanTree = (spanList: TraceSpan[]) => {
    const rootSpans = spanList.filter((s) => !s.parent_id);
    const childMap: Record<string, TraceSpan[]> = {};
    spanList.forEach((s) => {
      if (s.parent_id) {
        if (!childMap[s.parent_id]) childMap[s.parent_id] = [];
        childMap[s.parent_id]!.push(s);
      }
    });

    const renderSpan = (span: TraceSpan, depth: number): React.ReactNode => {
      const children = childMap[span.id] || [];
      return (
        <React.Fragment key={span.id}>
          <SpanRow span={span} depth={depth} t={t} />
          {children.map((child) => renderSpan(child, depth + 1))}
        </React.Fragment>
      );
    };

    return rootSpans.map((s) => renderSpan(s, 0));
  };

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col gap-[var(--space-3)] bg-[var(--color-bg-surface-1)] p-[var(--space-3)] text-[var(--color-text-primary)] md:flex-row">
      <div className="max-h-56 shrink-0 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--color-border-default)] md:max-h-none md:w-60">
        <div className="sticky top-0 flex items-center justify-between border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-[var(--space-3)] py-[var(--space-1)]">
           <h3 className="flex items-center gap-[var(--space-2)] text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]"><Activity size={14} aria-hidden="true" />{t('tracing.title')}</h3>
          <button type="button" onClick={fetchTraces} disabled={listLoading} aria-label={t('tracing.refresh_list_aria')} className="inline-flex min-h-[var(--control-height-sm)] items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] px-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50 motion-reduce:transition-none">
            <RefreshCw size={13} aria-hidden="true" className={cn(listLoading && 'animate-spin motion-reduce:animate-none')} />{t('common.refresh')}
          </button>
        </div>
        {listLoading && <div role="status" className="flex items-center gap-[var(--space-2)] p-[var(--space-3)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]"><StatusIcon tone="loading" size="sm" />{t('tracing.loading_list')}</div>}
        {listError && (
          <div role="alert" className="flex flex-wrap items-center gap-[var(--space-2)] p-[var(--space-3)] text-[length:var(--text-xs)] text-[var(--color-error)]">
            <StatusIcon tone="error" size="sm" />
            {t('tracing.errors.list')}
            <button type="button" onClick={fetchTraces} className="min-h-[var(--control-height-sm)] underline underline-offset-2">{t('tracing.retry_list')}</button>
          </div>
        )}
         {!listLoading && !listError && traces.length === 0 && (
           <div role="status" className="p-[var(--space-4)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
             <StatusIcon tone="unknown" size="lg" className="mb-[var(--space-2)]" />
             {t('tracing.empty_title')}
             <p className="mt-[var(--space-1)]">{t('tracing.empty_hint')}</p>
           </div>
         )}
        {traces.map((trace) => (
          <button type="button"
            key={trace.id}
            aria-pressed={selectedTrace === trace.id}
            onClick={() => setSelectedTrace(trace.id)}
            className={cn(
              // The start border is the selection rail: transparent until the
              // trace is the one the detail pane describes, so the padding never
              // shifts and no row reflows when the selection moves.
              'block w-full border-b border-s-2 border-b-[var(--color-border-subtle)] p-[var(--space-3)] text-start transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
              selectedTrace === trace.id
                ? 'border-s-[var(--color-border-accent)] bg-[var(--color-bg-surface-2)]'
                : 'border-s-transparent',
            )}
          >
            {/* The selected trace is the one the detail pane describes, so it
                also takes the accent border. Name is prose, the id and the
                timestamp are facts and stay monospace. */}
            <div className={cn('truncate text-[length:var(--text-sm)] font-medium', selectedTrace === trace.id ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]')}>
              {trace.name || trace.id}
            </div>
            <div className="mt-[var(--space-1)] flex items-center gap-[var(--space-1-5)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
              <span className="text-[var(--color-info)]">[{trace.kind}]</span>
              <span className="tabular-nums">{trace.started_at?.slice(0, 19)}</span>
            </div>
          </button>
        ))}
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-[var(--space-3)] overflow-y-auto">
        <div className="flex min-h-10 items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] text-[length:var(--text-xs)]">
          <ListTree size={14} aria-hidden="true" className="text-[var(--color-text-muted)]" />
          <h3 className="shrink-0 font-medium text-[var(--color-text-primary)]">{t('tracing.detail_title')}</h3>
          <span className="min-w-0 truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]" title={selectedTrace || undefined}>{selectedTrace || t('tracing.none_selected')}</span>
          {selectedTrace && (
            <button type="button" aria-label={t('tracing.refresh_detail_aria')} disabled={detailLoading} onClick={() => fetchTrace(selectedTrace)} className="ms-auto flex size-[var(--control-height-sm)] shrink-0 items-center justify-center rounded-[var(--radius-sm)] transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-50">
              <RefreshCw size={14} aria-hidden="true" className={cn(detailLoading && 'animate-spin motion-reduce:animate-none')} />
            </button>
          )}
        </div>
        {detailError && (
          <div role="alert" className="flex flex-wrap items-center gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-[var(--space-3)] text-[length:var(--text-xs)] text-[var(--color-error)]">
            <StatusIcon tone="error" size="sm" />
            {t('tracing.errors.detail')}
            <button type="button" onClick={() => selectedTrace && fetchTrace(selectedTrace)} className="min-h-[var(--control-height-sm)] underline underline-offset-2">{t('tracing.retry_detail')}</button>
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-2 gap-[var(--space-2)] sm:grid-cols-3 xl:grid-cols-6">
            <StatTile label={t('tracing.stat.spans')} value={String(stats.total_spans)} tone="queued" measure />
            <StatTile label={t('tracing.stat.duration')} value={formatDuration(stats.total_duration_ms, 'ms')} tone="info" measure />
            <StatTile label={t('tracing.stat.tokens')} value={String(stats.total_tokens)} tone="queued" measure />
            <StatTile label={t('tracing.stat.llm_calls')} value={String(stats.llm_calls)} tone="info" />
            <StatTile label={t('tracing.stat.tool_calls')} value={String(stats.tool_calls)} tone="warning" />
            <StatTile label={t('tracing.stat.errors')} value={String(stats.error_count)} tone="error" />
          </div>
        )}

        <div className="min-h-32 flex-1 overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border-default)] p-[var(--space-3)]">
          {detailLoading && <div role="status" className="flex items-center gap-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]"><StatusIcon tone="loading" size="sm" />{t('tracing.loading_detail')}</div>}
           {!detailLoading && !detailError && spans.length === 0 && selectedTrace && <div role="status" className="flex items-center gap-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]"><StatusIcon tone="unknown" size="sm" />{t('tracing.empty_spans')}</div>}
           {!selectedTrace && (
             <div className="py-[var(--space-6)] text-center text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
               <StatusIcon tone="unknown" size="lg" className="mx-auto mb-[var(--space-3)]" />
               {t('tracing.select_hint')}
             </div>
           )}
          {spans.length > 0 && renderSpanTree(spans)}
        </div>
      </div>
    </div>
  );
}

/**
 * One trace statistic. A measurement is a number in a monospace face, so the
 * glyph beside it carries the state (waiting, model time, a fault) and the
 * digits stay comparable down the row.
 */
function StatTile({ label, value, tone, measure }: { label: string; value: string; tone: StatusTone; measure?: boolean }) {
  return (
    <div className="flex items-center gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-[var(--space-3)] py-[var(--space-2)]">
      <StatusIcon tone={tone} size="sm" />
      <div className="min-w-0">
        <div className={cn('truncate text-[length:var(--text-base)] font-semibold', measure ? 'font-mono tabular-nums text-[var(--color-syntax-number)]' : 'font-sans text-[var(--color-text-primary)]')}>{value}</div>
        <div className="truncate text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{label}</div>
      </div>
    </div>
  );
}
