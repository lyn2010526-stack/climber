import { MessageSquare } from 'lucide-react';
import { useI18n } from '../../i18n';
import { MobileEmptyBodyCard, MobileNoticeCard, MobilePageSection } from './MobilePageScaffold';

interface MobileDesktopFallbackProps {
  title: string;
}

/**
 * The landing spot for a destination that stays desktop-first: the shell
 * header already carries the page name, so the body explains the situation and
 * offers the one action that always works on mobile — opening chat.
 */
export function MobileDesktopFallback({ title }: MobileDesktopFallbackProps) {
  const { t } = useI18n();

  return (
    <MobilePageSection labelledBy="mobile-fallback-title">
      <MobileNoticeCard
        icon={<MessageSquare size={20} aria-hidden="true" focusable="false" />}
        title={title}
        titleId="mobile-fallback-title"
        description={t('mobile.fallback.card_description')}
      />
      <MobileEmptyBodyCard
        emptyTitle={t('mobile.fallback.empty_title')}
        emptyDescription={t('mobile.fallback.empty_description')}
      />
    </MobilePageSection>
  );
}
