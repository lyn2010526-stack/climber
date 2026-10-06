import { FileDiff, FolderTree } from 'lucide-react';
import { api } from '../../../../api';
import { useI18n } from '../../../../i18n';
import { DiffPanel } from '../../../code/DiffPanel';
import { PanelEmpty, PanelError, PanelLoading, SectionHeader, useAsyncData } from '../PanelState';

function extractLatestDiff(messages: Array<Record<string, unknown>>): string | null {
  const diffs = messages.filter(
    (message) =>
      message.role === 'tool' &&
      typeof message.content === 'string' &&
      (message.content as string).includes('diff --git'),
  );
  const latest = diffs[diffs.length - 1];
  return latest ? (latest.content as string) : null;
}

export function DiffSection({ sessionId }: { sessionId: string | null }) {
  const { t } = useI18n();
  const { data, loading, error, reload } = useAsyncData<string | null>(async () => {
    if (!sessionId) return null;
    const messages = (await api.getSessionMessages(sessionId)) as unknown as Array<Record<string, unknown>>;
    return extractLatestDiff(messages);
  }, [sessionId]);

  if (loading) return <PanelLoading rows={3} />;
  if (error) return <PanelError onRetry={reload} />;
  if (!data) {
    return (
      <PanelEmpty
        icon={FileDiff}
        title={t('right_panel.states.empty_diff')}
        hint={t('right_panel.states.empty_diff_hint')}
      />
    );
  }

  return <DiffPanel diffText={data} />;
}

interface DocumentEntry {
  id: string;
  name: string;
  chunks: number;
}

export function FilesSection() {
  const { t } = useI18n();
  const { data, loading, error, reload } = useAsyncData<DocumentEntry[]>(async () => {
    const payload = await api.listDocuments();
    const docs = Array.isArray(payload) ? payload : [];
    return docs.map((doc, index) => {
      const rawName = doc.name;
      const rawChunks = doc.chunks;
      return {
        id: doc.id ?? `doc-${index}`,
        name: typeof rawName === 'string' ? rawName : '',
        chunks: typeof rawChunks === 'number' && Number.isFinite(rawChunks) && rawChunks > 0 ? rawChunks : 0,
      };
    });
  }, []);

  if (loading) return <PanelLoading rows={3} />;
  if (error) return <PanelError onRetry={reload} />;
  if (!data || data.length === 0) {
    return (
      <PanelEmpty
        icon={FolderTree}
        title={t('right_panel.states.empty_documents')}
        hint={t('right_panel.states.empty_documents_hint')}
      />
    );
  }

  return (
    <div>
      {/* The document count belongs to this localised title, so the group
          heading stays free of a second copy of the same number. */}
      <SectionHeader title={t('right_panel.files.title', { count: data.length })} />
      <ul className="pt-1.5">
        {data.map((doc) => (
          <li
            key={doc.id}
            className="flex items-center gap-2 rounded-[var(--radius-md)] px-1.5 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-2)]"
          >
            <FolderTree size={12} className="shrink-0 text-[var(--color-text-muted)]" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">
              {doc.name || t('right_panel.summary.none')}
            </span>
            {doc.chunks > 0 && (
              <span className="shrink-0 text-[10px] tabular-nums text-[var(--color-text-muted)]">
                {t('right_panel.files.chunks', { count: doc.chunks })}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
