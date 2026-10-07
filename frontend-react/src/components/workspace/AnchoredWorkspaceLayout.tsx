import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Group, Panel, Separator, usePanelRef } from 'react-resizable-panels';
import { PanelLeftOpen, PanelRightClose } from 'lucide-react';
import { useI18n } from '../../i18n';
import { useDefaultSession } from '../../hooks/useDefaultSession';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { useWorkspaceStore } from '../../store/workspace';
import { useMediaQuery } from '../../layout/breakpoints';
import { trapTab } from '../../lib/focusTrap';
import { useBootReveal } from '../motion/bootHandoff';
import { hasPlayedWorkspaceEntry, markWorkspaceEntryPlayed } from '../motion/firstEntry';
import { WORKSPACE_ENTER_TOTAL_MS } from '../motion/bootTiming';
import { AnchoredLeftNav } from './AnchoredLeftNav';
import { AnchoredInfoPanel } from './AnchoredInfoPanel';
import { AnchoredChatColumn } from '../agent/AnchoredChatColumn';
import { ControlBar } from './ControlBar';

const LEFT_DEFAULT = 240;
const LEFT_MIN = 180;
const LEFT_MAX = 360;
const LEFT_COLLAPSED = 60;
const CENTER_MIN = 600;
const RIGHT_DEFAULT = 320;
const RIGHT_MIN = 240;
const RIGHT_MAX = 480;
const RIGHT_COLLAPSED = 0;

/**
 * Width at which the inline three-column canvas fits without squeezing the
 * centre below its 600px floor: the two default side rails, the centre floor
 * and the two 1px separators. Below it the side rails become drawers so the
 * conversation keeps the full width instead of the columns collapsing.
 */
const THREE_COLUMN_MIN = LEFT_DEFAULT + CENTER_MIN + RIGHT_DEFAULT + 2;
const THREE_COLUMN_QUERY = `(min-width: ${THREE_COLUMN_MIN}px)`;

const PREFERENCES_KEY = 'climber.workspace.desktop.v1';
const DEFAULT_PREFERENCES = {
  leftWidth: LEFT_DEFAULT, rightWidth: RIGHT_DEFAULT,
  leftCollapsed: false, rightCollapsed: true,
};

function readPreferences() {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(PREFERENCES_KEY) ?? 'null');
    if (!saved || typeof saved !== 'object') return DEFAULT_PREFERENCES;
    const values = saved as Record<string, unknown>;
    const width = (value: unknown, fallback: number, min: number, max: number) =>
      typeof value === 'number' && Number.isFinite(value) ? Math.max(min, Math.min(max, value)) : fallback;
    return {
      leftWidth: width(values.leftWidth, LEFT_DEFAULT, LEFT_MIN, LEFT_MAX),
      rightWidth: width(values.rightWidth, RIGHT_DEFAULT, RIGHT_MIN, RIGHT_MAX),
      leftCollapsed: typeof values.leftCollapsed === 'boolean' ? values.leftCollapsed : false,
      rightCollapsed: typeof values.rightCollapsed === 'boolean' ? values.rightCollapsed : true,
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

interface ViewportClamp {
  height: number;
  top: number;
}

/**
 * The rail geometry to hand back when focus mode ends. Captured the moment the
 * mode is entered so the user's own `leftCollapsed` / `rightCollapsed`
 * preferences are restored verbatim instead of staying collapsed forever.
 */
interface FocusLayoutSnapshot {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  leftWidth: number;
  rightWidth: number;
  leftDrawerOpen: boolean;
  rightDrawerOpen: boolean;
}

/**
 * Clamps a fixed surface to the visual viewport so the on-screen keyboard cannot
 * cover the composer. Returns null whenever the layout viewport is already the
 * visible one (no visualViewport, pinch-zoom, or no occlusion), letting CSS own
 * the geometry.
 */
function useVisualViewportClamp(): ViewportClamp | null {
  const [clamp, setClamp] = useState<ViewportClamp | null>(null);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const sync = () => {
      // Pinch zoom makes the visual geometry unreliable, so hand sizing back to CSS.
      if (viewport.scale !== 1) {
        setClamp(null);
        return;
      }
      const top = Number.isFinite(viewport.offsetTop) ? Math.round(viewport.offsetTop) : 0;
      setClamp({ height: Math.round(viewport.height), top });
    };
    sync();
    viewport.addEventListener('resize', sync);
    viewport.addEventListener('scroll', sync);
    return () => {
      viewport.removeEventListener('resize', sync);
      viewport.removeEventListener('scroll', sync);
    };
  }, []);

  return clamp;
}

/**
 * A side rail rendered as an overlay drawer below the three-column breakpoint.
 * It owns the modal contract (aria-modal, Escape, Tab containment, focus
 * restoration) and the shared `.modal-overlay` scrim, so a press outside closes
 * it and focus returns to whatever opened it.
 */
function AnchoredDrawer({ label, side, clamp, onClose, children }: {
  label: string;
  side: 'left' | 'right';
  clamp: ViewportClamp | null;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    previousFocus.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key === 'Tab' && dialogRef.current && trapTab(dialogRef.current, event.shiftKey)) {
        event.preventDefault();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      // Return the caret to the control that opened the drawer.
      previousFocus.current?.focus();
    };
  }, []);

  return (
    <>
      <div className="modal-overlay" onClick={() => closeRef.current()} aria-hidden="true" />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        data-testid={side === 'left' ? 'anchored-left-drawer' : 'anchored-right-drawer'}
        className={[
          'fixed top-0 z-[var(--z-modal,400)] flex h-full w-[min(360px,86vw)] flex-col overflow-hidden',
          'bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-xl)] focus-visible:outline-none',
          side === 'left' ? 'left-0 border-r border-[var(--color-border-default)]' : 'right-0 border-l border-[var(--color-border-default)]',
        ].join(' ')}
        style={clamp ? { height: `${clamp.height}px`, top: `${clamp.top}px` } : undefined}
      >
        {children}
      </div>
    </>
  );
}

export function AnchoredWorkspaceLayout() {
  const { t } = useI18n();
  const { sessionId } = useDefaultSession();
  const threeColumn = useMediaQuery(THREE_COLUMN_QUERY);
  const clamp = useVisualViewportClamp();
  const focusMode = useWorkspaceStore((s) => s.focusMode);
  const toggleFocusMode = useWorkspaceStore((s) => s.toggleFocusMode);

  // Focus mode: Escape is the documented exit key (the slim control bar
  // advertises it via aria-keyshortcuts), bound whenever focus sits outside a
  // text field so typing Escape in the composer never leaves focus mode.
  useEffect(() => {
    if (!focusMode) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable="true"]')) return;
      event.preventDefault();
      toggleFocusMode();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [focusMode, toggleFocusMode]);
  const [preferences, setPreferences] = useState(readPreferences);
  const initialPreferences = useRef(preferences).current;
  const rootRef = useRef<HTMLElement>(null);
  const resizing = useRef(false);
  const [availableWidth, setAvailableWidth] = useState(() => window.innerWidth);
  const [leftWidth, setLeftWidth] = useState(preferences.leftCollapsed ? LEFT_COLLAPSED : preferences.leftWidth);
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(false);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(false);
  const leftPanelRef = usePanelRef();
  const rightPanelRef = usePanelRef();
  const focusSnapshot = useRef<FocusLayoutSnapshot | null>(null);
  const { leftCollapsed, rightCollapsed } = preferences;
  const leftMax = Math.max(LEFT_MIN, Math.min(LEFT_MAX, availableWidth - CENTER_MIN - (rightCollapsed ? 0 : RIGHT_MIN) - 2));
  const rightMax = Math.max(RIGHT_MIN, Math.min(RIGHT_MAX, availableWidth - CENTER_MIN - (leftCollapsed ? LEFT_COLLAPSED : LEFT_MIN) - 2));

  /**
   * Focus mode maximises the conversation surface: the side rails give way so
   * the centre keeps the full width. Entering captures the rail geometry in a
   * ref, drives the collapsed flags to `true` for the lifetime of the mode and
   * hands the snapshot back on exit, so the mode never rewrites the user's own
   * `leftCollapsed` / `rightCollapsed` preferences. The programmatic
   * `collapse()` runs outside a pointer/keyboard drag, so the panels' own
   * `onResize` handlers — guarded by `resizing.current` — leave `preferences`
   * untouched and the two paths never fight over the same values.
   * The snapshot is read once per mode transition, so the live geometry is
   * deliberately kept out of the dependency list.
   */
  useEffect(() => {
    if (focusMode) {
      if (!focusSnapshot.current) {
        focusSnapshot.current = {
          leftCollapsed, rightCollapsed,
          leftWidth, rightWidth: preferences.rightWidth,
          leftDrawerOpen, rightDrawerOpen,
        };
      }
      if (threeColumn) {
        leftPanelRef.current?.collapse();
        rightPanelRef.current?.collapse();
        setPreferences(current => ({ ...current, leftCollapsed: true, rightCollapsed: true }));
      } else {
        setLeftDrawerOpen(false);
        setRightDrawerOpen(false);
      }
      return;
    }
    const snapshot = focusSnapshot.current;
    focusSnapshot.current = null;
    if (!snapshot) return;
    // Restore both surfaces unconditionally: the viewport may have switched
    // between rails and drawers while the mode was active, and neither may be
    // left collapsed or closed because of it.
    setPreferences(current => ({ ...current, leftCollapsed: snapshot.leftCollapsed, rightCollapsed: snapshot.rightCollapsed }));
    if (threeColumn) {
      if (!snapshot.leftCollapsed) leftPanelRef.current?.resize(`${snapshot.leftWidth}px`);
      if (!snapshot.rightCollapsed) rightPanelRef.current?.resize(`${snapshot.rightWidth}px`);
    }
    setLeftDrawerOpen(snapshot.leftDrawerOpen);
    setRightDrawerOpen(snapshot.rightDrawerOpen);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusMode, threeColumn]);

  /**
   * The three-rail arrival, played once per tab and timed to the curtain lift.
   * The layout mounts underneath the splash, so it decides whether this is the
   * first entry on its own flag — before the boot session flag exists — and
   * holds the rails at their opening state until the boot announces the reveal.
   * Every later mount (a route change back to the workspace, a repeat visit)
   * renders the rails settled, so the sweep is spent exactly once.
   */
  const [playEntry] = useState(() => !hasPlayedWorkspaceEntry());
  const reducedMotion = usePrefersReducedMotion();
  const revealed = useBootReveal();
  const [entryDone, setEntryDone] = useState(!playEntry);
  useEffect(() => {
    if (!playEntry) return;
    markWorkspaceEntryPlayed();
    // The classes carry the keyframes; once the sweep has finished they are
    // dropped so a later resize never replays a rail mid-gesture.
    const timer = window.setTimeout(() => setEntryDone(true), WORKSPACE_ENTER_TOTAL_MS);
    return () => window.clearTimeout(timer);
  }, [playEntry]);
  // Reduced motion skips the sweep entirely: the rails render settled, never
  // held behind a curtain they are not going to animate out from under.
  // Otherwise the rails stay invisible until the curtain starts to lift:
  // spending the entrance behind the splash would leave the app looking like
  // it popped in.
  const entering = playEntry && !entryDone && !reducedMotion;
  const holding = entering && !revealed;
  const railEnterClass = (side: 'left' | 'center' | 'right') =>
    holding ? 'opacity-0' : entering ? `anchored-enter-${side}` : '';

  useEffect(() => {
    // Focus mode collapses the rails transiently; persisting that flag would
    // leave the workspace collapsed on the next load, so the mode skips the
    // write and lets the restored snapshot persist instead.
    if (focusMode) return;
    try { localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences)); } catch { /* Storage can be disabled. */ }
  }, [preferences, focusMode]);

  useEffect(() => {
    const sync = () => setAvailableWidth(rootRef.current?.clientWidth || window.innerWidth);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(sync);
    if (rootRef.current) observer?.observe(rootRef.current);
    window.addEventListener('resize', sync);
    sync();
    return () => { observer?.disconnect(); window.removeEventListener('resize', sync); };
  }, []);

  useEffect(() => {
    const stop = () => { resizing.current = false; };
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
    window.addEventListener('keyup', stop);
    window.addEventListener('blur', stop);
    return () => {
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      window.removeEventListener('keyup', stop);
      window.removeEventListener('blur', stop);
    };
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty('--anchored-left-width', `${leftWidth}px`);
    return () => { document.documentElement.style.removeProperty('--anchored-left-width'); };
  }, [leftWidth]);

  const toggleInfo = () => {
    // Below the three-column breakpoint the info panel is a drawer instead of a
    // fourth inline column, so the conversation never loses the full width.
    if (!threeColumn) {
      setRightDrawerOpen(open => !open);
      return;
    }
    if (rightCollapsed) {
      // Make room for inspect at 1024px while keeping the chat mounted and readable.
      const target = Math.min(preferences.rightWidth, rightMax);
      const leftTarget = Math.max(LEFT_MIN, availableWidth - CENTER_MIN - target - 2);
      if (!leftCollapsed && leftWidth > leftTarget) leftPanelRef.current?.resize(`${leftTarget}px`);
      rightPanelRef.current?.resize(`${target}px`);
    } else {
      rightPanelRef.current?.collapse();
      if (!leftCollapsed) leftPanelRef.current?.resize(`${Math.min(preferences.leftWidth, availableWidth - CENTER_MIN - 2)}px`);
    }
    setPreferences(current => ({ ...current, rightCollapsed: !rightCollapsed }));
  };
  const separatorProps = {
    className: 'workbench-desktop-separator',
    onPointerDown: () => { resizing.current = true; },
    onKeyDown: () => { resizing.current = true; },
  };

  return (
    <section ref={rootRef} data-testid="anchored-workspace" data-layout={threeColumn ? 'three-column' : 'drawers'}
      data-focus={focusMode ? 'true' : 'false'}
      data-inspect-open={threeColumn ? !rightCollapsed : rightDrawerOpen} aria-label={t('sidebar.workspace')}
      style={clamp ? { height: `${clamp.height}px`, top: `${clamp.top}px` } : undefined}
      className="workbench-theme workbench-desktop flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden motion-safe:transition-[opacity,transform] motion-safe:duration-150 motion-safe:ease-out">
      {!threeColumn && (
        <div key="anchored-drawers-bar" data-testid="anchored-drawers-bar"
          className="flex h-12 shrink-0 items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-[var(--space-2)]">
          <button type="button" aria-label={t('anchored.layout.expand_left')} aria-expanded={leftDrawerOpen}
            aria-controls="anchored-left-drawer" onClick={() => setLeftDrawerOpen(open => !open)}
            className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-lg)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] focus-visible:shadow-[var(--focus-ring)]">
            <PanelLeftOpen size={16} aria-hidden="true" />
          </button>
          <span className="min-w-0 flex-1 truncate text-[length:var(--text-sm)] font-medium text-[var(--color-text-primary)]">{t('anchored.nav.label')}</span>
        </div>
      )}
      <Group key="anchored-workspace-group" orientation="horizontal" id="anchored-workspace-group" className="min-h-0 min-w-0 flex-1">
        {threeColumn && (
          <Panel key="anchored-left" id="anchored-left" panelRef={leftPanelRef}
            defaultSize={`${initialPreferences.leftCollapsed ? LEFT_COLLAPSED : initialPreferences.leftWidth}px`}
            minSize={`${LEFT_MIN}px`} maxSize={`${leftMax}px`} collapsible collapsedSize={`${LEFT_COLLAPSED}px`}
            groupResizeBehavior="preserve-pixel-size" className={`workbench-desktop-sidebar h-full ${railEnterClass('left')}`.trim()}
            onResize={(size, _id, previous) => {
              setLeftWidth(size.inPixels);
              if (!previous || !resizing.current) return;
              setPreferences(current => ({ ...current, leftCollapsed: size.inPixels <= LEFT_COLLAPSED,
                leftWidth: size.inPixels >= LEFT_MIN ? Math.min(LEFT_MAX, size.inPixels) : current.leftWidth }));
            }}>
            {leftCollapsed ? <div className="workbench-desktop-rail">
              <button type="button" className="workbench-desktop-panel-button" aria-label={t('anchored.layout.expand_left')}
                onClick={() => {
                  leftPanelRef.current?.resize(`${Math.min(preferences.leftWidth, leftMax)}px`);
                  setPreferences(current => ({ ...current, leftCollapsed: false }));
                }}><PanelLeftOpen size={16} aria-hidden="true" /></button>
            </div> : <AnchoredLeftNav onCollapse={() => {
              leftPanelRef.current?.collapse();
              setPreferences(current => ({ ...current, leftCollapsed: true }));
            }} />}
          </Panel>
        )}
        {threeColumn && <Separator key="anchored-separator-left" {...separatorProps} aria-label={t('sidebar.workspace')} data-testid="anchored-left-separator" />}
        <Panel key="anchored-center" id="anchored-center" minSize={`${threeColumn ? CENTER_MIN : 0}px`} groupResizeBehavior="preserve-relative-size"
          className={`workbench-desktop-canvas h-full min-w-0 ${railEnterClass('center')}`.trim()}>
          {/* Session snapshot/rollback, expert/focus and permission controls live
              on this slim strip above the chat column; the column itself is not
              touched. */}
          <ControlBar variant="slim" />
          <div className="min-h-0 flex-1">
            <AnchoredChatColumn sessionId={sessionId} onToggleInfo={toggleInfo} />
          </div>
        </Panel>
        {threeColumn && <Separator key="anchored-separator-right" {...separatorProps} data-testid="anchored-right-separator" className="workbench-desktop-separator workbench-desktop-inspect-separator"
          disabled={rightCollapsed} aria-label={t('anchored.panel.label')} />}
        {threeColumn && (
          <Panel key="anchored-right" id="anchored-right" panelRef={rightPanelRef}
            defaultSize={`${initialPreferences.rightCollapsed ? RIGHT_COLLAPSED : initialPreferences.rightWidth}px`}
            minSize={`${RIGHT_MIN}px`} maxSize={`${rightMax}px`} collapsible collapsedSize={`${RIGHT_COLLAPSED}px`}
            groupResizeBehavior="preserve-pixel-size" className={`workbench-desktop-inspect h-full ${railEnterClass('right')}`.trim()}
            onResize={(size, _id, previous) => {
              if (!previous || !resizing.current) return;
              setPreferences(current => ({ ...current, rightCollapsed: size.inPixels <= RIGHT_COLLAPSED,
                rightWidth: size.inPixels >= RIGHT_MIN ? Math.min(RIGHT_MAX, size.inPixels) : current.rightWidth }));
            }}>
            {!rightCollapsed && <div className="workbench-desktop-inspect-content">
              <div className="workbench-desktop-inspect-header">
                <span>{t('anchored.panel.label')}</span>
                <button type="button" className="workbench-desktop-panel-button" aria-label={t('anchored.layout.collapse_right')}
                  onClick={toggleInfo}><PanelRightClose size={16} aria-hidden="true" /></button>
              </div>
              <div className="min-h-0 flex-1"><AnchoredInfoPanel sessionId={sessionId} /></div>
            </div>}
          </Panel>
        )}
      </Group>
      {!threeColumn && leftDrawerOpen && (
        <AnchoredDrawer key="anchored-left-drawer" side="left" label={t('anchored.nav.label')} clamp={clamp}
          onClose={() => setLeftDrawerOpen(false)}>
          <AnchoredLeftNav onCollapse={() => setLeftDrawerOpen(false)} />
        </AnchoredDrawer>
      )}
      {!threeColumn && rightDrawerOpen && (
        <AnchoredDrawer key="anchored-right-drawer" side="right" label={t('anchored.panel.label')} clamp={clamp}
          onClose={() => setRightDrawerOpen(false)}>
          <AnchoredInfoPanel sessionId={sessionId} />
        </AnchoredDrawer>
      )}
    </section>
  );
}

export const ANCHORED_LAYOUT_GEOMETRY = {
  LEFT_DEFAULT, LEFT_MIN, LEFT_MAX, LEFT_COLLAPSED, CENTER_MIN,
  RIGHT_DEFAULT, RIGHT_MIN, RIGHT_MAX, RIGHT_COLLAPSED, THREE_COLUMN_MIN,
};
