import { useState, useMemo, useEffect, useId, useRef, type CSSProperties } from 'react';
import { MoreHorizontal, X, ChevronRight } from 'lucide-react';
import { ClimberMark } from '../brand/ClimberMark';
import { CORE_NAV_ITEMS_BASE, ALL_NAV_ITEMS_BASE, MOBILE_ADAPTED_PAGE_IDS, type Page } from '../../navigation/navConfig';
import type { NavItem } from '../../navigation/navConfig';
import { trapTab } from '../../lib/focusTrap';
import { useI18n } from '../../i18n';
import { MobileDesktopFallback } from '../../pages/mobile/MobileDesktopFallback';

const MOBILE_PRIMARY_IDS: readonly string[] = ['dashboard', 'chat', 'factory', 'tasks'];
const PRIMARY_ID_SET: ReadonlySet<string> = new Set(MOBILE_PRIMARY_IDS);

// Mirrors the mobile branch of the app router: only these ids resolve to a
// surface that actually renders inside the shell. Everything else stays
// desktop-first and resolves to the conversation entry.
const MOBILE_USABLE_PAGE_IDS: ReadonlySet<string> = new Set([
  'dashboard', 'chat', 'factory', 'cluster', 'tasks', 'agents', 'apikeys', 'settings',
]);

const CHAT_PAGE_ID = 'chat';
const MOBILE_FALLBACK_PAGE_IDS = new Set(['agents', 'apikeys', 'settings']);

// The shell is clamped to the software keyboard. A zero height would hide the
// composer entirely, so the clamp keeps a floor that still fits one row.
const MIN_SHELL_HEIGHT = 120;

// Breathing room below the composer once the navigation is behind the keyboard
// and its reserved strip is no longer reachable.
const KEYBOARD_CONTENT_PADDING = 12;

interface ShellMetrics {
  /** Visible shell height in layout-viewport pixels, or null to let CSS own it. */
  clamp: number | null;
}

/**
 * Measures how much of the fixed shell the software keyboard leaves visible.
 *
 * The shell is `position: fixed`, so it is sized by the layout viewport and the
 * navigation is pinned to that same viewport. While the navigation is still
 * reachable the browser already sizes the shell correctly, including the
 * toolbar collapses that change the layout viewport height. Once the keyboard
 * occludes the navigation the shell is clamped to the visual viewport bottom,
 * and the navigation reserve in the content area is released with it.
 */
function useShellMetrics(shellRef: React.RefObject<HTMLElement | null>): ShellMetrics {
  const [clamp, setClamp] = useState<number | null>(null);

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const viewport = window.visualViewport ?? null;
    let frame = 0;

    const sync = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        // Pinch zoom makes layout geometry unreliable, so sizing goes back to
        // CSS until the user returns to scale 1.
        if (viewport && viewport.scale !== 1) {
          setClamp(null);
          return;
        }
        const layoutBottom = window.innerHeight;
        const visibleBottom = viewport ? viewport.offsetTop + viewport.height : layoutBottom;
        if (!Number.isFinite(visibleBottom) || visibleBottom >= layoutBottom) {
          setClamp(null);
          return;
        }
        const shellTop = shell.getBoundingClientRect().top;
        const next = Math.max(MIN_SHELL_HEIGHT, Math.round(visibleBottom - shellTop));
        setClamp(previous => (previous === next ? previous : next));
      });
    };

    sync();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(sync);
    if (observer) observer.observe(shell);
    viewport?.addEventListener('resize', sync);
    viewport?.addEventListener('scroll', sync);
    window.addEventListener('resize', sync);
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
      viewport?.removeEventListener('resize', sync);
      viewport?.removeEventListener('scroll', sync);
      window.removeEventListener('resize', sync);
    };
  }, [shellRef]);

  return { clamp };
}

export function AdaptiveMobileLayout({ children, currentPage, onNavigate }: {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}) {
  const { t } = useI18n();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreButtonRef = useRef<HTMLButtonElement>(null);
  const sheetCloseRef = useRef<HTMLButtonElement>(null);
  const sheetRef = useRef<HTMLElement>(null);
  const shellRef = useRef<HTMLDivElement>(null);
  const requestedFallbackRef = useRef<string | null>(null);
  const sheetTitleId = useId();
  const metrics = useShellMetrics(shellRef);

  useEffect(() => {
    if (!moreOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMoreOpen(false);
        return;
      }
      // The sheet declares aria-modal, so Tab must stay inside it. The dialog
      // element itself is the first stop, which is why it carries tabIndex -1.
      if (e.key !== 'Tab' || !sheetRef.current) return;
      if (trapTab(sheetRef.current, e.shiftKey)) e.preventDefault();
    };
    // Press-outside dismissal listens on the document rather than on the
    // dimmed layer. The layer is decoration, and a handler on it would be a
    // control that answers to no key; here the gesture is owned by the dialog,
    // which keeps a real close button and Escape as its keyboard equivalents.
    const handlePointerDown = (e: PointerEvent) => {
      if (!sheetRef.current) return;
      const target = e.target as Node;
      if (sheetRef.current.contains(target)) return;
      setMoreOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('pointerdown', handlePointerDown);
    sheetCloseRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('pointerdown', handlePointerDown);
      // Restore focus to the trigger so keyboard users keep their place.
      moreButtonRef.current?.focus();
    };
  }, [moreOpen]);

  const { primaryItems, moreItems } = useMemo(() => {
    const toEntry = (item: NavItem) => ({
      id: item.id,
      label: t(item.labelKey ?? item.label ?? item.id),
      icon: item.icon,
    });
    const isUsable = (id: string) =>
      MOBILE_ADAPTED_PAGE_IDS.has(id as Page) && MOBILE_USABLE_PAGE_IDS.has(id);
    return {
      primaryItems: MOBILE_PRIMARY_IDS
        .map(id => CORE_NAV_ITEMS_BASE.find(item => item.id === id))
        .filter((item): item is NavItem => item !== undefined)
        .map(toEntry),
      moreItems: ALL_NAV_ITEMS_BASE
        .filter(item => isUsable(item.id) && !PRIMARY_ID_SET.has(item.id))
        .map(toEntry),
    };
  }, [t]);

  // The header and the active marker always describe what the shell renders.
  const effectivePage = MOBILE_USABLE_PAGE_IDS.has(currentPage) ? currentPage : CHAT_PAGE_ID;

  useEffect(() => {
    if (effectivePage === currentPage) {
      requestedFallbackRef.current = null;
      return;
    }
    // Idempotent: the router hands over a fresh callback on every render, so the
    // request is recorded instead of retriggering on unrelated renders.
    if (requestedFallbackRef.current === currentPage) return;
    requestedFallbackRef.current = currentPage;
    onNavigate(CHAT_PAGE_ID);
  }, [currentPage, effectivePage, onNavigate]);

  const currentItem = [...primaryItems, ...moreItems].find(item => item.id === effectivePage);
  const moreActive = moreItems.some(item => item.id === effectivePage);

  const navigate = (page: string) => {
    onNavigate(page);
    setMoreOpen(false);
  };

  const shellStyle: CSSProperties | undefined = metrics.clamp === null ? undefined : { height: `${metrics.clamp}px` };
  const contentStyle: CSSProperties = {
    minHeight: 0,
    ...(metrics.clamp === null ? {} : { paddingBottom: `${KEYBOARD_CONTENT_PADDING}px` }),
  };

  return (
    <div ref={shellRef} className="mobile-workspace-shell" style={shellStyle}>
      <header className="mobile-context-bar safe-area-top">
        <div className="workspace-mark" aria-hidden="true"><ClimberMark size={15} /></div>
        <div className="min-w-0 flex-1">
           <p className="workspace-eyebrow">Climber · {t('sidebar.workspace')}</p>
          <h1 className="truncate text-sm font-semibold text-[var(--color-text-primary)]">{currentItem?.label ?? t('sidebar.workspace')}</h1>
        </div>
      </header>

      <main id="main-content" className="mobile-content" style={contentStyle}>
        {MOBILE_FALLBACK_PAGE_IDS.has(effectivePage) ? (
          <MobileDesktopFallback
            title={currentItem?.label ?? t('sidebar.workspace')}
            description="此页面属于桌面工作台，移动端保留明确入口并提供稳定导航。"
          />
        ) : children ?? (
          <div className="flex min-h-full items-center justify-center px-6 text-center text-sm text-[var(--color-text-muted)]" role="status">
            {t('common.no_data')}
          </div>
        )}
      </main>

      <nav className="mobile-bottom-nav safe-area-bottom" aria-label={t('sidebar.main_nav')}>
        {primaryItems.map(({ id, label, icon: Icon }) => {
          const active = effectivePage === id;
          return (
            <button type="button" key={id} onClick={() => navigate(id)} aria-current={active ? 'page' : undefined} className="mobile-nav-item">
              <Icon size={19} strokeWidth={active ? 2.4 : 1.8} />
              <span>{label}</span>
            </button>
          );
        })}
        <button type="button" ref={moreButtonRef} onClick={() => setMoreOpen(true)} aria-expanded={moreOpen} aria-current={moreActive ? 'page' : undefined} className="mobile-nav-item" data-active={moreActive || undefined}>
          <MoreHorizontal size={19} />
          <span>{t('sidebar.more')}</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="mobile-sheet-layer">
          {/* The dimmed backdrop is decoration. Press-outside dismissal is owned
              by the dialog below, which is the ARIA dialog pattern: a dialog
              that dismisses on an outside press keeps a real close control and
              Escape, so the backdrop needs no name and no focus stop. */}
          <div className="mobile-sheet-backdrop" aria-hidden="true" />
          <section
            className="mobile-nav-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby={sheetTitleId}
            aria-describedby={`${sheetTitleId}-description`}
            tabIndex={-1}
            ref={sheetRef}
          >
            <div className="mobile-sheet-header">
              <div>
                 <p className="workspace-eyebrow">{t('sidebar.workspace')}</p>
                <h2 id={sheetTitleId} className="text-base font-semibold">{t('sidebar.all_entries')}</h2>
                <p id={`${sheetTitleId}-description`} className="sr-only">使用 Tab 浏览移动端页面，按 Escape 关闭菜单。</p>
              </div>
              <button type="button" ref={sheetCloseRef} className="icon-button" onClick={() => setMoreOpen(false)} aria-label={t('common.close')}><X size={18} aria-hidden="true" focusable="false" /></button>
            </div>
            <div className="mobile-more-grid">
              {moreItems.map(({ id, label, icon: Icon }) => (
                <button type="button" key={id} onClick={() => navigate(id)} aria-current={effectivePage === id ? 'page' : undefined}>
                  <Icon size={18} aria-hidden="true" focusable="false" />
                  <span>{label}</span>
                  <ChevronRight size={14} aria-hidden="true" className="text-[var(--color-text-muted)]" />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
