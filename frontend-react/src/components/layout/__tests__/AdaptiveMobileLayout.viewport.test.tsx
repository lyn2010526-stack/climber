import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../AdaptiveMobileLayout';
import i18n from '../../../i18n';

// Mirrors the shell stylesheet: the navigation strip is 64px tall and the
// content area reserves that strip plus 12px of breathing room.
const NAV_HEIGHT = 64;
const CONTENT_GAP = 12;
const RESERVED = NAV_HEIGHT + CONTENT_GAP;

class FakeVisualViewport extends EventTarget {
  height: number;
  offsetTop: number;
  scale: number;

  constructor(height: number, offsetTop = 0, scale = 1) {
    super();
    this.height = height;
    this.offsetTop = offsetTop;
    this.scale = scale;
  }
}

let layoutHeight = 768;
let viewport: FakeVisualViewport;

function setLayoutHeight(height: number) {
  layoutHeight = height;
  Object.defineProperty(window, 'innerHeight', { value: height, configurable: true, writable: true });
}

function openKeyboard(viewportHeight: number, offsetTop = 0) {
  act(() => {
    viewport.height = viewportHeight;
    viewport.offsetTop = offsetTop;
    viewport.dispatchEvent(new Event('resize'));
  });
}

function closeKeyboard() {
  act(() => {
    viewport.height = layoutHeight;
    viewport.offsetTop = 0;
    viewport.dispatchEvent(new Event('resize'));
  });
}

function shell(): HTMLElement {
  return document.querySelector('.mobile-workspace-shell') as HTMLElement;
}

function content(): HTMLElement {
  return document.getElementById('main-content') as HTMLElement;
}

/** The shell measures inside an animation frame, so let that frame settle. */
async function settle(): Promise<void> {
  await act(async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
  });
}

/** Bottom edge of the composer, derived from the shell height and its content reserve. */
function composerBottom(): number {
  const reserve = content().style.paddingBottom
    ? Number.parseFloat(content().style.paddingBottom)
    : RESERVED;
  return shellHeight() - reserve;
}

/**
 * Effective shell height. With the keyboard closed the browser owns the height
 * of the fixed shell, so the layout viewport is the closest observable value.
 */
function shellHeight(): number {
  return shell().style.height ? Number.parseFloat(shell().style.height) : layoutHeight;
}

/** Top edge of the fixed navigation, which is pinned to the layout viewport. */
function navTop(): number {
  return layoutHeight - NAV_HEIGHT;
}

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
  setLayoutHeight(768);
  viewport = new FakeVisualViewport(layoutHeight);
  vi.stubGlobal('visualViewport', viewport);
});

afterEach(() => {
  vi.unstubAllGlobals();
  Object.defineProperty(window, 'innerHeight', { value: 768, configurable: true, writable: true });
});

describe('AdaptiveMobileLayout keyboard and safe-area geometry', () => {
  it('keeps the composer clear of the navigation and stops exactly at the keyboard edge', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();

    // Keyboard closed: no inline sizing, so the browser keeps the reserved
    // navigation strip and the composer sits above the navigation.
    expect(shell().style.height).toBe('');
    expect(content().style.paddingBottom).toBe('');
    expect(composerBottom()).toBeLessThanOrEqual(navTop());

    openKeyboard(420);
    await settle();
    expect(shell().style.height).toBe('420px');
    // The navigation is behind the keyboard, so its strip is released.
    expect(content().style.paddingBottom).toBe('12px');
    expect(composerBottom()).toBe(420 - CONTENT_GAP);
    expect(composerBottom()).toBeLessThanOrEqual(420);

    closeKeyboard();
    await settle();
    expect(shell().style.height).toBe('');
    expect(content().style.paddingBottom).toBe('');
    expect(composerBottom()).toBeLessThanOrEqual(navTop());
  });

  it('follows the browser while the toolbar resizes the layout viewport', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    act(() => {
      viewport.height = 700;
      setLayoutHeight(700);
      viewport.dispatchEvent(new Event('resize'));
    });
    await settle();
    // Collapsing the toolbar changes the layout viewport, so CSS still owns the
    // height and the navigation reserve is untouched.
    expect(shell().style.height).toBe('');
    expect(content().style.paddingBottom).toBe('');
    expect(composerBottom()).toBe(700 - RESERVED);
    expect(composerBottom()).toBeLessThanOrEqual(700 - NAV_HEIGHT);
  });

  it('accounts for a scrolled visual viewport so the shell covers the visible band', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    openKeyboard(380, 24);
    await settle();
    // iOS can scroll the layout viewport when the keyboard opens; the shell has
    // to reach the visual viewport bottom, not the layout viewport bottom.
    expect(shell().style.height).toBe('404px');
    expect(composerBottom()).toBe(380 + 24 - CONTENT_GAP);
  });

  it('never collapses the shell while the keyboard animates', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    openKeyboard(40);
    await settle();
    expect(shell().style.height).toBe('120px');
  });

  it('ignores a visual viewport that reports more room than the layout viewport', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    openKeyboard(1200);
    await settle();
    expect(shell().style.height).toBe('');
    expect(content().style.paddingBottom).toBe('');
  });

  it('hands sizing back to css while pinch zoomed and remeasures afterwards', async () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    openKeyboard(420);
    await settle();
    expect(shell().style.height).toBe('420px');

    act(() => {
      viewport.scale = 2;
      viewport.dispatchEvent(new Event('resize'));
    });
    await settle();
    expect(shell().style.height).toBe('');

    act(() => {
      viewport.scale = 1;
      viewport.height = 500;
      viewport.dispatchEvent(new Event('resize'));
    });
    await settle();
    expect(shell().style.height).toBe('500px');
  });

  it('keeps the content box shrinkable so a tall page cannot push the shell open', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    expect(content().style.minHeight).toBe('0px');
  });

  it('removes every viewport listener on unmount', () => {
    const removeViewport = vi.spyOn(viewport, 'removeEventListener');
    const removeWindow = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    unmount();
    expect(removeViewport).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(removeViewport).toHaveBeenCalledWith('scroll', expect.any(Function));
    expect(removeWindow).toHaveBeenCalledWith('resize', expect.any(Function));
  });

  it('falls back to the layout viewport when visualViewport is unavailable', async () => {
    vi.unstubAllGlobals();
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    await settle();
    expect(shell().style.height).toBe('');
    expect(content().style.paddingBottom).toBe('');
    expect(screen.getByRole('main')).toBe(content());
  });
});
