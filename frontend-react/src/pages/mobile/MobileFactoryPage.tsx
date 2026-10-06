import { Factory } from 'lucide-react';
import { useI18n } from '../../i18n';
import { MobileEmptyBodyCard, MobileNoticeCard, MobilePageSection } from './MobilePageScaffold';

/**
 * The mobile surface for factory mode. Plans, steps and the final report are
 * edited side by side on desktop; the body explains what factory covers and
 * keeps the chat action reachable on mobile.
 */
export function MobileFactoryPage() {
  const { t } = useI18n();

  return (
    <MobilePageSection labelledBy="mobile-factory-title">
      <MobileNoticeCard
        icon={<Factory size={20} aria-hidden="true" focusable="false" />}
        title={t('mobile.factory.card_title')}
        titleId="mobile-factory-title"
        description={t('mobile.factory.card_description')}
      />
      <MobileEmptyBodyCard
        emptyTitle={t('mobile.factory.empty_title')}
        emptyDescription={t('mobile.factory.empty_description')}
      />
    </MobilePageSection>
  );
}
