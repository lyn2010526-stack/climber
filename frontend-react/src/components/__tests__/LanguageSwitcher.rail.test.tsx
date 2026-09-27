import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LanguageSwitcher } from '../LanguageSwitcher';
import i18n from '../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('LanguageSwitcher in the collapsed rail', () => {
  it('keeps the current language in the accessible name when icon-only', () => {
    render(<LanguageSwitcher showIcon iconOnly />);
    // The rail is 64px, so the visible name cannot survive. It has to move into
    // the name, or a screen reader user learns only that "a thing" was pressed.
    expect(screen.getByRole('button', { name: /English/ })).toBeInTheDocument();
    expect(screen.getByRole('button').textContent).toBe('');
  });

  it('meets the 44px touch target when icon-only', () => {
    render(<LanguageSwitcher showIcon iconOnly />);
    // jsdom reports a zero box, so the guarantee is asserted on the classes
    // that set the floor. The pixel measurement lives in the axe sweep.
    const button = screen.getByRole('button');
    expect(button.className).toMatch(/\bmin-h-11\b/);
    expect(button.className).toMatch(/\bmin-w-11\b/);
  });

  it('keeps the caret decorative so the name is not doubled up', () => {
    const { container } = render(<LanguageSwitcher showIcon iconOnly />);
    // The inline caret svg is the one that is not the Languages icon.
    const svgs = container.querySelectorAll('button svg');
    for (const svg of svgs) expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows the language and the caret in the expanded sidebar', () => {
    render(<LanguageSwitcher showIcon compact />);
    const button = screen.getByRole('button');
    expect(button.textContent).toContain('English');
    // The expanded rail has room, so the name stays visible.
    expect(button.className).not.toMatch(/\bmin-w-11\b/);
  });
});
