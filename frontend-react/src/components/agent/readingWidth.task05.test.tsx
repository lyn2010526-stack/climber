import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ChatInterface } from './ChatInterface';
import { getReadingWidthClass, hasParallelToolContent, MAXIMIZE_SPACE_KEY } from './readingWidth';

vi.mock('../../api', () => ({ api: { submitFeedback: vi.fn() } }));

const single = [
  { id: 'u1', role: 'user' as const, content: 'Review this repository' },
  { id: 'a1', role: 'assistant' as const, content: 'The parser is lenient.' },
];

const parallel = [
  ...single,
  {
    id: 'a2',
    role: 'assistant' as const,
    content: 'Both branches finished.',
    toolCalls: [
      { id: 't1', name: 'read_file', arguments: {}, status: 'success' as const, result: 'a' },
      { id: 't2', name: 'read_file', arguments: {}, status: 'success' as const, result: 'b' },
    ],
  },
];

/** The width a rendered row or composer actually carries. */
function widthClassOf(element: Element | null): string {
  const classes = element?.className.split(' ') ?? [];
  return classes.filter(name => name.includes('max-w')).join(' ');
}

beforeEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage('zh-CN');
});

describe('reading column tiers', () => {
  it('returns one width per content type and lets the preference win', () => {
    const normal = getReadingWidthClass();
    const wide = getReadingWidthClass({ hasParallelContent: true });
    const full = getReadingWidthClass({ fullWidth: true, hasParallelContent: true });

    expect(normal).toContain('md:max-w-3xl');
    expect(normal).toContain('xl:max-w-4xl');
    expect(wide).toContain('md:max-w-[58rem]');
    expect(wide).toContain('xl:max-w-[70rem]');
    expect(full).toContain('max-w-full');
    expect(full).not.toContain('md:max-w-3xl');
    // A switch animates, so a toggle reads as the same column growing.
    for (const tier of [normal, wide, full]) {
      expect(tier).toContain('transition-[max-width]');
      expect(tier).toContain('motion-reduce:transition-none');
    }
  });

  it('treats more than one tool call on a turn as parallel content', () => {
    expect(hasParallelToolContent(0)).toBe(false);
    expect(hasParallelToolContent(undefined)).toBe(false);
    expect(hasParallelToolContent(1)).toBe(false);
    expect(hasParallelToolContent(2)).toBe(true);
  });

  it('widens only the turn that carries parallel tool output and keeps the composer with it', () => {
    const { container } = render(<ChatInterface messages={parallel} onSend={vi.fn()} />);
    const rows = container.querySelectorAll('[data-transcript] > div');
    expect(widthClassOf(rows[0]!)).toContain('md:max-w-3xl');
    expect(widthClassOf(rows[rows.length - 1]!)).toContain('md:max-w-[58rem]');
    // The composer follows the widest turn, so prompt and reply stay aligned.
    const form = screen.getByRole('textbox').closest('form')!;
    expect(widthClassOf(form.firstElementChild)).toContain('md:max-w-[58rem]');
  });

  it('leaves an ordinary conversation on the prose measure', () => {
    const { container } = render(<ChatInterface messages={single} onSend={vi.fn()} />);
    const form = screen.getByRole('textbox').closest('form')!;
    expect(widthClassOf(form.firstElementChild)).toContain('md:max-w-3xl');
    expect(widthClassOf(container.querySelector('[data-transcript] > div'))).toContain('md:max-w-3xl');
  });
});

describe('persisted full-width preference', () => {
  it('starts on the content tier, switches the whole stage and survives a remount', () => {
    const { container, unmount } = render(<ChatInterface messages={parallel} onSend={vi.fn()} />);
    const toggle = screen.getByRole('button', { name: i18n.t('chat.wide_column') });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(localStorage.getItem(MAXIMIZE_SPACE_KEY)).toBeNull();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(localStorage.getItem(MAXIMIZE_SPACE_KEY)).toBe('true');
    const form = screen.getByRole('textbox').closest('form')!;
    expect(widthClassOf(form.firstElementChild)).toContain('max-w-full');
    expect(widthClassOf(container.querySelector('[data-transcript] > div'))).toContain('max-w-full');

    unmount();
    render(<ChatInterface messages={parallel} onSend={vi.fn()} />);
    const restored = screen.getByRole('button', { name: i18n.t('chat.wide_column') });
    expect(restored).toHaveAttribute('aria-pressed', 'true');
    const restoredForm = screen.getByRole('textbox').closest('form')!;
    expect(widthClassOf(restoredForm.firstElementChild)).toContain('max-w-full');
  });
});

describe('editing claims the whole column', () => {
  it('drops the fitted-bubble cap for the message being edited', () => {
    const { container } = render(<ChatInterface messages={single} onSend={vi.fn()} />);
    // In view mode a user turn is a fitted bubble, capped so a short question
    // never spans the column.
    const userRow = container.querySelectorAll('[data-transcript] > div')[0]!;
    expect(userRow.textContent).toContain('Review this repository');
    const fitted = userRow.firstElementChild!;
    expect(fitted.classList.contains('sm:max-w-[85%]')).toBe(true);
    expect(fitted.classList.contains('max-w-[90%]')).toBe(true);

    fireEvent.click(screen.getAllByRole('button', { title: '编辑' })[0]!);
    const editor = screen.getByRole('textbox', { name: i18n.t('chat.edit_message') });
    expect(editor).toHaveValue('The parser is lenient.');
    // The editing box takes the whole column: a box clipped to 85% of it
    // hides the text the user is rewriting.
    const editingBox = editor.closest('div')!.parentElement!;
    expect(editingBox.classList.contains('w-full')).toBe(true);
    expect(editingBox.classList.contains('max-w-[90%]')).toBe(false);
    expect(editingBox.classList.contains('sm:max-w-[85%]')).toBe(false);
  });
});
