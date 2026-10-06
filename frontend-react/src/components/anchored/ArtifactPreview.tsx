import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { useAnchoredStore } from '../../store/anchored';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import '../workspace/codex-suite.css';

const MARKER_TONE = {
  add: 'text-[var(--color-diff-added)]',
  del: 'text-[var(--color-diff-removed)]',
  change: 'text-[var(--color-diff-hunk)]',
  ctx: 'text-[var(--color-text-secondary)]',
} as const;

export function ArtifactPreview() {
  const { t } = useI18n();
  const previews = useAnchoredStore(state => state.previews);
  const activePreviewId = useAnchoredStore(state => state.activePreviewId);
  const setActivePreview = useAnchoredStore(state => state.setActivePreview);
  const closeFilePreview = useAnchoredStore(state => state.closeFilePreview);
  const active = previews.find(entry => entry.id === activePreviewId) ?? previews.at(-1);
  return (
    <div data-testid="anchored-file-preview" className="space-y-[var(--space-1-5)]">
      {active ? <>
        <div role="tablist" aria-label={t('anchored.cards.file_preview')} className="flex gap-[var(--space-1)] overflow-x-auto">
          {previews.map(entry => (
            <button key={entry.id} type="button" role="tab" aria-selected={entry.id === active.id} aria-controls="anchored-artifact-content" id={`artifact-tab-${entry.id}`} onClick={() => setActivePreview(entry.id)} title={entry.path}
              className={cn('shrink-0 rounded-[var(--radius-md)] border px-[var(--space-1-5)] py-[var(--space-0-5)] text-[length:var(--text-xs)] transition-colors focus-visible:shadow-[var(--focus-ring)]', entry.id === active.id ? 'border-[var(--color-border-accent)] text-[var(--color-text-primary)]' : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]')}>
              <WorkbenchIcon name="preview" size={12} />{entry.name}
            </button>
          ))}
        </div>
        <button type="button" onClick={() => closeFilePreview(active.id)} className="cx-mono rounded-[var(--radius-sm)] px-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] focus-visible:shadow-[var(--focus-ring)]">{t('anchored.preview.close')} · {active.name}</button>
        <div id="anchored-artifact-content" role="tabpanel" aria-labelledby={`artifact-tab-${active.id}`}>
          <pre className="max-h-[var(--anchored-result-height)] overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-[var(--space-2)] font-mono text-[length:var(--text-2xs)] leading-[var(--leading-normal)]">
            {active.lines.map((line, index) => <div key={index} className={cn('workbench-code-line', MARKER_TONE[line.marker])} data-line-marker={line.marker}><span className="workbench-line-number" aria-hidden="true">{index + 1}</span><span className="workbench-line-sign" aria-hidden="true">{line.marker === 'add' ? '+' : line.marker === 'del' ? '-' : line.marker === 'change' ? '~' : ' '}</span><span>{line.text}</span></div>)}
          </pre>
          <p className="cx-mono mt-[var(--space-1)] truncate text-[length:var(--text-2xs)] text-[var(--color-text-muted)]" title={active.path}>{active.path}</p>
        </div>
      </> : <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{t('anchored.preview.empty')}</p>}
      <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">产物来源：成功文件工具的输出。独立产物下载与版本管理尚未接入。</p>
    </div>
  );
}
