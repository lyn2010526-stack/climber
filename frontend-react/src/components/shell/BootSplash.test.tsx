import { StrictMode } from 'react';
import { readFileSync } from 'node:fs';
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BootSplash } from './BootSplash';
import { CLIMBER_MARK } from '../brand/ClimberMark';
import { hasSeenBootSession, markBootSessionSeen } from '../motion/bootSession';

beforeEach(() => {
  vi.useFakeTimers();
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('BootSplash', () => {
  it('plays the first-session orchestration, then reveals and completes', () => {
    const onDone = vi.fn();
    render(<BootSplash onDone={onDone} />);
    const splash = screen.getByRole('status');
    expect(splash).toHaveAccessibleName(/Climber/);
    expect(splash).toHaveClass('boot-splash-first');
    expect(splash.querySelector('polyline')).toHaveAttribute('points', CLIMBER_MARK.ridge);
    expect(screen.getByText('Climber')).toBeInTheDocument();
    expect(screen.getByText('Preparing your workspace')).toBeInTheDocument();
    expect(splash.querySelector('.boot-splash-bar')).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(639));
    expect(splash).not.toHaveClass('boot-splash-exit');
    act(() => vi.advanceTimersByTime(1));
    expect(splash).toHaveClass('boot-splash-exit');
    act(() => vi.advanceTimersByTime(299));
    expect(onDone).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(hasSeenBootSession()).toBe(true);
    act(() => vi.advanceTimersByTime(1000));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('passes quickly on a repeat session in the same tab', () => {
    markBootSessionSeen();
    const onDone = vi.fn();
    render(<BootSplash onDone={onDone} />);
    const splash = screen.getByRole('status');
    expect(splash).toHaveClass('boot-splash-quick');
    expect(splash.querySelector('.boot-splash-name')).toBeNull();
    expect(splash.querySelector('.boot-splash-bar')).toBeNull();
    expect(splash.querySelector('.boot-splash-tagline')).toBeNull();
    act(() => vi.advanceTimersByTime(179));
    expect(splash).not.toHaveClass('boot-splash-exit');
    act(() => vi.advanceTimersByTime(1));
    expect(splash).toHaveClass('boot-splash-exit');
    act(() => vi.advanceTimersByTime(159));
    expect(onDone).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(hasSeenBootSession()).toBe(true);
  });

  it('keeps the original deadline and uses the latest callback after a rerender', () => {
    const original = vi.fn();
    const latest = vi.fn();
    const { rerender } = render(<BootSplash onDone={original} />);
    act(() => vi.advanceTimersByTime(300));
    rerender(<BootSplash onDone={latest} />);
    act(() => vi.advanceTimersByTime(640));
    expect(original).not.toHaveBeenCalled();
    expect(latest).toHaveBeenCalledTimes(1);
  });

  it.each([200, 700])('clears both timers when unmounted at %ims', (elapsed) => {
    const onDone = vi.fn();
    const { unmount } = render(<BootSplash onDone={onDone} />);
    act(() => vi.advanceTimersByTime(elapsed));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    act(() => vi.advanceTimersByTime(1000));
    expect(onDone).not.toHaveBeenCalled();
  });

  it('completes once under StrictMode effect replay', () => {
    const onDone = vi.fn();
    render(<StrictMode><BootSplash onDone={onDone} /></StrictMode>);
    expect(vi.getTimerCount()).toBe(2);
    act(() => vi.advanceTimersByTime(940));
    expect(onDone).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(1000));
    expect(vi.getTimerCount()).toBe(0);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('immediately hands off for reduced motion without a held display or reveal', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const onDone = vi.fn();
    render(<BootSplash onDone={onDone} />);
    act(() => vi.advanceTimersByTime(0));
    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)');
    expect(onDone).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(1));
    expect(vi.getTimerCount()).toBe(0);
  });

  it('cleans up normally with an optional completion callback', () => {
    render(<BootSplash />);
    act(() => vi.advanceTimersByTime(940));
    act(() => vi.advanceTimersByTime(1000));
    expect(vi.getTimerCount()).toBe(0);
  });

  it('marks the session only once the full hand-off has fired', () => {
    expect(hasSeenBootSession()).toBe(false);
    const onDone = vi.fn();
    render(<BootSplash onDone={onDone} />);
    act(() => vi.advanceTimersByTime(639));
    expect(hasSeenBootSession()).toBe(false);
    act(() => vi.advanceTimersByTime(301));
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(hasSeenBootSession()).toBe(true);
  });

  it('orchestrates with transform-only keyframes and a static reduced-motion override', () => {
    const styles = readFileSync('src/index.css', 'utf8');
    const bootStyles = styles.slice(styles.indexOf('.boot-splash {'));
    expect(bootStyles).toMatch(/\.boot-splash-bar\s*\{[^}]*height: 2px;/);
    expect(bootStyles).toMatch(/\.boot-splash-first \.boot-splash-mark\s*\{[^}]*animation: boot-mark-in/);
    expect(bootStyles).toMatch(/\.boot-splash-first \.boot-splash-name\s*\{[^}]*animation: boot-name-in/);
    expect(bootStyles).toMatch(/\.boot-splash-first \.boot-splash-bar::after\s*\{[^}]*animation: boot-fill/);
    expect(bootStyles).toMatch(/\.boot-splash-first \.boot-splash-tagline\s*\{[^}]*animation: boot-tagline-in/);
    expect(bootStyles).toMatch(/\.boot-splash-first\.boot-splash-exit\s*\{[^}]*animation: boot-reveal 300ms/);
    expect(bootStyles).toMatch(/\.boot-splash-quick\.boot-splash-exit\s*\{[^}]*animation: boot-fade-out 160ms/);
    expect(bootStyles).toMatch(/@keyframes boot-mark-in\s*\{\s*from \{ opacity: 0; transform: translateY\(12px\) scale\(0\.88\); \}/);
    expect(bootStyles).toMatch(/@keyframes boot-fill\s*\{\s*from \{ transform: scaleX\(0\); \}\s*to \{ transform: scaleX\(1\); \}/);
    expect(bootStyles).toMatch(/@keyframes boot-reveal\s*\{\s*to \{ transform: translateY\(-100%\); \}/);
    expect(bootStyles).not.toMatch(/@keyframes boot-[a-z-]+\s*\{[^}]*(width|height|margin|padding|top|left|right|bottom)\s*:/);
    expect(bootStyles).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*\.boot-splash-tagline\s*\{[\s\S]*?animation: none;/);
    expect(bootStyles).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*\.boot-splash-bar::after\s*\{\s*transform: none;/);
  });
});
