import { readFileSync } from 'node:fs';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { PageTransition } from './PageTransition';
import type { PageTransitionDirection, PageTransitionVariant } from './PageTransition';

const reducedMotionState = vi.hoisted(() => ({ value: false }));

vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('framer-motion')>();
  return {
    ...actual,
    useReducedMotion: () => reducedMotionState.value,
  };
});

interface HarnessProps {
  page: string;
  variant?: PageTransitionVariant;
  direction?: PageTransitionDirection;
}

function Harness({ page, variant, direction }: HarnessProps) {
  return (
    <PageTransition transitionKey={page} variant={variant} direction={direction}>
      <div>Page {page}</div>
    </PageTransition>
  );
}

afterEach(() => {
  reducedMotionState.value = false;
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('PageTransition', () => {
  it('defaults to the overlay: freezes the outgoing page under the mask, then swaps and settles', async () => {
    const { rerender } = render(<Harness page="agents" />);
    expect(screen.getByText('Page agents')).toBeInTheDocument();
    const mask = document.querySelector('.page-mask');
    expect(mask).toHaveAttribute('data-state', 'idle');
    expect(mask).toHaveAttribute('data-direction', 'forward');

    rerender(<Harness page="settings" />);
    expect(screen.getByText('Page agents')).toBeInTheDocument();
    expect(screen.queryByText('Page settings')).toBeNull();
    expect(mask).toHaveAttribute('data-state', 'cover');
    expect(screen.getByText('正在切换页面')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText('Page settings')).toBeInTheDocument(), { timeout: 4000 });
    expect(screen.queryByText('Page agents')).toBeNull();
    await waitFor(() => expect(mask).toHaveAttribute('data-state', 'idle'), { timeout: 4000 });
    expect(screen.queryByText('正在切换页面')).toBeNull();
  });

  it('follows the latest key when navigation changes again mid-cover', async () => {
    const { rerender } = render(<Harness page="agents" />);
    rerender(<Harness page="workflows" />);
    rerender(<Harness page="settings" />);
    expect(screen.getByText('Page agents')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Page settings')).toBeInTheDocument(), { timeout: 4000 });
    expect(screen.queryByText('Page workflows')).toBeNull();
    const mask = document.querySelector('.page-mask');
    await waitFor(() => expect(mask).toHaveAttribute('data-state', 'idle'), { timeout: 4000 });
  });

  it('passes the configured direction to the mask', () => {
    const { rerender } = render(<Harness page="agents" direction="backward" />);
    rerender(<Harness page="settings" direction="backward" />);
    expect(document.querySelector('.page-mask')).toHaveAttribute('data-direction', 'backward');
  });

  it('switches immediately without animation frames under reduced motion', () => {
    reducedMotionState.value = true;
    const { rerender } = render(<Harness page="agents" />);
    rerender(<Harness page="settings" />);
    expect(screen.getByText('Page settings')).toBeInTheDocument();
    expect(screen.queryByText('Page agents')).toBeNull();
    expect(document.querySelector('.page-mask')).toHaveAttribute('data-state', 'idle');
    expect(screen.queryByText('正在切换页面')).toBeNull();
  });

  it('keeps the fade variant as an opt-in without a mask', async () => {
    const { rerender } = render(<Harness page="agents" variant="fade" />);
    expect(screen.getByText('Page agents')).toBeInTheDocument();
    expect(document.querySelector('.page-mask')).toBeNull();
    rerender(<Harness page="settings" variant="fade" />);
    expect(document.querySelector('.page-mask')).toBeNull();
    await waitFor(() => expect(screen.getByText('Page settings')).toBeInTheDocument(), { timeout: 4000 });
    expect(screen.queryByText('Page agents')).toBeNull();
  });

  it('switches immediately for the fade variant under reduced motion', () => {
    reducedMotionState.value = true;
    const { rerender } = render(<Harness page="agents" variant="fade" />);
    rerender(<Harness page="settings" variant="fade" />);
    expect(screen.getByText('Page settings')).toBeInTheDocument();
    expect(screen.queryByText('Page agents')).toBeNull();
  });

  it('keeps the mask a fixed, pointer-transparent layer that only blocks while covering', () => {
    const styles = readFileSync('src/index.css', 'utf8');
    expect(styles).toMatch(/\.page-mask\s*\{[^}]*position: fixed;/);
    expect(styles).toMatch(/\.page-mask\s*\{[^}]*z-index: var\(--z-overlay, 300\);/);
    expect(styles).toMatch(/\.page-mask\s*\{[^}]*pointer-events: none;/);
    expect(styles).toMatch(/\.page-mask\[data-state='cover'\]\s*\{\s*pointer-events: auto;/);
    expect(styles).toMatch(/\.page-mask\s*\{[^}]*will-change: transform;/);
    expect(styles).not.toMatch(/@keyframes page-mask/);
  });
});
