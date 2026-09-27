import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AdaptiveMobileLayout } from '../AdaptiveMobileLayout';
import i18n from '../../../i18n';

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
});

function openMoreSheet() {
  fireEvent.click(screen.getByRole('button', { name: /more/i }));
  return screen.getByRole('dialog');
}

function sheetLabels(): string[] {
  return Array.from(openMoreSheet().querySelectorAll('.mobile-more-grid button'))
    .map(button => button.textContent ?? '');
}

function title(): string {
  return screen.getByRole('heading', { level: 1 }).textContent ?? '';
}

describe('AdaptiveMobileLayout usable mobile destinations', () => {
  it('lists only pages that render a surface inside the mobile shell', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    const labels = sheetLabels().map(label => label.toLowerCase());
    expect(labels.some(label => label.includes('agents'))).toBe(true);
    expect(labels.some(label => label.includes('cluster'))).toBe(true);
    expect(labels.some(label => label.includes('api key'))).toBe(true);
    expect(labels.some(label => label.includes('settings'))).toBe(true);
    // Desktop-only destinations stay out of the sheet.
    expect(labels.some(label => label.includes('crews'))).toBe(false);
    expect(labels.some(label => label.includes('api access'))).toBe(false);
    expect(labels.some(label => label.includes('workflows'))).toBe(false);
    expect(labels.some(label => label.includes('traces'))).toBe(false);
  });

  it('keeps the four primary destinations in the bottom bar', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    const nav = screen.getByRole('navigation');
    const items = Array.from(nav.querySelectorAll('button')).map(button => button.textContent ?? '');
    expect(items).toHaveLength(5);
    expect(items.some(item => item.toLowerCase().includes('dashboard'))).toBe(true);
    expect(items.some(item => item.toLowerCase().includes('chat'))).toBe(true);
    expect(items.some(item => item.toLowerCase().includes('factory'))).toBe(true);
    expect(items.some(item => item.toLowerCase().includes('tasks'))).toBe(true);
  });

  it('sends a desktop-only destination back to the conversation entry', async () => {
    const onNavigate = vi.fn();
    render(<AdaptiveMobileLayout currentPage="crews" onNavigate={onNavigate}><div>content</div></AdaptiveMobileLayout>);
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith('chat'));
    expect(title().toLowerCase()).toContain('chat');
  });

  it('requests the fallback once even while the router keeps the old page', async () => {
    const onNavigate = vi.fn();
    const { rerender } = render(<AdaptiveMobileLayout currentPage="terminal" onNavigate={onNavigate}><div>content</div></AdaptiveMobileLayout>);
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith('chat'));
    rerender(<AdaptiveMobileLayout currentPage="terminal" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    rerender(<AdaptiveMobileLayout currentPage="terminal" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });

  it('keeps a usable mobile destination untouched and marks it active', () => {
    const onNavigate = vi.fn();
    render(<AdaptiveMobileLayout currentPage="cluster" onNavigate={onNavigate}><div>content</div></AdaptiveMobileLayout>);
    expect(onNavigate).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /more/i })).toHaveAttribute('aria-current', 'page');
  });

  it('marks the primary entry active and clears the sheet marker on chat', () => {
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={vi.fn()}><div>content</div></AdaptiveMobileLayout>);
    expect(screen.getByRole('button', { name: /^chat$/i })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: /more/i })).not.toHaveAttribute('aria-current');
  });

  it('navigates from the sheet and closes it', () => {
    const onNavigate = vi.fn();
    render(<AdaptiveMobileLayout currentPage="chat" onNavigate={onNavigate}><div>content</div></AdaptiveMobileLayout>);
    openMoreSheet();
    fireEvent.click(screen.getByRole('button', { name: /settings/i }));
    expect(onNavigate).toHaveBeenCalledWith('settings');
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
