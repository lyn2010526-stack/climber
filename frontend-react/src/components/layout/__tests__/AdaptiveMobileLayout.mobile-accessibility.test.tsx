import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../AdaptiveMobileLayout';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

describe('mobile navigation accessibility', () => {
  it('moves focus into the sheet and restores it after Escape', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    const trigger = screen.getByRole('button', { name: /more/i });
    fireEvent.click(trigger);
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('wraps Tab in both directions and dismisses an outside pointer press', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    fireEvent.click(screen.getByRole('button', { name: /more/i }));
    const sheet = screen.getByRole('dialog');
    const controls = Array.from(sheet.querySelectorAll('button')) as HTMLButtonElement[];
    const close = controls[0]!;
    const last = controls.at(-1)!;
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(last).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: false });
    expect(close).toHaveFocus();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
