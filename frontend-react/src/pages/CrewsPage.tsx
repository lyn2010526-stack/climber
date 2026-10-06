import { Users } from 'lucide-react';
import { useI18n } from '../i18n';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';

/**
 * Placeholder surface for the crews destination. The navigation entry exists
 * so crews and cluster no longer render the same page; the real orchestration
 * UI is delivered separately and fills this shell in.
 */
export function CrewsPage() {
  const { t } = useI18n();
  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('crews.page_title', { defaultValue: 'Crews' })}
          icon={<Users size={20} aria-hidden="true" />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
        />
        <Card padding="none" className="overflow-hidden">
          <EmptyState
            className="w-full"
            icon="inbox"
            title={t('crews.empty_title', { defaultValue: 'Crews orchestration' })}
            description={t('crews.empty_description', { defaultValue: 'Multi-agent crew orchestration is on the way.' })}
          />
        </Card>
      </div>
    </div>
  );
}

export default CrewsPage;
