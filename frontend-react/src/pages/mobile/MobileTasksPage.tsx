import { Cpu } from 'lucide-react';
import { useI18n } from '../../i18n';
import { MobileEmptyBodyCard, MobileNoticeCard, MobilePageSection } from './MobilePageScaffold';

/**
 * The mobile surface for task monitoring. The desktop console owns the live
 * table; here the body explains what monitoring covers and offers the chat
 * action that always works on mobile.
 */
export function MobileTasksPage() {
  const { t } = useI18n();

  return (
    <MobilePageSection labelledBy="mobile-tasks-title">
      <MobileNoticeCard
        icon={<Cpu size={20} aria-hidden="true" focusable="false" />}
        title={t('mobile.tasks.card_title')}
        titleId="mobile-tasks-title"
        description={t('mobile.tasks.card_description')}
      />
      <MobileEmptyBodyCard
        emptyTitle={t('mobile.tasks.empty_title')}
        emptyDescription={t('mobile.tasks.empty_description')}
      />
    </MobilePageSection>
  );
}
