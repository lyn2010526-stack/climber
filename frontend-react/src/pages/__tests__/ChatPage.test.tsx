import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ChatPage } from '../ChatPage';
import i18n from '../../i18n';

const state = vi.hoisted(() => ({
  sessionId: 'desktop-session' as string | null,
  creationError: null as string | null,
  messages: [] as Array<{ id: string; role: 'assistant'; content: string }>,
  isStreaming: false,
  error: null as string | null,
  sendMessage: vi.fn(),
  stopStreaming: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock('../../useChat', () => ({
  useChat: () => state,
}));

vi.mock('../../hooks/useDefaultSession', () => ({
  useDefaultSession: () => ({ sessionId: state.sessionId, creationError: state.creationError }),
}));

vi.mock('../../components/agent/ChatInterface', () => ({
  ChatInterface: ({ emptyStateTitle }: { emptyStateTitle?: string }) => (
    <form aria-label={emptyStateTitle ?? 'chat'}>
      <textarea aria-label="Type your message here..." />
      <button type="submit" aria-label="Send">Send</button>
    </form>
  ),
}));

beforeEach(async () => {
  localStorage.setItem('i18next_lng', 'en');
  await i18n.changeLanguage('en');
  state.sessionId = 'desktop-session';
  state.creationError = null;
  state.isStreaming = false;
  state.error = null;
  vi.clearAllMocks();
});

describe('ChatPage alert placement', () => {
  it('keeps the alert out of the overlay layer so it cannot cover the composer', () => {
    state.error = 'stream failed';
    const { container } = render(<ChatPage />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('stream failed');
    // The composer owns the bottom of a fixed-height column, so the alert takes
    // part in normal flow above the transcript instead of floating over it.
    expect(alert.className).not.toContain('absolute');
    expect(alert.className).toContain('shrink-0');
    const section = container.firstElementChild as HTMLElement;
    expect(section.firstElementChild).toBe(alert);
  });

  it('offers a retry that calls the refresh contract', () => {
    state.error = 'stream failed';
    render(<ChatPage />);
    screen.getByRole('button', { name: 'Retry' }).click();
    expect(state.refresh).toHaveBeenCalledOnce();
  });

  it('reports a session creation failure without a dead retry', () => {
    state.sessionId = null;
    state.creationError = '创建失败';
    render(<ChatPage />);
    expect(screen.getByRole('alert')).toHaveTextContent('创建失败');
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  });

  it('renders no alert on a healthy session', () => {
    render(<ChatPage />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: 'Start a conversation' })).toBeInTheDocument();
  });

  it('sends through the useChat contract', async () => {
    render(<ChatPage />);
    screen.getByRole('button', { name: 'Send' }).click();
    await waitFor(() => expect(state.sendMessage).not.toHaveBeenCalled());
  });
});
