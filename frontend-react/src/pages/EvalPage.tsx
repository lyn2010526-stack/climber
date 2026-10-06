import { EvalDashboard } from '../components/eval/EvalDashboard';
import { PageHeader } from '../components/ui/PageHeader';
import { FlaskConical } from 'lucide-react';
import { useI18n } from '../i18n';

export default function EvalPage() {
  const { t } = useI18n();
  return (
    <div className="h-full flex flex-col overflow-hidden page-transition">
      <div className="px-4 py-3 md:px-6 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <PageHeader
          title={t('navigation.eval', { defaultValue: 'Evaluations' })}
          icon={<FlaskConical size={20} />}
          className="mb-0 md:mb-0 [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <EvalDashboard />
      </div>
    </div>
  );
}
