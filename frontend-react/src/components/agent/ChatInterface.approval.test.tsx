import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { api, ApiRequestError } from '../../api';
import { ChatInterface } from './ChatInterface';

vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  api: { submitFeedback: vi.fn(), resolvePermission: vi.fn() },
}));

const messages = [{
  id: 'turn-1', role: 'assistant' as const, content: 'Listing files',
  toolCalls: [{
    id: 'call-1', name: 'read_file', arguments: { path: '/etc/hosts' },
    requiresApproval: true, action: 'file_read' as const,
    description: 'Read /etc/hosts', path: '/etc/hosts', severity: 'low' as const,
  }],
}];

function approvalCard() {
  return document.querySelector('section[data-approval-status]') as HTMLElement | null;
}

function approveButton() {
  const card = approvalCard();
  if (!card) throw new Error('no approval card is rendered');
  const buttons = within(card).getAllByRole('button');
  return buttons[buttons.length - 1]!;
}

describe('ChatInterface approval lifecycle', () => {
  beforeEach(async () => {
    vi.resetAllMocks();
    await i18n.changeLanguage('zh-CN');
    vi.mocked(api.resolvePermission).mockResolvedValue({} as never);
  });

  it('drops the card once the decision is recorded', async () => {
    render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    expect(approvalCard()).not.toBeNull();

    await act(async () => { fireEvent.click(approveButton()); });

    expect(api.resolvePermission).toHaveBeenCalledExactlyOnceWith('call-1', 'allow');
    // The transcript keeps the tool call; only the pending decision is gone.
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(approvalCard()).toBeNull();
  });

  it('keeps an expired request on screen with its reason', async () => {
    vi.mocked(api.resolvePermission).mockRejectedValue(new ApiRequestError(409, 'Approval request is gone'));
    render(<ChatInterface messages={messages} onSend={vi.fn()} />);

    await act(async () => { fireEvent.click(approveButton()); });

    // The resolved set only grows on success, so a terminal failure stays
    // visible and the user learns why the request can no longer be answered.
    expect(approvalCard()).toHaveAttribute('data-approval-status', 'expired');
    expect(screen.getByRole('alert')).toHaveTextContent('此审批已过期');
    expect(approveButton()).toBeDisabled();
  });
});
