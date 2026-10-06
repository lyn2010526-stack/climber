import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { HeroSection } from './HeroSection';
import { resetHeroIntroForTests } from './heroIntro';

vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
  matches: query.includes('prefers-reduced-motion'),
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
})));

const SUBTITLE = 'Start from one conversation and direct your agent cluster through every climb.';

beforeEach(async () => {
  resetHeroIntroForTests();
  await i18n.changeLanguage('en');
});

afterEach(() => {
  cleanup();
  window.history.replaceState(null, '', '/');
});

describe('HeroSection reduced motion', () => {
  it('presents every element immediately without the staggered intro', () => {
    render(<HeroSection />);

    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion)');
    expect(screen.getByRole('region', { name: 'Climber hero section' })).toHaveAttribute('data-hero-intro', 'instant');

    for (const item of ['mark', 'title', 'subtitle', 'actions']) {
      const node = document.querySelector(`[data-hero-item="${item}"]`) as HTMLElement;
      expect(node).not.toBeNull();
      expect(node.style.opacity).not.toBe('0');
    }

    expect(screen.getByRole('heading', { level: 1, name: 'Climber' })).toBeVisible();
    expect(screen.getByText(SUBTITLE)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Start a conversation' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'View agents' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Settings' })).toBeVisible();
  });

  it('navigates with the primary CTA under reduced motion as well', () => {
    render(<HeroSection />);

    fireEvent.click(screen.getByRole('button', { name: 'Start a conversation' }));
    expect(window.location.hash).toBe('#chat');
  });
});
