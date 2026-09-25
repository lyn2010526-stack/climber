import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Button } from '../Button';
import { Badge } from '../Badge';
import { ConfirmDialog } from '../Modal';
import { StreamingCursor } from '../../chat/StreamingCursor';
import css from '../../../index.css?raw';
import markdown from '../../chat/MarkdownRenderer.tsx?raw';
import bubble from '../../chat/MessageBubble.tsx?raw';
import content from '../../chat/MessageContent.tsx?raw';
import modal from '../Modal.tsx?raw';
import card from '../Card.tsx?raw';
import mobile from '../../mobile/MobileChatInterface.tsx?raw';
import chart from '../Chart.tsx?raw';
import toast from '../Toast.tsx?raw';

afterEach(cleanup);

describe('Slate presentation contract', () => {
  it.each(Object.entries({ css, markdown, bubble, content, modal, card, mobile, chart, toast }))(
    '%s keeps legacy purple and decorative cyan out of presentation',
    (_name, source) => {
      expect(source).not.toMatch(/#(?:5e6ad2|6e7ae3|8b5cf6|6366f1|a78bfa|c4b5fd|22d3ee)|rgba?\(\s*(?:94,\s*106,\s*210|139,\s*92,\s*246|34,\s*211,\s*238)|(?:from|to|bg|text)-(?:purple|violet|indigo|cyan)-/i);
      expect(source).not.toMatch(/(?:hover|active):scale-/);
    },
  );

  it('defines every referenced shadow token and retains modal depth', () => {
    const definitions = new Set([...css.matchAll(/(--shadow-[\w-]+)\s*:/g)].map(match => match[1]));
    const references = [...css.matchAll(/var\((--shadow-[\w-]+)\)/g)].map(match => match[1]);
    expect(references.length).toBeGreaterThan(0);
    for (const name of references) expect(definitions.has(name), name).toBe(true);
    expect(css).toMatch(/\.modal-content\s*\{[^}]*box-shadow:\s*var\(--shadow-xl\)/);
    expect(css).toMatch(/--shadow-xl:\s*0 24px/);
    expect(css).not.toMatch(/\*\s*\{[^}]*box-shadow:\s*none/);
  });

  it('preserves semantic colors and reduced-motion coverage for pseudo-elements', () => {
    expect(css).toMatch(/--color-success:\s*#10B981/);
    expect(css).toMatch(/--color-error:\s*#EF4444/);
    expect(css).toMatch(/--color-warning:\s*#F59E0B/);
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\*,\s*\*::before,\s*\*::after\s*\{[^}]*animation-duration:\s*0\.01ms !important;[^}]*transition-duration:\s*0\.01ms !important;/);
    expect(css).toMatch(/@keyframes statusPulse/);
    expect(css).toMatch(/\.status-dot\.running\s*\{[^}]*animation:\s*statusPulse/);
  });

  it('retains loading feedback and prevents repeat submission', () => {
    const onClick = vi.fn();
    const { container, rerender } = render(<Button loading onClick={onClick}>Run</Button>);
    const button = screen.getByRole('button', { name: 'Run' });
    expect(button).toBeDisabled();
    expect(container.querySelector('.animate-spin')).not.toBeNull();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
    rerender(<Button onClick={onClick}>Run</Button>);
    fireEvent.click(screen.getByRole('button', { name: 'Run' }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('retains semantic badge colors alongside the neutral primary badge', () => {
    render(<><Badge variant="primary">Primary</Badge><Badge variant="success">Success</Badge><Badge variant="destructive">Error</Badge></>);
    expect(screen.getByText('Primary')).toHaveClass('border-[var(--color-border-accent)]');
    expect(screen.getByText('Success')).toHaveClass('text-[var(--color-success)]');
    expect(screen.getByText('Error')).toHaveClass('text-[var(--color-error)]');
  });

  it('uses a solid streaming cursor with a running indicator', () => {
    const { container } = render(<StreamingCursor />);
    expect(container.firstElementChild).toHaveStyle({ backgroundColor: 'var(--color-accent-foreground)' });
    expect(container.firstElementChild).toHaveStyle({ animation: 'cursorBlink 1s step-end infinite' });
    expect(container.innerHTML).not.toContain('gradient');
  });

  it('uses themed confirmation and preserves danger styling', () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    const { rerender } = render(<ConfirmDialog open onConfirm={onConfirm} onClose={onClose} title="Confirm action" />);
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('bg-[var(--color-accent)]');
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(onConfirm).toHaveBeenCalledOnce();
    rerender(<ConfirmDialog open variant="danger" onConfirm={onConfirm} onClose={onClose} title="Confirm action" />);
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('bg-[#EF4444]');
  });
});
