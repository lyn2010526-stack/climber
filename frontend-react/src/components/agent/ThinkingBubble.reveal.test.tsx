import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import type { Message } from '../../useChat';
import { setTypewriterMode } from './typewriterConfig';
import { ThinkingBubble } from './ThinkingBubble';

const message: Message = { id: 'a-1', role: 'assistant', content: 'Typed answer', reasoning: 'Reported public summary' };

let frames: FrameRequestCallback[];

beforeEach(async () => {
  frames = [];
  setTypewriterMode('off');
  await i18n.changeLanguage('zh-CN');
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    frames.push(callback);
    return frames.length;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => {
    frames[id - 1] = Function.prototype as unknown as FrameRequestCallback;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ThinkingBubble reveal behavior', () => {
  it('keeps the public reasoning summary collapsed while streaming', () => {
    render(<ThinkingBubble message={message} active />);
    expect(screen.getByRole('button', { name: '公开推理摘要' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Reported public summary')).toBeNull();
  });

  it('keeps reasoning collapsed when idle', () => {
    render(<ThinkingBubble message={message} active={false} />);
    expect(screen.getByRole('button', { name: '公开推理摘要' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Reported public summary')).toBeNull();
  });

  it('defaults to the full answer when the typewriter is off', () => {
    render(<ThinkingBubble message={message} active />);
    expect(screen.getByText('Typed answer')).toBeVisible();
    expect(frames).toHaveLength(0);
  });
});
