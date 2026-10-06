import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import { useWorkspaceStore } from '../../store/workspace';
import { AnchoredPopupStack } from './AnchoredPopupStack';

// 只桩掉 HTTP 响应，审批走真实的 api 客户端，这样 URL、method 与 body 都可断言。
const fetchResponse = vi.fn<typeof fetch>();

const label = (key: string, fallback: string) => i18n.t(key, { defaultValue: fallback });

beforeEach(() => {
  vi.clearAllMocks();
  resetAnchoredStore();
  useWorkspaceStore.setState({ permissionMode: null });
  vi.stubGlobal('fetch', fetchResponse);
  fetchResponse.mockResolvedValue(Response.json({ status: 'resolved' }));
});

afterEach(() => cleanup());

function pushApproval(popup: Parameters<ReturnType<typeof useAnchoredStore.getState>['pushPopup']>[0]) {
  return useAnchoredStore.getState().pushPopup(popup);
}

function resolveCalls() {
  return fetchResponse.mock.calls.filter(([url]) => String(url).includes('/permissions/resolve'));
}

it('keeps the Codex numbered options as the approval path and posts the documented body', async () => {
  pushApproval({ kind: 'approval', title: 'Would you like to run the following command?', command: 'echo hello', payload: { toolCallId: 'tool-1' } });
  render(<AnchoredPopupStack />);

  const popup = screen.getByTestId('anchored-popup');
  expect(popup).toHaveAttribute('data-approval-variant', 'exec');
  expect(within(popup).getByText('1. Yes, proceed')).toBeVisible();
  expect(within(popup).getByText(/2\. Yes, and don't ask again for commands that start with `echo hello`/)).toBeVisible();
  expect(within(popup).getByText('3. No, and tell Climber what to do differently')).toBeVisible();

  fireEvent.click(within(popup).getByRole('button', { name: 'Approve' }));
  await waitFor(() => expect(screen.queryByTestId('anchored-popup')).toBeNull());
  expect(resolveCalls()).toHaveLength(1);
  expect(resolveCalls()[0]?.[0]).toBe('/api/v1/permissions/resolve');
  expect(resolveCalls()[0]?.[1]).toMatchObject({ method: 'POST', body: JSON.stringify({ tool_call_id: 'tool-1', decision: 'allow' }) });
});

it('keeps the numbered shortcuts and the deny mapping on the Codex path', async () => {
  pushApproval({ kind: 'approval', title: 'Would you like to make the following edits?', path: '/tmp/target.md', payload: { toolCallId: 'tool-2' } });
  render(<AnchoredPopupStack />);
  const popup = screen.getByTestId('anchored-popup');
  expect(popup).toHaveAttribute('data-approval-variant', 'patch');

  fireEvent.keyDown(popup, { key: '3' });
  await waitFor(() => expect(resolveCalls()[0]?.[1]).toMatchObject({ body: JSON.stringify({ tool_call_id: 'tool-2', decision: 'deny' }) }));
  expect(screen.queryByTestId('anchored-popup')).toBeNull();
});

it('honours the popup confirm label on the Codex path', async () => {
  pushApproval({ kind: 'approval', title: 'Approve tool', confirmLabel: 'Run it', payload: { toolCallId: 'tool-3' } });
  render(<AnchoredPopupStack />);
  const approve = screen.getByRole('button', { name: 'Run it' });
  expect(screen.getByTestId('anchored-popup')).toBeVisible();
  fireEvent.click(approve);
  await waitFor(() => expect(resolveCalls()[0]?.[1]).toMatchObject({ body: JSON.stringify({ tool_call_id: 'tool-3', decision: 'allow' }) }));
});

it('falls back to the panel approval form when the popup carries no option list', async () => {
  pushApproval({ kind: 'approval', title: 'Approve tool', description: 'needs review', payload: { toolCallId: 'tool-9' } });
  render(<AnchoredPopupStack />);

  expect(screen.queryByTestId('anchored-popup')).toBeNull();
  const dialog = screen.getByRole('dialog', { name: 'Approve tool' });
  expect(within(dialog).getByText('needs review')).toBeVisible();
  expect(within(dialog).queryByRole('button', { name: label('hitl.always_allow', 'Always allow') })).toBeNull();

  fireEvent.click(within(dialog).getByRole('button', { name: label('hitl.approve', 'Approve') }));
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  expect(resolveCalls()[0]?.[0]).toBe('/api/v1/permissions/resolve');
  expect(resolveCalls()[0]?.[1]).toMatchObject({ method: 'POST', body: JSON.stringify({ tool_call_id: 'tool-9', decision: 'allow' }) });
});

it('maps the fallback reject decision to deny', async () => {
  pushApproval({ kind: 'approval', title: 'Approve tool', description: 'needs review', payload: { toolCallId: 'tool-10' } });
  render(<AnchoredPopupStack />);
  fireEvent.click(within(screen.getByRole('dialog', { name: 'Approve tool' })).getByRole('button', { name: label('anchored.popup.cancel', 'Cancel') }));
  await waitFor(() => expect(resolveCalls()[0]?.[1]).toMatchObject({ body: JSON.stringify({ tool_call_id: 'tool-10', decision: 'deny' }) }));
  expect(screen.queryByRole('dialog')).toBeNull();
});

it('offers always allow only while the reported permission config allows it', async () => {
  useWorkspaceStore.setState({ permissionMode: 'strict' });
  pushApproval({ kind: 'approval', title: 'Approve tool', payload: { toolCallId: 'tool-11' } });
  render(<AnchoredPopupStack />);
  expect(screen.queryByRole('button', { name: label('hitl.always_allow', 'Always allow') })).toBeNull();

  cleanup();
  resetAnchoredStore();
  useWorkspaceStore.setState({ permissionMode: 'default' });
  pushApproval({ kind: 'approval', title: 'Approve tool', payload: { toolCallId: 'tool-12' } });
  render(<AnchoredPopupStack />);
  fireEvent.click(screen.getByRole('button', { name: label('hitl.always_allow', 'Always allow') }));
  await waitFor(() => expect(resolveCalls()[0]?.[1]).toMatchObject({ body: JSON.stringify({ tool_call_id: 'tool-12', decision: 'allow' }) }));
});

it('keeps a failed fallback decision on screen instead of dropping the request', async () => {
  fetchResponse.mockRejectedValueOnce(new Error('offline'));
  pushApproval({ kind: 'approval', title: 'Approve tool', payload: { toolCallId: 'tool-13' } });
  render(<AnchoredPopupStack />);
  const dialog = screen.getByRole('dialog', { name: 'Approve tool' });
  fireEvent.click(within(dialog).getByRole('button', { name: label('hitl.approve', 'Approve') }));
  expect(await within(dialog).findByRole('alert')).toHaveTextContent('offline');
  expect(screen.getByRole('dialog', { name: 'Approve tool' })).toBeInTheDocument();
});

it('stacks both approval forms with the newest popup on top', () => {
  pushApproval({ kind: 'approval', title: 'Would you like to run the following command?', command: 'echo hello', payload: { toolCallId: 'tool-14' } });
  pushApproval({ kind: 'approval', title: 'Approve tool', payload: { toolCallId: 'tool-15' } });
  render(<AnchoredPopupStack />);
  const dialogs = screen.getAllByRole('dialog');
  expect(dialogs).toHaveLength(2);
  expect(dialogs[0]).toHaveAccessibleName('Approve tool');
  expect(dialogs[1]).toHaveAttribute('data-approval-variant', 'exec');
});