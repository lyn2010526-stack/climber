import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ToolCallVisualization, type ToolCall } from './ToolCallVisualization';
import { FloatingPermissionDialog, type PermissionRequest } from './FloatingPermissionDialog';

const request: PermissionRequest = { id: 'request-1', action: 'command', description: 'Run the selected command', details: 'npm test', severity: 'high', timestamp: 1 };
const call: ToolCall = { id: 'call-1', name: 'run_command', arguments: { command: 'npm test' }, result: 'Passed', status: 'success' };

describe('Task 04 tool disclosure and approval', () => {
  it('expands successful calls and discloses the arguments of an already visible output', () => {
    render(<ToolCallVisualization calls={[call]} />);
    expect(screen.queryByText(/"command"/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.expand_all') }));
    fireEvent.click(screen.getByRole('button', { name: `${i18n.t('tool_call.arguments')} (1)` }));
    expect(screen.getByText(/"command"/)).toHaveTextContent('npm test');
    // The output is the card's body, so it is readable the moment it expands.
    expect(screen.getByText('Passed')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.collapse_all') }));
    expect(screen.queryByText(/"command"/)).not.toBeInTheDocument();
  });

  it('preserves manual expansion across status updates and displays full errors', () => {
    const { rerender } = render(<ToolCallVisualization calls={[{ ...call, status: 'running' }]} />);
    fireEvent.click(screen.getByRole('button', { name: /run_command/ }));
    rerender(<ToolCallVisualization calls={[{ ...call, status: 'error', error: 'Command failed: exit code 1' }]} />);
    expect(screen.getByRole('button', { name: /run_command/ })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Command failed: exit code 1')).toBeVisible();
  });

  it('drops the argument section for an empty object and still shows empty output', () => {
    render(<ToolCallVisualization calls={[{ ...call, arguments: {}, result: '' }]} defaultExpanded />);
    // Nothing was passed, so there is no parameters section to fold.
    expect(screen.queryByRole('button', { name: i18n.t('tool_call.arguments') })).toBeNull();
    expect(screen.getByLabelText(i18n.t('tool_call.result'))).toBeVisible();
  });

  it('requires explicit high-risk confirmation and keeps denial available', async () => {
    const onApprove = vi.fn();
    const onDeny = vi.fn();
    render(<FloatingPermissionDialog requests={[request]} onApprove={onApprove} onDeny={onDeny} onApproveAll={vi.fn()} />);
    expect(screen.getByText('npm test')).toBeVisible();
    const buttons = within(screen.getByRole('region')).getAllByRole('button');
    const approve = buttons[buttons.length - 1]!;
    const deny = buttons[buttons.length - 2]!;
    expect(approve).toBeDisabled();
    expect(deny).toBeEnabled();
    // Denial needs no confirmation, and it ends the request like any other decision.
    await act(async () => { fireEvent.click(deny); });
    expect(onDeny).toHaveBeenCalledExactlyOnceWith(request.id);

    render(<FloatingPermissionDialog requests={[request]} onApprove={onApprove} onDeny={onDeny} onApproveAll={vi.fn()} />);
    fireEvent.click(screen.getByRole('checkbox'));
    await act(async () => { fireEvent.click(screen.getAllByRole('button').at(-1)!); });
    expect(onApprove).toHaveBeenCalledExactlyOnceWith(request.id);
  });

  it('treats file deletion as dangerous and resets confirmation for changed contents', () => {
    const props = { onApprove: vi.fn(), onDeny: vi.fn(), onApproveAll: vi.fn() };
    const deletion = { ...request, action: 'file_delete' as const, severity: 'low' as const };
    const { rerender } = render(<FloatingPermissionDialog {...props} requests={[deletion]} />);
    fireEvent.click(screen.getByRole('checkbox'));
    rerender(<FloatingPermissionDialog {...props} requests={[{ ...deletion, details: '/different/file' }]} />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByText('/different/file')).toBeVisible();
  });

  it('limits bulk approval to low-risk requests and keeps minimized requests recoverable', async () => {
    const onApproveAll = vi.fn();
    const props = { onApprove: vi.fn(), onDeny: vi.fn(), onApproveAll };
    const low = { ...request, severity: 'low' as const };
    const { rerender } = render(<FloatingPermissionDialog {...props} requests={[low, { ...low, id: 'request-2' }]} />);
    const bulk = screen.getAllByRole('button').at(-1)!;
    await act(async () => { fireEvent.click(bulk); });
    expect(onApproveAll).toHaveBeenCalledOnce();
    rerender(<FloatingPermissionDialog {...props} requests={[low, { ...request, id: 'request-2' }]} />);
    expect(screen.queryByRole('button', { name: bulk.textContent! })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.collapse_all') }));
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.expand_all') }));
    expect(screen.getByRole('checkbox')).toBeVisible();
  });

  it('locks pending approval and surfaces callback errors without losing the request', async () => {
    let reject!: (error: Error) => void;
    const onApprove = vi.fn(() => new Promise<void>((_, fail) => { reject = fail; }));
    render(<FloatingPermissionDialog requests={[{ ...request, severity: 'low' }]} onApprove={onApprove} onDeny={vi.fn()} onApproveAll={vi.fn()} />);
    const buttons = within(screen.getByRole('region')).getAllByRole('button');
    const approve = buttons.at(-1)!;
    fireEvent.click(approve);
    expect(approve).toBeDisabled();
    fireEvent.click(approve);
    expect(onApprove).toHaveBeenCalledOnce();
    await act(async () => { reject(new Error('Approval failed')); });
    expect(screen.getByRole('alert')).toHaveTextContent('Approval failed');
    expect(approve).toBeEnabled();
  });
});
