import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { hashPin } from '../../../hooks/useAppLock';
import { LockScreen, PRIVACY_SHAKE_STYLE } from '../LockScreen';
import { PinSetup } from '../PinSetup';
import { resetPrivacyStorage, setupPrivacyHarness } from './harness';

const reducedMotionState = vi.hoisted(() => ({ value: false }));

vi.stubGlobal(
  'matchMedia',
  vi.fn((query: string) => ({
    matches: reducedMotionState.value && query.includes('prefers-reduced-motion'),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
);

beforeEach(async () => {
  await setupPrivacyHarness();
  resetPrivacyStorage();
});

afterEach(() => {
  cleanup();
  reducedMotionState.value = false;
});

function pressDigits(digits: string): void {
  for (const digit of digits.split('')) {
    fireEvent.click(screen.getByRole('button', { name: `数字 ${digit}` }));
  }
}

async function renderLockedScreen(
  onUnlock: () => void,
  extra?: { webAuthnAvailable?: boolean; onWebAuthnUnlock?: () => Promise<boolean> },
) {
  const stored = await hashPin('135790');
  render(
    <LockScreen
      pinHash={stored ?? ''}
      onUnlock={onUnlock}
      webAuthnAvailable={extra?.webAuthnAvailable}
      onWebAuthnUnlock={extra?.onWebAuthnUnlock}
    />,
  );
}

describe('LockScreen entrance choreography', () => {
  it('plays the staggered entrance from hidden states with the reveal line', async () => {
    await renderLockedScreen(vi.fn());
    const dialog = screen.getByRole('dialog', { name: '隐私锁屏' });
    expect(dialog).toHaveAttribute('data-lock-intro', 'play');
    expect(dialog).toHaveAttribute('data-unlock-phase', 'idle');
    const brand = document.querySelector('[data-lock-item="brand"]') as HTMLElement;
    const keypad = document.querySelector('[data-lock-item="keypad"]') as HTMLElement;
    const dots = document.querySelectorAll('[data-lock-item="pin-dot"]');
    expect(dots).toHaveLength(6);
    expect(brand.style.opacity).toBe('0');
    expect(keypad.style.opacity).toBe('0');
    expect((dots[0] as HTMLElement).style.opacity).toBe('0');
    expect(document.querySelector('[data-lock-item="reveal-line"]')).not.toBeNull();
    expect(document.querySelector('[data-lock-item="backdrop"]')).not.toBeNull();
  });

  it('presents the lock instantly under reduced motion', async () => {
    reducedMotionState.value = true;
    await renderLockedScreen(vi.fn());
    const dialog = screen.getByRole('dialog', { name: '隐私锁屏' });
    expect(dialog).toHaveAttribute('data-lock-intro', 'instant');
    const brand = document.querySelector('[data-lock-item="brand"]') as HTMLElement;
    const keypad = document.querySelector('[data-lock-item="keypad"]') as HTMLElement;
    expect(brand.style.opacity).not.toBe('0');
    expect(keypad.style.opacity).not.toBe('0');
    expect(document.querySelector('[data-lock-item="reveal-line"]')).toBeNull();
  });
});

describe('LockScreen unlock sequence', () => {
  it('celebrates the six dots in teal before firing onUnlock', async () => {
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    pressDigits('135790');
    const dialog = screen.getByRole('dialog', { name: '隐私锁屏' });
    await waitFor(() => expect(dialog).toHaveAttribute('data-unlock-phase', 'celebrate'));
    expect(onUnlock).not.toHaveBeenCalled();
    const dots = document.querySelectorAll('[data-lock-item="pin-dot"] > span');
    for (const dot of dots) {
      expect(dot.className).toContain('accent-foreground');
    }
    await waitFor(() => expect(onUnlock).toHaveBeenCalledTimes(1));
    expect(dialog).toHaveAttribute('data-unlock-phase', 'celebrate');
  });

  it('unlocks without the celebration hold under reduced motion', async () => {
    reducedMotionState.value = true;
    const onUnlock = vi.fn();
    await renderLockedScreen(onUnlock);
    pressDigits('135790');
    await waitFor(() => expect(onUnlock).toHaveBeenCalledTimes(1), { timeout: 400 });
    expect(screen.getByRole('dialog', { name: '隐私锁屏' })).toHaveAttribute(
      'data-unlock-phase',
      'idle',
    );
  });
});

describe('LockScreen face scanning ritual', () => {
  it('radiates the scanning rings with aria while WebAuthn is pending', async () => {
    let settle!: (ok: boolean) => void;
    const onWebAuthnUnlock = vi
      .fn()
      .mockImplementation(() => new Promise<boolean>((resolve) => {
        settle = resolve;
      }));
    await renderLockedScreen(vi.fn(), { webAuthnAvailable: true, onWebAuthnUnlock });
    fireEvent.click(screen.getByRole('button', { name: '使用人脸识别解锁' }));
    const face = screen.getByRole('button', { name: '使用人脸识别解锁' });
    expect(face).toHaveAttribute('data-face-state', 'scanning');
    expect(face).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('status')).toHaveTextContent('正在扫描人脸');
    expect(screen.getByText('正在识别人脸…')).toBeInTheDocument();
    const rings = document.querySelectorAll('.privacy-face-ring');
    expect(rings).toHaveLength(2);
    settle(true);
    await waitFor(() => expect(face).toHaveAttribute('data-face-state', 'succeeded'));
    expect(screen.getByRole('dialog', { name: '隐私锁屏' })).toHaveAttribute(
      'data-unlock-phase',
      'celebrate',
    );
  });

  it('collapses the rings to the error tone and keeps the keypad usable on failure', async () => {
    const onUnlock = vi.fn();
    let settle!: (ok: boolean) => void;
    const onWebAuthnUnlock = vi
      .fn()
      .mockImplementation(() => new Promise<boolean>((resolve) => {
        settle = resolve;
      }));
    await renderLockedScreen(onUnlock, { webAuthnAvailable: true, onWebAuthnUnlock });
    fireEvent.click(screen.getByRole('button', { name: '使用人脸识别解锁' }));
    settle(false);
    const face = screen.getByRole('button', { name: '使用人脸识别解锁' });
    await waitFor(() => expect(face).toHaveAttribute('data-face-state', 'failed'));
    const rings = document.querySelectorAll('.privacy-face-ring');
    expect(rings).toHaveLength(2);
    for (const ring of rings) {
      expect(ring).toHaveAttribute('data-tone', 'error');
    }
    expect(await screen.findByText('人脸识别不可用，请输入密码')).toBeInTheDocument();
    pressDigits('135790');
    await waitFor(() => expect(onUnlock).toHaveBeenCalledTimes(1));
  });
});

describe('injected keyframes governance', () => {
  it('keeps the style tag token-based and reduced-motion safe', () => {
    expect(PRIVACY_SHAKE_STYLE).toContain('@media (prefers-reduced-motion: reduce)');
    expect(PRIVACY_SHAKE_STYLE).toContain('animation: none');
    expect(PRIVACY_SHAKE_STYLE).toContain('privacy-face-ring-breathe');
    expect(PRIVACY_SHAKE_STYLE).toContain('var(--color-accent)');
    expect(PRIVACY_SHAKE_STYLE).toContain('var(--color-error)');
    expect(PRIVACY_SHAKE_STYLE).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(PRIVACY_SHAKE_STYLE).not.toMatch(/rgba?\(/);
  });
});

describe('PinSetup motion language', () => {
  it('shares the entrance choreography with the lock screen', () => {
    render(<PinSetup onConfirm={vi.fn().mockResolvedValue(true)} />);
    expect(document.querySelector('[data-lock-intro]')?.getAttribute('data-lock-intro')).toBe(
      'play',
    );
    const brand = document.querySelector('[data-lock-item="brand"]') as HTMLElement;
    expect(brand.style.opacity).toBe('0');
    expect(document.querySelector('[data-lock-item="reveal-line"]')).not.toBeNull();
    expect(document.querySelector('[data-lock-step]')?.getAttribute('data-lock-step')).toBe('set');
  });

  it('steps from set to confirm through the masked transition', async () => {
    render(<PinSetup onConfirm={vi.fn().mockResolvedValue(true)} />);
    pressDigits('135790');
    expect(await screen.findByText('请再次输入以确认')).toBeInTheDocument();
    expect(document.querySelector('[data-lock-step]')?.getAttribute('data-lock-step')).toBe(
      'confirm',
    );
  });

  it('swaps steps instantly under reduced motion', async () => {
    reducedMotionState.value = true;
    render(<PinSetup onConfirm={vi.fn().mockResolvedValue(true)} />);
    expect(document.querySelector('[data-lock-intro]')?.getAttribute('data-lock-intro')).toBe(
      'instant',
    );
    expect(document.querySelector('[data-lock-item="reveal-line"]')).toBeNull();
    pressDigits('135790');
    expect(await screen.findByText('请再次输入以确认')).toBeInTheDocument();
    const stage = document.querySelector('[data-lock-step]') as HTMLElement;
    expect(stage.style.opacity).not.toBe('0');
  });
});
