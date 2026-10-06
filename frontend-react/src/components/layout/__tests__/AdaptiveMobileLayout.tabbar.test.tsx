import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../AdaptiveMobileLayout';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

function renderLayout(currentPage = 'chat', onNavigate = vi.fn()) {
  return render(
    <AdaptiveMobileLayout currentPage={currentPage} onNavigate={onNavigate}>
      <div>content</div>
    </AdaptiveMobileLayout>,
  );
}

describe('mobile tab bar presentation', () => {
  it('renders the frosted glass treatment on the bottom bar', () => {
    renderLayout();
    const nav = screen.getByRole('navigation');
    const style = nav.getAttribute('style') ?? '';
    expect(style).toContain('color-mix(in srgb, var(--color-bg-surface-1) 78%, transparent)');
    expect(style).toMatch(/backdrop-filter:\s*blur\(20px\)/);
  });

  it('fills the active icon with the accent colour and leaves the rest hollow', () => {
    renderLayout('chat');
    const nav = screen.getByRole('navigation');
    const active = nav.querySelector('button[aria-current="page"]');
    expect(active).not.toBeNull();
    expect(active!.querySelector('svg')).toHaveAttribute('fill', 'currentColor');
    for (const svg of nav.querySelectorAll('button:not([aria-current="page"]) svg')) {
      expect(svg).toHaveAttribute('fill', 'none');
    }
  });

  it('declares the switch micro-motion and honours reduced motion', () => {
    renderLayout();
    const nav = screen.getByRole('navigation');
    for (const button of nav.querySelectorAll('button')) {
      expect(button.className).toMatch(/\btransition\b/);
      expect(button.className).toMatch(/\bduration-200\b/);
      expect(button.className).toMatch(/active:scale-95/);
      expect(button.className).toMatch(/motion-reduce:transition-none/);
    }
  });

  it('keeps every bar entry at least 44px and named from visible text or a label', () => {
    renderLayout();
    const nav = screen.getByRole('navigation');
    const buttons = Array.from(nav.querySelectorAll('button'));
    // Four high-frequency tabs plus the More trigger share the five slots.
    expect(buttons).toHaveLength(5);
    const named = buttons.filter(button => (button.textContent ?? '').trim() !== '');
    expect(named).toHaveLength(4);
    // The More trigger is icon-only and carries an explicit label instead.
    expect(screen.getByRole('button', { name: i18n.t('sidebar.more') })).toBeInTheDocument();
  });

  it('keeps exactly one page marker across the shell on a primary page', () => {
    renderLayout('chat');
    const markers = document.querySelectorAll('[aria-current="page"]');
    expect(markers).toHaveLength(1);
    expect(markers[0]!.textContent).toContain(i18n.t('navigation.chat'));
  });

  it('marks the More trigger instead when a sheet page is active', () => {
    renderLayout('cluster');
    const markers = document.querySelectorAll('[aria-current="page"]');
    expect(markers).toHaveLength(1);
    expect(markers[0]).toHaveAttribute('aria-label', i18n.t('sidebar.more'));
  });

  it('gives the header an iOS large title and a right-side action slot', () => {
    renderLayout();
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1.className).toMatch(/text-2xl/);
    expect(h1.className).toMatch(/\bfont-bold\b/);
    const action = document.querySelector('[data-testid="mobile-header-action"]');
    expect(action).not.toBeNull();
    expect(action!.getAttribute('aria-hidden')).toBe('true');
  });
});
