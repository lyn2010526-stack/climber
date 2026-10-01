import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PRIVACY_SHAKE_STYLE } from '../LockScreen';
import { PinSetup } from '../PinSetup';
import { resetPrivacyStorage, setupPrivacyHarness } from './harness';

beforeEach(async () => {
  await setupPrivacyHarness();
  resetPrivacyStorage();
});

afterEach(cleanup);

function pressDigits(digits: string): void {
  for (const digit of digits.split('')) {
    fireEvent.click(screen.getByRole('button', { name: `数字 ${digit}` }));
  }
}

describe('PinSetup', () => {
  it('collects the passcode twice and confirms on matching entries', async () => {
    const onConfirm = vi.fn().mockResolvedValue(true);
    render(<PinSetup onConfirm={onConfirm} />);
    expect(screen.getByText('请输入六位数字密码')).toBeInTheDocument();
    pressDigits('135790');
    expect(await screen.findByText('请再次输入以确认')).toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
    pressDigits('135790');
    await vi.waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith('135790');
    });
  });

  it('shows the mismatch error, shakes, and restarts from the first step', async () => {
    const onConfirm = vi.fn().mockResolvedValue(true);
    render(<PinSetup onConfirm={onConfirm} />);
    pressDigits('135790');
    await screen.findByText('请再次输入以确认');
    pressDigits('654321');
    expect(await screen.findByText('两次输入不一致，请重新设置')).toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText('请输入六位数字密码')).toBeInTheDocument();
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 0 位，共 6 位');
    expect(document.querySelector('[data-shake="true"]')).not.toBeNull();
    expect(PRIVACY_SHAKE_STYLE).toContain('@media (prefers-reduced-motion: reduce)');
    expect(PRIVACY_SHAKE_STYLE).toContain('animation: none');
  });

  it('surfaces a failure when onConfirm resolves false', async () => {
    const onConfirm = vi.fn().mockResolvedValue(false);
    render(<PinSetup onConfirm={onConfirm} />);
    pressDigits('135790');
    await screen.findByText('请再次输入以确认');
    pressDigits('135790');
    expect(await screen.findByText('设置失败，请重试')).toBeInTheDocument();
    expect(screen.getByText('请输入六位数字密码')).toBeInTheDocument();
  });

  it('keeps typing after a wrong entry starts with an empty field', () => {
    const onConfirm = vi.fn().mockResolvedValue(true);
    render(<PinSetup onConfirm={onConfirm} />);
    pressDigits('11');
    fireEvent.click(screen.getByRole('button', { name: '删除' }));
    expect(screen.getByTestId('pin-dots').getAttribute('aria-label')).toBe('已输入 1 位，共 6 位');
  });

  it('calls onSkip when the user skips', () => {
    const onSkip = vi.fn();
    render(<PinSetup onConfirm={vi.fn().mockResolvedValue(true)} onSkip={onSkip} />);
    expect(screen.getByRole('button', { name: '跳过' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '跳过' }));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('hides the skip action when onSkip is absent', () => {
    render(<PinSetup onConfirm={vi.fn().mockResolvedValue(true)} />);
    expect(screen.queryByRole('button', { name: '跳过' })).toBeNull();
  });
});
