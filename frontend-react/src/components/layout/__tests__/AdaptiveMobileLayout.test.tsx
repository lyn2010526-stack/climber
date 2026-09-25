import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../AdaptiveMobileLayout';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

function renderLayout(onNavigate = vi.fn()) {
  render(
    <AdaptiveMobileLayout currentPage="chat" onNavigate={onNavigate}>
      <div>content</div>
    </AdaptiveMobileLayout>,
  );
  return onNavigate;
}

describe('AdaptiveMobileLayout navigation', () => {
  it('shows only mobile-adapted entries in the more sheet', () => {
    const onNavigate = renderLayout();
    fireEvent.click(screen.getByRole('button', { name: /more/i }));
    const sheet = screen.getByRole('dialog');
    const buttons = Array.from(sheet.querySelectorAll('button')).map((b) => b.textContent);
    expect(buttons.some((t) => t?.includes('Agents'))).toBe(true);
    expect(buttons.some((t) => t?.includes('Settings'))).toBe(true);
    expect(buttons.some((t) => t?.includes('Cluster'))).toBe(true);
    expect(buttons.some((t) => t?.toLowerCase().includes('workflows'))).toBe(false);
    expect(buttons.some((t) => t?.toLowerCase().includes('traces'))).toBe(false);
    expect(buttons.some((t) => t?.toLowerCase().includes('terminal'))).toBe(false);
    expect(buttons.some((t) => t?.toLowerCase().includes('eval'))).toBe(false);
    expect(buttons.some((t) => t?.toLowerCase().includes('api key'))).toBe(false);
  });

  it('navigates to an adapted page from the more sheet', () => {
    const onNavigate = renderLayout();
    fireEvent.click(screen.getByRole('button', { name: /more/i }));
    fireEvent.click(screen.getByRole('button', { name: /settings/i }));
    expect(onNavigate).toHaveBeenCalledWith('settings');
  });
});
