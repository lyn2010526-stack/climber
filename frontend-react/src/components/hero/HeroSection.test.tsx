import { readFileSync } from 'node:fs';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { CLIMBER_MARK } from '../brand/ClimberMark';
import { HeroSection } from './HeroSection';
import { hasHeroIntroPlayed, resetHeroIntroForTests } from './heroIntro';

const SUBTITLE = 'Start from one conversation and direct your agent cluster through every climb.';

beforeEach(async () => {
  resetHeroIntroForTests();
  await i18n.changeLanguage('en');
});

afterEach(() => {
  cleanup();
  window.history.replaceState(null, '', '/');
  vi.restoreAllMocks();
});

describe('HeroSection', () => {
  it('renders the brand mark, product name, value proposition and all three actions', () => {
    render(<HeroSection />);

    const hero = screen.getByRole('region', { name: 'Climber hero section' });
    expect(hero).toHaveAttribute('data-hero-intro', 'play');

    expect(screen.getByRole('heading', { level: 1, name: 'Climber' })).toBeInTheDocument();
    expect(screen.getByText(SUBTITLE)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start a conversation' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View agents' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Settings' })).toBeInTheDocument();

    expect(hero.querySelector('[data-hero-item="mark"] polyline')).toHaveAttribute('points', CLIMBER_MARK.ridge);
    expect(hero.querySelector('.hero-glow')).not.toBeNull();
    expect(hero.querySelector('.hero-grid')).not.toBeNull();
    expect(hero.querySelector('.hero-watermark polyline')).toHaveAttribute('points', CLIMBER_MARK.ridge);
  });

  it('plays the staggered intro once, then repeats instantly on the next visit', async () => {
    const first = render(<HeroSection />);
    const firstMark = document.querySelector('[data-hero-item="mark"]') as HTMLElement;
    expect(firstMark.style.opacity).toBe('0');

    await waitFor(() => {
      const mark = document.querySelector('[data-hero-item="mark"]') as HTMLElement;
      expect(mark.style.opacity).toBe('1');
    }, { timeout: 3000 });

    first.unmount();
    expect(hasHeroIntroPlayed()).toBe(true);

    render(<HeroSection />);
    expect(screen.getByRole('region', { name: 'Climber hero section' })).toHaveAttribute('data-hero-intro', 'instant');
    const repeatMark = document.querySelector('[data-hero-item="mark"]') as HTMLElement;
    expect(repeatMark.style.opacity).not.toBe('0');
    expect(screen.getByRole('button', { name: 'Start a conversation' })).toBeVisible();
  });

  it('routes the primary CTA to chat and the secondary actions to agents and settings', () => {
    render(<HeroSection />);

    fireEvent.click(screen.getByRole('button', { name: 'Start a conversation' }));
    expect(window.location.hash).toBe('#chat');

    fireEvent.click(screen.getByRole('button', { name: 'View agents' }));
    expect(window.location.hash).toBe('#agents');

    fireEvent.click(screen.getByRole('button', { name: 'Settings' }));
    expect(window.location.hash).toBe('#settings');
  });

  it('keeps the ambient decor to transform and opacity animations with a reduced-motion override', () => {
    const styles = readFileSync('src/components/hero/hero.css', 'utf8');
    const keyframeBlocks = styles.match(/@keyframes[^{]+\{[\s\S]*?\n\}/g) ?? [];
    expect(keyframeBlocks.length).toBe(2);

    for (const block of keyframeBlocks) {
      const props = [...block.matchAll(/^\s+(transform|opacity|[a-z-]+):/gm)].map((match) => match[1]);
      expect(props.length).toBeGreaterThan(0);
      for (const prop of props) {
        expect(['transform', 'opacity']).toContain(prop);
      }
    }

    expect(styles).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{\s*\.hero-glow,\s*\.hero-watermark\s*\{\s*animation: none;/);
    expect(styles).not.toMatch(/url\(/);
  });
});
