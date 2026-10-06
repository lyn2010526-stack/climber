import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { useChat } from '../../useChat';
import { resetAnchoredStore } from '../../store/anchored';
import { useSmoothScroll } from '../../hooks/useSmoothScroll';
import { AnchoredChatColumn } from './AnchoredChatColumn';
import type { ChatMessage } from '../../store/types';

vi.mock('../../useChat', () => ({ useChat: vi.fn() }));
vi.mock('../../api', () => ({
  api: {
    getStats: vi.fn().mockResolvedValue({}),
    getPermissionConfig: vi.fn().mockResolvedValue({ mode: 'default' }),
    updatePermissionConfig: vi.fn(),
  },
}));
vi.mock('./AnchoredComposer', () => ({
  AnchoredComposer: () => <div data-testid="anchored-composer" />,
}));
vi.mock('./AnchoredMessageFlow', () => ({ AnchoredMessageFlow: () => null }));
vi.mock('../../hooks/useSmoothScroll', () => ({
  useSmoothScroll: vi.fn(() => ({ enabled: false, scrollTo: vi.fn(), stop: vi.fn(), start: vi.fn() })),
}));

const chat = {
  messages: [],
  isStreaming: false,
  error: null,
  sendMessage: vi.fn(),
  stopStreaming: vi.fn(),
  retry: vi.fn(),
  clear: vi.fn(),
  refresh: vi.fn(),
  isLoading: false,
  inputs: [],
  runtimeReport: null,
  submitInput: vi.fn(),
  retryInput: vi.fn(),
  resumeInputs: vi.fn(),
  resumePending: false,
  resumeFeedback: null,
  startInputs: vi.fn(),
} satisfies ReturnType<typeof useChat>;

const message = (id: string) => ({ id, role: 'user', content: 'hello' }) as unknown as ChatMessage;

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('zh-CN');
  resetAnchoredStore();
  vi.mocked(useChat).mockReturnValue({ ...chat });
});

it('wires smooth scrolling at window level without binding the message container', () => {
  render(<AnchoredChatColumn sessionId="session-1" />);
  expect(useSmoothScroll).toHaveBeenCalledWith();
  expect(screen.getByTestId('anchored-message-scroll')).toBeInTheDocument();
});

it('wraps the welcome state in a scroll reveal container', () => {
  render(<AnchoredChatColumn sessionId="session-1" />);
  const reveal = screen.getByTestId('anchored-welcome-reveal');
  expect(reveal).toContainElement(screen.getByTestId('anchored-welcome'));
  expect(reveal.style.opacity).toBe('');
});

it('wraps the conversation region in a scroll reveal container', () => {
  vi.mocked(useChat).mockReturnValue({ ...chat, messages: [message('m1')] } as ReturnType<typeof useChat>);
  render(<AnchoredChatColumn sessionId="session-1" />);
  const reveal = screen.getByTestId('anchored-conversation-reveal');
  expect(reveal).toContainElement(screen.getByTestId('anchored-conversation'));
  expect(reveal.style.opacity).toBe('');
});

it('keeps following the message bottom across updates while untouched', () => {
  const { rerender } = render(<AnchoredChatColumn sessionId="session-1" />);
  const scroller = screen.getByTestId('anchored-message-scroll');
  const heightSpy = vi.spyOn(scroller, 'scrollHeight', 'get').mockReturnValue(500);
  vi.mocked(useChat).mockReturnValue({ ...chat, messages: [message('m1')] } as ReturnType<typeof useChat>);
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  expect(scroller.scrollTop).toBe(500);
  heightSpy.mockReturnValue(600);
  vi.mocked(useChat).mockReturnValue({ ...chat, messages: [message('m1'), message('m2')] } as ReturnType<typeof useChat>);
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  expect(scroller.scrollTop).toBe(600);
});

it('stops following the bottom once the reader scrolls away', () => {
  const { rerender } = render(<AnchoredChatColumn sessionId="session-1" />);
  const scroller = screen.getByTestId('anchored-message-scroll');
  vi.spyOn(scroller, 'scrollHeight', 'get').mockReturnValue(500);
  vi.mocked(useChat).mockReturnValue({ ...chat, messages: [message('m1')] } as ReturnType<typeof useChat>);
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  expect(scroller.scrollTop).toBe(500);
  scroller.scrollTop = 100;
  fireEvent.scroll(scroller);
  vi.mocked(useChat).mockReturnValue({ ...chat, messages: [message('m1'), message('m2')] } as ReturnType<typeof useChat>);
  rerender(<AnchoredChatColumn sessionId="session-1" />);
  expect(scroller.scrollTop).toBe(100);
});
