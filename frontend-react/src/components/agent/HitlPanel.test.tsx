import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { HitlPanel } from './HitlPanel';

afterEach(() => cleanup());

describe('HitlPanel', () => {
  it('renders the title, description and both decisions', () => {
    render(<HitlPanel title="Approve deploy" description="Ship to production?" onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByRole('dialog', { name: 'Approve deploy' })).toBeVisible();
    expect(screen.getByText('Ship to production?')).toBeVisible();
    expect(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) })).toBeEnabled();
    expect(screen.getByRole('button', { name: i18n.t('hitl.reject', { defaultValue: 'Reject' }) })).toBeEnabled();
    expect(screen.queryByRole('button', { name: i18n.t('hitl.always_allow', { defaultValue: 'Always allow' }) })).not.toBeInTheDocument();
  });

  it('calls onApprove and onReject with no arguments', async () => {
    const onApprove = vi.fn(() => Promise.resolve());
    const onReject = vi.fn(() => Promise.resolve());
    render(<HitlPanel title="Gate" onApprove={onApprove} onReject={onReject} />);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) }));
    });
    expect(onApprove).toHaveBeenCalledOnce();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.reject', { defaultValue: 'Reject' }) }));
    });
    expect(onReject).toHaveBeenCalledOnce();
  });

  it('offers an always-allow action only when its handler is provided', async () => {
    const onAlwaysAllow = vi.fn(() => Promise.resolve());
    render(<HitlPanel title="Gate" onApprove={vi.fn()} onReject={vi.fn()} onAlwaysAllow={onAlwaysAllow} />);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.always_allow', { defaultValue: 'Always allow' }) }));
    });
    expect(onAlwaysAllow).toHaveBeenCalledOnce();
  });

  it('locks every decision while one is in flight', async () => {
    let resolve!: () => void;
    const onApprove = vi.fn(() => new Promise<void>(r => { resolve = r; }));
    const onReject = vi.fn();
    render(<HitlPanel title="Gate" onApprove={onApprove} onReject={onReject} onAlwaysAllow={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) }));
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('button', { name: i18n.t('hitl.reject', { defaultValue: 'Reject' }) })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) }));
    expect(onApprove).toHaveBeenCalledOnce();
    await act(async () => resolve());
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-busy', 'false');
  });

  it('surfaces a failure and re-enables the decision', async () => {
    const onApprove = vi.fn(() => Promise.reject(new Error('network down')));
    render(<HitlPanel title="Gate" onApprove={onApprove} onReject={vi.fn()} />);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) }));
    });
    expect(screen.getByRole('alert')).toHaveTextContent('network down');
    expect(screen.getByRole('button', { name: i18n.t('hitl.approve', { defaultValue: 'Approve' }) })).toBeEnabled();
  });

  it('renders nothing when show is false', () => {
    render(<HitlPanel title="Hidden" show={false} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
