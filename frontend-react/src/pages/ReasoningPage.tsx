import { ReasoningPanel } from '../components/workspace/ReasoningPanel';
import { ResearchPanel } from '../components/workspace/ResearchPanel';
import { useI18n } from '../i18n';
import { Brain } from 'lucide-react';

export function ReasoningPage() {
  const { t } = useI18n();
  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col">
      <header className="flex shrink-0 items-center gap-2 px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <Brain size={16} aria-hidden="true" className="text-[var(--color-text-muted)]" />
        <h1 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{t('navigation.reasoning')}</h1>
      </header>
      <div className="flex-1 min-h-0 min-w-0 overflow-auto">
        <ReasoningPanel />
        <ResearchPanel />
      </div>
    </div>
  );
}
