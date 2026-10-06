import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useI18n } from '../../i18n';
import { api } from '../../api';
import { ScrollReveal } from '../motion/ScrollReveal';
import '../workspace/codex-suite.css';

interface ScopeSummary {
  scope: string;
  abstract: string;
  overview: string;
}

interface SidecarRecord {
  id: string;
  level: number;
  scope: string;
  body: string;
  generated_by: string;
  updated_at: string | null;
}

type MemoryPanelState =
  | { status: 'loading' }
  | { status: 'empty' }
  | { status: 'error' }
  | { status: 'ready'; scopes: ScopeSummary[] };

function formatTime(value: string | null): string | null {
  if (!value) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) ? new Date(time).toLocaleString() : null;
}

function levelLabel(level: number, t: (key: string, options?: Record<string, unknown>) => string): string {
  if (level === 0) return t('anchored.memory.level_l0', { defaultValue: 'L0 摘要' });
  if (level === 1) return t('anchored.memory.level_l1', { defaultValue: 'L1 概览' });
  return t('anchored.memory.level_l2', { defaultValue: 'L2 详情' });
}

interface ArchiveSummary {
  id: string;
  session_id: string;
  title: string | null;
  one_line_summary: string;
  message_count: number;
  archive_status: string;
  created_at: string | null;
}

interface ArchiveDetail extends ArchiveSummary {
  messages: Array<{ role: string; content: string }>;
  memory_diff: Record<string, unknown> | null;
}

/**
 * 会话归档列表：GET /memory/archives?session_id=…，点击单条按需加载
 * GET /memory/archives/{id} 的消息与 memory_diff。
 */
function SessionArchives({ sessionId }: { sessionId: string }) {
  const { t } = useI18n();
  const [archives, setArchives] = useState<ArchiveSummary[] | null>(null);
  const [error, setError] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ArchiveDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setArchives(null);
    setError(false);
    api.listMemoryArchives(sessionId)
      .then((payload) => {
        if (active) setArchives(Array.isArray(payload?.archives) ? payload.archives : []);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  const toggle = useCallback((archiveId: string) => {
    if (openId === archiveId) {
      setOpenId(null);
      setDetail(null);
      return;
    }
    setOpenId(archiveId);
    setDetail(null);
    setDetailLoading(true);
    api.getMemoryArchive(archiveId)
      .then((payload) => setDetail(payload as ArchiveDetail))
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [openId]);

  if (error) {
    return (
      <p role="alert" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('anchored.memory.archives_unavailable', { defaultValue: '会话归档暂不可用' })}
      </p>
    );
  }
  if (archives === null) {
    return (
      <p role="status" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('anchored.memory.archives_loading', { defaultValue: '正在读取会话归档…' })}
      </p>
    );
  }
  if (archives.length === 0) return null;

  return (
    <div className="space-y-[var(--space-1)]" data-testid="anchored-memory-archives">
      <p className="text-[length:var(--text-2xs)] font-medium text-[var(--color-text-muted)]">
        {t('anchored.memory.archives_title', { defaultValue: '会话归档' })}
      </p>
      {archives.map((archive) => {
        const open = openId === archive.id;
        const created = formatTime(archive.created_at);
        return (
          <div key={archive.id} className="cx-subcard overflow-hidden">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => toggle(archive.id)}
              className="flex w-full items-center gap-[var(--space-1-5)] px-[var(--space-1-5)] py-[var(--space-1)] text-left transition-colors duration-150 motion-reduce:transition-none hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
            >
              {open ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
              <span className="min-w-0 flex-1 truncate text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                {archive.title || archive.one_line_summary || archive.id}
              </span>
              {created && <time className="cx-mono shrink-0 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{created}</time>}
            </button>
            {open && (
              <div className="space-y-[var(--space-1)] border-t border-[var(--color-border-subtle)] px-[var(--space-1-5)] py-[var(--space-1-5)]">
                <p className="whitespace-pre-wrap break-words text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">
                  {archive.one_line_summary}
                </p>
                {detailLoading ? (
                  <p role="status" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                    {t('anchored.memory.details_loading', { defaultValue: '正在加载明细…' })}
                  </p>
                ) : detail && (
                  <ul className="max-h-48 space-y-[var(--space-1)] overflow-y-auto">
                    {detail.messages.map((message, index) => (
                      <li key={index} className="rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-1-5)] py-[var(--space-1)]">
                        <p className="cx-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{message.role}</p>
                        <p className="whitespace-pre-wrap break-words text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">{message.content}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * 记忆归档面板：L0 摘要条目列表（context-bundle）+ 点击展开 L1 overview，
 * L2 详情按需加载（sidecar 端点）。隐私门槛文案走 anchored.memory.* 回退。
 */
export function MemoryArchivePanel({ sessionId }: { sessionId?: string | null }) {
  const { t } = useI18n();
  const [state, setState] = useState<MemoryPanelState>({ status: 'loading' });
  const [openScope, setOpenScope] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, SidecarRecord[]>>({});
  const [detailsLoading, setDetailsLoading] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setState({ status: 'loading' });
    api.getMemoryContextBundle({ sessionId: sessionId ?? undefined })
      .then((bundle) => {
        if (!active) return;
        const scopes = Array.isArray(bundle?.scopes) ? bundle.scopes.filter((entry) => typeof entry?.scope === 'string') : [];
        setState(scopes.length > 0 ? { status: 'ready', scopes } : { status: 'empty' });
      })
      .catch(() => {
        if (active) setState({ status: 'error' });
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  const toggleScope = useCallback((scope: string) => {
    setOpenScope((current) => (current === scope ? null : scope));
  }, []);

  const loadDetails = useCallback((scope: string) => {
    setDetailsLoading(scope);
    api.listMemorySidecars(scope)
      .then((payload) => {
        setDetails((current) => ({ ...current, [scope]: payload?.records ?? [] }));
      })
      .catch(() => {
        setDetails((current) => ({ ...current, [scope]: [] }));
      })
      .finally(() => {
        setDetailsLoading(null);
      });
  }, []);

  if (state.status === 'loading') {
    return (
      <p role="status" data-testid="anchored-memory-panel" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('anchored.memory.loading', { defaultValue: '正在读取记忆归档…' })}
      </p>
    );
  }

  if (state.status === 'error') {
    return (
      <p role="alert" data-testid="anchored-memory-panel" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('anchored.memory.unavailable', { defaultValue: '记忆归档暂不可用' })}
      </p>
    );
  }

  if (state.status === 'empty') {
    return (
      <div data-testid="anchored-memory-panel" className="space-y-[var(--space-1)]">
        <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
          {t('anchored.memory.empty', { defaultValue: '暂无已归档记忆' })}
        </p>
        <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
          {t('anchored.memory.privacy_note', { defaultValue: '记忆仅在会话归档后生成，归档前不会上传任何内容' })}
        </p>
        {sessionId && <SessionArchives sessionId={sessionId} />}
      </div>
    );
  }

  return (
    <div data-testid="anchored-memory-panel" className="space-y-[var(--space-2)]">
      <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('anchored.memory.privacy_note', { defaultValue: '记忆仅在会话归档后生成，归档前不会上传任何内容' })}
      </p>
      <ScrollReveal stagger={60} className="space-y-[var(--space-1)]" testId="anchored-memory-scopes">
        {state.scopes.map((entry) => {
          const open = openScope === entry.scope;
          const records = details[entry.scope];
          return (
            <div key={entry.scope} data-testid={`anchored-memory-scope-${entry.scope}`} className="cx-subcard overflow-hidden">
              <button
                type="button"
                aria-expanded={open}
                onClick={() => {
                  toggleScope(entry.scope);
                  if (!open && records === undefined) loadDetails(entry.scope);
                }}
                className="flex w-full items-center gap-[var(--space-1-5)] px-[var(--space-1-5)] py-[var(--space-1)] text-left transition-colors duration-150 motion-reduce:transition-none hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
              >
                {open ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
                <span className="cx-mono min-w-0 flex-1 truncate text-[length:var(--text-xs)] text-[var(--color-text-primary)]">
                  {entry.scope}
                </span>
                <span className="cx-pill cx-mono shrink-0">
                  L0
                </span>
              </button>
              {!open && entry.abstract && (
                <p className="truncate px-[var(--space-1-5)] pb-[var(--space-1)] text-[length:var(--text-xs)] leading-[var(--leading-normal)] text-[var(--color-text-muted)]">
                  {entry.abstract}
                </p>
              )}
              {open && (
                <div className="space-y-[var(--space-1-5)] border-t border-[var(--color-border-subtle)] px-[var(--space-1-5)] py-[var(--space-1-5)]">
                  <p className="whitespace-pre-wrap break-words text-[length:var(--text-2xs)] leading-[var(--leading-normal)] text-[var(--color-text-secondary)]">
                    {entry.abstract}
                  </p>
                  {entry.overview && (
                    <p className="whitespace-pre-wrap break-words text-[length:var(--text-2xs)] leading-[var(--leading-normal)] text-[var(--color-text-muted)]">
                      {entry.overview}
                    </p>
                  )}
                  <div className="space-y-[var(--space-1)]">
                    <p className="text-[length:var(--text-2xs)] font-medium text-[var(--color-text-muted)]">
                      {t('anchored.memory.details_title', { defaultValue: '工作明细' })}
                    </p>
                    {records === undefined || detailsLoading === entry.scope ? (
                      <p role="status" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                        {t('anchored.memory.details_loading', { defaultValue: '正在加载明细…' })}
                      </p>
                    ) : records.length === 0 ? (
                      <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                        {t('anchored.memory.details_empty', { defaultValue: '无明细记录' })}
                      </p>
                    ) : (
                      <ul className="space-y-[var(--space-1)]">
                        {records.map((record) => {
                          const updated = formatTime(record.updated_at);
                          return (
                            <li key={record.id} className="rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-1-5)] py-[var(--space-1)]">
                              <p className="flex items-center gap-[var(--space-1-5)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                                <span className="cx-pill cx-mono">{levelLabel(record.level, t)}</span>
                                <span className="cx-mono">{record.generated_by}</span>
                                {updated && <time className="cx-mono ml-auto shrink-0">{updated}</time>}
                              </p>
                              <p className="mt-[var(--space-0-5)] max-h-32 overflow-y-auto whitespace-pre-wrap break-words text-[length:var(--text-2xs)] leading-[var(--leading-normal)] text-[var(--color-text-secondary)]">
                                {record.body}
                              </p>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </ScrollReveal>
      {sessionId && <SessionArchives sessionId={sessionId} />}
    </div>
  );
}

export default MemoryArchivePanel;
