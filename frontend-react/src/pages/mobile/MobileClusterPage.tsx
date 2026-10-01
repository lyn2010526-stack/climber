import { Network } from 'lucide-react';
import { useI18n } from '../../i18n';
import { MobileEmptyBodyCard, MobileNoticeCard, MobilePageSection } from './MobilePageScaffold';

/**
 * The mobile surface for cluster collaboration. Groups and members need wide
 * tables and detail panes, so the body keeps the surface reachable and hands
 * the full workbench back to the desktop.
 */
export function MobileClusterPage() {
  const { t } = useI18n();

  return (
    <MobilePageSection labelledBy="mobile-cluster-title">
      <MobileNoticeCard
        icon={<Network size={20} aria-hidden="true" focusable="false" />}
        title={t('mobile.cluster.card_title')}
        titleId="mobile-cluster-title"
        description={t('mobile.cluster.card_description')}
      />
      <MobileEmptyBodyCard
        emptyTitle={t('mobile.cluster.empty_title')}
        emptyDescription={t('mobile.cluster.empty_description')}
      />
    </MobilePageSection>
  );
}
