import { useState, useMemo } from 'react';
import { MoreHorizontal, X, ChevronUp } from 'lucide-react';
import { ClimberMark } from '../brand/ClimberMark';
import { CORE_NAV_ITEMS_BASE, ALL_NAV_ITEMS_BASE } from '../../navigation/navConfig';
import type { NavItem } from '../../navigation/navConfig';
import { useI18n } from '../../i18n';

const MOBILE_PRIMARY_IDS = new Set(['dashboard', 'chat', 'agents', 'workflows']);

export function AdaptiveMobileLayout({ children, currentPage, onNavigate }: {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}) {
  const { t } = useI18n();
  const [moreOpen, setMoreOpen] = useState(false);

  const { primaryItems, moreItems } = useMemo(() => {
    const toEntry = (item: NavItem) => ({
      id: item.id,
      label: t(item.labelKey ?? item.label ?? item.id),
      icon: item.icon,
    });
    return {
      primaryItems: CORE_NAV_ITEMS_BASE.filter(item => MOBILE_PRIMARY_IDS.has(item.id)).map(toEntry),
      moreItems: ALL_NAV_ITEMS_BASE.filter(item => !MOBILE_PRIMARY_IDS.has(item.id)).map(toEntry),
    };
  }, [t]);

  const currentItem = [...primaryItems, ...moreItems].find(item => item.id === currentPage);
  const moreActive = moreItems.some(item => item.id === currentPage);

  const navigate = (page: string) => {
    onNavigate(page);
    setMoreOpen(false);
  };

  return (
    <div className="mobile-workspace-shell">
      <header className="mobile-context-bar safe-area-top">
        <div className="workspace-mark" aria-hidden="true"><ClimberMark size={15} /></div>
        <div className="min-w-0 flex-1">
          <p className="workspace-eyebrow"><span>Climber</span> workspace</p>
          <h1 className="truncate text-sm font-semibold text-[var(--color-text-primary)]">{currentItem?.label ?? t('sidebar.workspace')}</h1>
        </div>
      </header>

      <main id="main-content" className="mobile-content">{children}</main>

      <nav className="mobile-bottom-nav safe-area-bottom" aria-label={t('sidebar.main_nav')}>
        {primaryItems.map(({ id, label, icon: Icon }) => {
          const active = currentPage === id;
          return (
            <button key={id} onClick={() => navigate(id)} aria-current={active ? 'page' : undefined} className="mobile-nav-item">
              <Icon size={19} strokeWidth={active ? 2.4 : 1.8} />
              <span>{label}</span>
            </button>
          );
        })}
        <button onClick={() => setMoreOpen(true)} aria-expanded={moreOpen} aria-current={moreActive ? 'page' : undefined} className="mobile-nav-item" data-active={moreActive || undefined}>
          <MoreHorizontal size={19} />
          <span>{t('sidebar.more')}</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="mobile-sheet-layer" role="presentation" onClick={() => setMoreOpen(false)}>
          <section className="mobile-nav-sheet" role="dialog" aria-modal="true" aria-label={t('sidebar.all_entries')} onClick={event => event.stopPropagation()}>
            <div className="mobile-sheet-header">
              <div>
                <p className="workspace-eyebrow">Workspace</p>
                <h2 className="text-base font-semibold">{t('sidebar.all_entries')}</h2>
              </div>
              <button className="icon-button" onClick={() => setMoreOpen(false)} aria-label={t('common.close')}><X size={18} /></button>
            </div>
            <div className="mobile-more-grid">
              {moreItems.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => navigate(id)} aria-current={currentPage === id ? 'page' : undefined}>
                  <Icon size={18} />
                  <span>{label}</span>
                  <ChevronUp size={14} className="rotate-90 text-[var(--color-text-muted)]" />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
