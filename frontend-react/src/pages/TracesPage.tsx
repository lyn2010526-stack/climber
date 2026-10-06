import TraceViewer from '../components/tracing/TraceViewer';
import { useI18n } from '../i18n';
import { GitBranch } from 'lucide-react';

export default function TracesPage() {
  const { t } = useI18n();
  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col">
      <header className="flex shrink-0 items-center gap-2 px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <GitBranch size={16} aria-hidden="true" className="text-[var(--color-text-muted)]" />
        <h1 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{t('navigation.traces')}</h1>
      </header>
      <div className="flex-1 min-h-0 min-w-0 overflow-auto">
        <TraceViewer />
      </div>
    </div>
  );
}
