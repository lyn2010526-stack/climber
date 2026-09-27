import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ApiRequestError } from '../../api';
import { FloatingPermissionDialog, isExpiredError, type PermissionRequest } from './FloatingPermissionDialog';

const highRisk: PermissionRequest = {
  id: 'request-1', action: 'command', description: 'Run the selected command',
  details: 'npm test', severity: 'high', timestamp: 1,
};
const lowRisk: PermissionRequest = { ...highRisk, severity: 'low' };
const handlers = { onApprove: vi.fn(), onDeny: vi.fn(), onApproveAll: vi.fn() };

function renderDialog(requests: PermissionRequest[], props: Partial<typeof handlers> = {}) {
  return render(
    <FloatingPermissionDialog requests={requests} {...handlers} {...props} />,
  );
}

/** One request card. The dialog frame and the card are both regions, so the
 *  card is addressed by the state it publishes. */
function card(): HTMLElement {
  const element = document.querySelector('section[data-approval-status]');
  if (!element) throw new Error('no approval card is rendered');
  return element as HTMLElement;
}

/** The approve and deny controls are the last two buttons of a request card. */
function actions() {
  const buttons = within(card()).getAllByRole('button');
  return { approve: buttons[buttons.length - 1]!, deny: buttons[buttons.length - 2]! };
}

describe('Approval terminal states', () => {
  beforeEach(async () => { await i18n.changeLanguage('zh-CN'); });

  it('reads an expiry from the status code and from a body that names it', () => {
    expect(isExpiredError(new ApiRequestError(409, 'Approval expired'))).toBe(true);
    expect(isExpiredError({ response: { status: 409 } })).toBe(true);
    expect(isExpiredError(new Error('This approval request has expired'))).toBe(true);
    expect(isExpiredError(new Error('Approval already expired upstream'))).toBe(true);
    // A status that is present and is not 409 is the answer; the text never wins.
    expect(isExpiredError(new ApiRequestError(500, 'expired'))).toBe(false);
    expect(isExpiredError(new ApiRequestError(400, 'Invalid tool_call_id'))).toBe(false);
    expect(isExpiredError(new Error('Network request failed'))).toBe(false);
    expect(isExpiredError(undefined)).toBe(false);
  });

  it('locks an expired request for good and explains why a retry is pointless', async () => {
    const onApprove = vi.fn(() => Promise.reject(new ApiRequestError(409, 'Approval request is no longer pending')));
    renderDialog([lowRisk], { onApprove });

    const { approve, deny } = actions();
    await act(async () => { fireEvent.click(approve); });

    // Terminal: every control is locked, the request stays for the record, and
    // the reason is stated instead of an offer to try again.
    expect(onApprove).toHaveBeenCalledExactlyOnceWith('request-1');
    expect(card()).toHaveAttribute('data-approval-status', 'expired');
    expect(approve).toBeDisabled();
    expect(deny).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent('此审批已过期');
    expect(screen.getByRole('alert')).toHaveTextContent('重试无效');
    expect(screen.queryByText('可重试，操作内容已保留。')).not.toBeInTheDocument();

    // Retrying is not merely disabled, it is refused: the lock outlives the click.
    fireEvent.click(approve);
    fireEvent.click(deny);
    expect(onApprove).toHaveBeenCalledOnce();
    expect(handlers.onDeny).not.toHaveBeenCalled();
  });

  it('keeps a failed submission unlocked so the same decision can be retried', async () => {
    const onApprove = vi.fn()
      .mockRejectedValueOnce(new Error('Network request failed'))
      .mockResolvedValueOnce(undefined);
    renderDialog([lowRisk], { onApprove });

    const { approve } = actions();
    await act(async () => { fireEvent.click(approve); });
    expect(card()).toHaveAttribute('data-approval-status', 'error');
    expect(approve).toBeEnabled();
    expect(screen.getByRole('alert')).toHaveTextContent('Network request failed');
    expect(screen.getByRole('alert')).toHaveTextContent('可重试');

    await act(async () => { fireEvent.click(approve); });
    expect(onApprove).toHaveBeenCalledTimes(2);
    // The decision landed, so the card leaves the stack.
    expect(document.querySelector('section[data-approval-status]')).toBeNull();
  });

  it('locks a submission in flight and reports success by removing the card', async () => {
    let resolve!: () => void;
    const onApprove = vi.fn(() => new Promise<void>((done) => { resolve = done; }));
    renderDialog([lowRisk], { onApprove });

    const { approve, deny } = actions();
    fireEvent.click(approve);
    expect(card()).toHaveAttribute('data-approval-status', 'submitting');
    expect(approve).toBeDisabled();
    expect(deny).toBeDisabled();
    // One activation, one submission: the in-flight lock is what enforces it.
    fireEvent.click(approve);
    expect(onApprove).toHaveBeenCalledOnce();

    await act(async () => { resolve(); });
    expect(document.querySelector('section[data-approval-status]')).toBeNull();
  });

  it('holds the high-risk confirmation across a card remount and voids it on new content', async () => {
    const onApprove = vi.fn(() => Promise.reject(new Error('Network request failed')));
    const { rerender } = render(
      <FloatingPermissionDialog requests={[highRisk]} {...handlers} onApprove={onApprove} />,
    );
    fireEvent.click(screen.getByRole('checkbox'));

    // A streaming update re-keys the card; the acknowledgement is the user's and
    // it outlives the element that recorded it.
    rerender(
      <FloatingPermissionDialog requests={[{ ...highRisk, timestamp: 2 }]} {...handlers} onApprove={onApprove} />,
    );
    expect(screen.getByRole('checkbox')).toBeChecked();

    // The moment the authorisable content changes, the old acknowledgement is
    // about a different command and cannot carry over.
    rerender(
      <FloatingPermissionDialog requests={[{ ...highRisk, details: 'npm publish', timestamp: 3 }]} {...handlers} onApprove={onApprove} />,
    );
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(actions().approve).toBeDisabled();
  });

  it('locks the whole card when a bulk approval is in flight', async () => {
    let resolve!: () => void;
    const onApproveAll = vi.fn(() => new Promise<void>((done) => { resolve = done; }));
    renderDialog([lowRisk, { ...lowRisk, id: 'request-2' }], { onApproveAll });
    const bulk = screen.getAllByRole('button').at(-1)!;
    fireEvent.click(bulk);
    expect(card()).toHaveAttribute('aria-busy', 'true');
    expect(actions().deny).toBeDisabled();
    await act(async () => { resolve(); });
    expect(card()).toHaveAttribute('aria-busy', 'false');
  });

  it('names the expired state in the language the user reads', async () => {
    await act(async () => { await i18n.changeLanguage('en'); });
    try {
      renderDialog([lowRisk], { onApprove: vi.fn(() => Promise.reject(new ApiRequestError(409, 'gone'))) });
      await act(async () => { fireEvent.click(actions().approve); });
      expect(screen.getByRole('alert')).toHaveTextContent('This approval request has expired');
    } finally {
      await act(async () => { await i18n.changeLanguage('zh-CN'); });
    }
  });
});
