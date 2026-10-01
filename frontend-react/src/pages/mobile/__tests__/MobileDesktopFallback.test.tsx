import { describe, expect, it, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MobileDesktopFallback } from '../MobileDesktopFallback';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('MobileDesktopFallback', () => {
  it('explains why a desktop surface has a mobile fallback', () => {
    render(<MobileDesktopFallback title="Agents" />);
    expect(screen.getByRole('heading', { name: 'Agents' })).toBeInTheDocument();
    expect(screen.getByText(i18n.t('mobile.fallback.card_description'))).toBeInTheDocument();
  });

  it('ends in a shared empty state and an open chat action', () => {
    render(<MobileDesktopFallback title="Agents" />);
    expect(screen.getByRole('heading', { name: i18n.t('mobile.fallback.empty_title') })).toBeInTheDocument();
    const action = screen.getByRole('button', { name: i18n.t('mobile.open_chat') });
    expect(action.className).toMatch(/min-h-11/);
  });

  it('routes the action back to chat through the hash router', () => {
    window.location.hash = '';
    render(<MobileDesktopFallback title="Agents" />);
    fireEvent.click(screen.getByRole('button', { name: i18n.t('mobile.open_chat') }));
    expect(window.location.hash).toBe('#chat');
  });
});
